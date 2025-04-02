import multiprocessing
import os
import time
import flask
import threading
import sys
import logging

from flask import jsonify
import octoprint.plugin
from pathlib import Path
from octoprint.schema.webcam import Webcam, WebcamCompatibility
import octoprint.webcams
import yaml
import requests
from . import visionModule
from . import notifications
from . import monitoring as Monitoring

class cvpluginInit(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.WebcamProviderPlugin,
                       octoprint.plugin.AssetPlugin,
                       octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.BlueprintPlugin,
                       octoprint.plugin.ShutdownPlugin):
    
    _notificationsModule = None

    _CVprocess = None
    _queueListener = None

    _queue = None
    _running = None
    _pausedOnError = False
    _currentConfidence = 0
    _webcam = None

    _lastPauseTime = 0


    def on_after_startup(self):
        self._logger.info("CVPrinting started")
        multiprocessing.set_start_method('spawn', force=True)
        self._running = multiprocessing.Value('b', False)
        self._notificationsModule = notifications.Notificationscvprinting(self._settings, self._logger)
        #Create folder for storing images
        os.makedirs(os.path.join(self._basefolder, 'data/images'), exist_ok=True)


    def on_shutdown(self):
        #Make sure monitoring process and listener thread are stopped
        self.stop_monitoring()
        self._logger.info("CVPrinting stopped")


    def get_settings_defaults(self):
        return dict(pausePrintOnIssue=False, pauseThreshold=80, warningThreshold=50, cvprintingSnapshotUrl="", cvprintingStreamUrl="", cvEnabled=True, discordNotifications=False, discordWebhookUrl="", selectedWebcam="classic", telegramNotifications=False, telegramBotToken="", telegramChatId="")

    def get_webcam_list(self):
        webcams = octoprint.webcams.get_webcams()
        webcamList = []
        for webcamName, providerContainer in webcams.items():
            if webcamName == "classic" or webcamName == "cvprinting":
                webcamList.append({
                    "name": webcamName,
                    "streamUrl": providerContainer.config.extras.get("stream", None),
                    "snapshotUrl": providerContainer.config.snapshotDisplay
                })
        return webcamList
                
    #Get the currently used webcam
    def get_current_webcam(self):
        webcamList = self.get_webcam_list()
        for webcam in webcamList:
            if webcam["name"] == self._settings.get(["selectedWebcam"]):
                return webcam
        if (self._settings.get(["selectedWebcam"]) == "cvprinting"):
            return {"name": "cvprinting", "streamUrl": self._settings.get(["cvprintingStreamUrl"]), "snapshotUrl": self._settings.get(["cvprintingSnapshotUrl"])}
        return None
    
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True, template="cvprinting_settings.jinja2"),
            dict(type="sidebar", custom_bindings=True, template="cvprinting_sidebar.jinja2"),
        ]
    
    #API endpoint to get the list of webcams
    @octoprint.plugin.BlueprintPlugin.route("/get_webcams", methods=["POST"])
    def get_webcams(self):
        webcamList = self.get_webcam_list()
        return jsonify(webcamList)
    
    #API endpoint to get the current confidence value
    @octoprint.plugin.BlueprintPlugin.route("/get_confidence", methods=["POST"])
    def get_confidence(self):
        return jsonify({"variable": self._currentConfidence})
    
    #API endpoint to test notifications
    @octoprint.plugin.BlueprintPlugin.route("/test_notifications", methods=["POST"])
    def test_notifications(self):
        value = None
        if not "target" in flask.request.values:
            return jsonify({"message": "Error: No target specified"}), 400
        if flask.request.values["target"] == "discord":
            if not "webhook_url" in flask.request.values:
                return jsonify({"message": "Error: No webhook URL specified"}), 400
            value = self._notificationsModule.notify("Test", {"target":"discord", "webhook_url": flask.request.values["webhook_url"]})
        elif flask.request.values["target"] == "telegram":
            if not "chat_id" in flask.request.values or not "token" in flask.request.values:
                return jsonify({"message": "Error: No chat ID or token specified"}), 400
            value = self._notificationsModule.notify("Test", {"target":"telegram", "chat_id": flask.request.values["chat_id"], "token": flask.request.values["token"]})
        else:
            return jsonify({"message": "Error: Invalid target specified"}), 400
        if value == 0:
            return jsonify({"message": "Notification sent"}), 200
        else:
            return jsonify({"message": "Error sending notification, verify inputted data"}), 400
    
    #API endpoint for obtaining current settings
    @octoprint.plugin.BlueprintPlugin.route("/get_settings", methods=["POST"])
    def get_settings(self):
        settings = dict()
        settings["pausePrintOnIssue"] = self._settings.get(["pausePrintOnIssue"])
        settings["pauseThreshold"] = self._settings.get(["pauseThreshold"])
        settings["warningThreshold"] = self._settings.get(["warningThreshold"])
        settings["cvprintingSnapshotUrl"] = self._settings.get(["cvprintingSnapshotUrl"])
        settings["cvprintingStreamUrl"] = self._settings.get(["cvprintingStreamUrl"])
        settings["selectedWebcam"] = self._settings.get(["selectedWebcam"])
        settings["cvEnabled"] = self._settings.get(["cvEnabled"])
        settings["discordNotifications"] = self._settings.get(["discordNotifications"])
        settings["discordWebhookUrl"] = self._settings.get(["discordWebhookUrl"])
        settings["telegramNotifications"] = self._settings.get(["telegramNotifications"])
        settings["telegramBotToken"] = self._settings.get(["telegramBotToken"])
        settings["telegramChatId"] = self._settings.get(["telegramChatId"])
        #TODO: Include webcam list in settings
        return jsonify(settings)
    
    #API endpoint for updating settings
    @octoprint.plugin.BlueprintPlugin.route("/update_settings", methods=["POST"])
    def update_settings(self):
        data = flask.request.get_json()
        if not data:
            return jsonify({"message": "Error: No data received"}), 400
        if "pausePrintOnIssue" in data.keys():
            if not isinstance(data["pausePrintOnIssue"], bool):
                return jsonify({"message": "Error: Invalid value for pausePrintOnIssue"}), 400
            self._settings.set(["pausePrintOnIssue"], data["pausePrintOnIssue"])
        if "pauseThreshold" in data.keys():
            if not isinstance(data["pauseThreshold"], int) and not isinstance(data["pauseThreshold"], float):
                return jsonify({"message": "Error: Invalid value for pauseThreshold"}), 400
            self._settings.set(["pauseThreshold"], int(data["pauseThreshold"]))
        if "warningThreshold" in data.keys():
            if not isinstance(data["warningThreshold"], int) and not isinstance(data["warningThreshold"], float):
                return jsonify({"message": "Error: Invalid value for warningThreshold"}), 400
            self._settings.set(["warningThreshold"], int(data["warningThreshold"]))
        if "cvprintingSnapshotUrl" in data.keys():
            if not isinstance(data["cvprintingSnapshotUrl"], str):
                return jsonify({"message": "Error: Invalid value for cvprintingSnapshotUrl"}), 400
            self._settings.set(["cvprintingSnapshotUrl"], data["cvprintingSnapshotUrl"])
            if self._settings.get(["selectedWebcam"]) == "cvprinting" and self._printer.is_printing() and self._settings.get(["cvEnabled"]) and self._webcam:
                self._webcam["snapshotUrl"] = data["cvprintingSnapshotUrl"]
        if "cvprintingStreamUrl" in data.keys():
            if not isinstance(data["cvprintingStreamUrl"], str):
                return jsonify({"message": "Error: Invalid value for cvprintingStreamUrl"}), 400
            self._settings.set(["cvprintingStreamUrl"], data["cvprintingStreamUrl"])
            if self._settings.get(["selectedWebcam"]) == "cvprinting" and self._printer.is_printing() and self._settings.get(["cvEnabled"]) and self._webcam:
                self._webcam["streamUrl"] = data["cvprintingStreamUrl"]
        if "selectedWebcam" in data.keys():
            if not isinstance(data["selectedWebcam"], str):
                return jsonify({"message": "Error: Invalid value for selectedWebcam"}), 400
            self._settings.set(["selectedWebcam"], data["selectedWebcam"])
            if self._printer.is_printing() and self._settings.get(["cvEnabled"]) and self._webcam:
                webcam = self.get_current_webcam()
                self._webcam["name"] = webcam["name"]
                self._webcam["streamUrl"] = webcam["streamUrl"]
                self._webcam["snapshotUrl"] = webcam["snapshotUrl"]
        if "cvEnabled" in data.keys():
            if not isinstance(data["cvEnabled"], bool):
                return jsonify({"message": "Error: Invalid value for cvEnabled"}), 400
            tmp = self._settings.get(["cvEnabled"])
            self._settings.set(["cvEnabled"], data["cvEnabled"])
            if self._printer.is_printing() and data["cvEnabled"] and not tmp:
                self.start_monitoring()
            elif self._printer.is_printing() and not data["cvEnabled"] and tmp:
                self.stop_monitoring()
        if "discordwebhookUrl" in data.keys():
            if not isinstance(data["discordWebhookUrl"], str):
                return jsonify({"message": "Error: Invalid value for discordWebhookUrl"}), 400
            self._settings.set(["discordWebhookUrl"], data["discordWebhookUrl"])
        if "discordNotifications" in data.keys():
            if not isinstance(data["discordNotifications"], bool):
                return jsonify({"message": "Error: Invalid value for discordNotifications"}), 400
            if not self._settings.get(["discordwebhookUrl"]):
                return jsonify({"message": "Error: No webhook URL found. Can't enable notifications"}), 400
            self._settings.set(["discordNotifications"], data["discordNotifications"])
        if "telegramBotToken" in data.keys():
            if not isinstance(data["telegramBotToken"], str):
                return jsonify({"message": "Error: Invalid value for telegramBotToken"}), 400
            self._settings.set(["telegramBotToken"], data["telegramBotToken"])
        if "telegramChatId" in data.keys():
            if not isinstance(data["telegramChatId"], str):
                return jsonify({"message": "Error: Invalid value for telegramChatId"}), 400
            if not self._settings.get(["telegramBotToken"]):
                return jsonify({"message": "Error: No bot token found. Can't set chatId"}), 400
            self._settings.set(["telegramChatId"], data["telegramChatId"])
        if "telegramNotifications" in data.keys():
            if not isinstance(data["telegramNotifications"], bool):
                return jsonify({"message": "Error: Invalid value for telegramNotifications"}), 400
            if not self._settings.get(["telegramBotToken"]):
                return jsonify({"message": "Error: No bot token found. Can't enable notifications"}), 400
            if not self._settings.get(["telegramChatId"]):
                return jsonify({"message": "Error: No chat ID found. Can't enable notifications"}), 400
            self._settings.set(["telegramNotifications"], data["telegramNotifications"])
        return jsonify({"message": "Settings updated"}), 200
            
    
    def get_template_vars(self):
        return dict(currentDetection=self._currentConfidence)

    def get_assets(self):
        return dict(
            js=["js/cvprinting_settings.js", "js/cvprinting_sidebar.js"],
        )
    
    def start_monitoring(self):
        if self._running.value:
            self._logger.debug("Monitoring already running")
            return
        #Delete all images in the folder before starting monitoring
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        self._running.value = True
        self._queue = multiprocessing.Queue()
        self._queueListener = threading.Thread(target=self.queue_listener)
        self._queueListener.start()
        self._logger.debug("Queue listener started")
        if self._CVprocess:
            self._logger.debug("CV process already running")
        self._logger.debug("Starting monitoring")
        self._webcam = multiprocessing.Manager().dict()
        #Update webcam settings
        webcam = self.get_current_webcam()
        self._webcam["name"] = webcam["name"]
        self._webcam["streamUrl"] = webcam["streamUrl"]
        self._webcam["snapshotUrl"] = webcam["snapshotUrl"]
        baseFolder = self._basefolder
        self._CVprocess = multiprocessing.Process(target=Monitoring.Monitoring, kwargs={'queue': self._queue, "baseFolder" : baseFolder, "webcam" : self._webcam, "running" : self._running}, name="CVProcess")
        self._CVprocess.daemon = True
        self._CVprocess.start()

    #queue implementation to send messages to the main thread, used for logging and pausing the print
    def queue_listener(self):
        firstDetection = False
        lastWarningTime = 0
        #If print was paused due to high confidence, set the last pause time to now to avoid pausing again
        if self._pausedOnError:
            self._lastPauseTime = time.time()
            lastWarningTime = time.time()
        else:
            self._lastPauseTime = 0
        while True:
            msg_type, data = self._queue.get()
            if msg_type == "EXIT":
                break
            elif msg_type == "INFO":
                self._logger.info(data.get("message"))
            elif msg_type == "ERROR":
                self._logger.error(data.get("message"))
            elif msg_type == "DEBUG":
                self._logger.debug(data.get("message"))
            elif msg_type == "RESULT":
                image = data.get("image")
                result = data.get("result")
                if result == None:
                    firstDetection = False
                    self._currentConfidence = 0
                    os.remove(image)
                    continue
                self._currentConfidence = int(result.get("conf"))
                if int(result.get("conf")) > int(self._settings.get(["pauseThreshold"])) and self._settings.get(["pausePrintOnIssue"]):
                    #If it's the first detection, don't pause the print
                    if not firstDetection:
                        firstDetection = True
                    #If the print was paused in the last 10 minutes, don't pause again
                    elif (self._lastPauseTime + 10*60) < time.time():
                        self._logger.info("Pausing print due to high confidence")
                        self._notificationsModule.notify("Error", {"image": image, "label": result.get("label"), "conf": result.get("conf")})
                        self._printer.pause_print()
                        self._lastPauseTime = time.time()
                        self._pausedOnError = True
                elif int(result.get("conf")) > int(self._settings.get(["warningThreshold"])):
                    #If it's the first detection, don't send a warning
                    if not firstDetection:
                        firstDetection = True
                    #If warning was sent in the last 5 minutes, don't send again
                    if (lastWarningTime + 5*60) < time.time():
                        self._logger.info("Warning: " + str(result.get("label")) + " " + str(result.get("conf")))
                        self._notificationsModule.notify("Warning", {"image": image, "label": result.get("label"), "conf": result.get("conf")})
                        lastWarningTime = time.time()
                        firstDetection = False
                os.remove(image)
        self._logger.debug("Queue listener exiting")
        return
        
    def stop_monitoring(self):
        self._running.value = False
        if self._CVprocess and self._CVprocess.is_alive():
            self._logger.debug("process is alive")
            self._CVprocess.join()
            self._logger.debug("CV process exited")
            self._CVprocess = None
        else:
            self._logger.debug("CV process already exited")
            self._CVprocess = None
        if self._queueListener:
            self._queue.put(("EXIT", None))
            self._queueListener.join()
            self._logger.debug("Queue listener exited")
            self._queueListener = None
        else:
            self._logger.debug("Queue listener already exited")
        #Delete all images in the folder after stopping monitoring
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def on_settings_save(self, data):
        if self._printer.is_printing() and "cvEnabled" in data.keys():
            if not data["cvEnabled"]:
                self._logger.debug("cv was disabled while printing")
                self.stop_monitoring()
            elif data["cvEnabled"]:
                self._logger.debug("cv was enabled while printing")
                self.start_monitoring()
        for key, value in data.items():
            if key != "discordNotifications" and key != "telegramNotifications":
                self._settings.set([key], value)
        if "discordNotifications" in data.keys():
            if data["discordNotifications"]:
                if self._settings.get(["discordWebhookUrl"]):
                    self._settings.set(["discordNotifications"], True)
                else:
                    self._logger.info("Disabling discord notifications, no webhook URL found")
                    self._settings.set(["discordNotifications"], False)
            else:
                self._settings.set(["discordNotifications"], False)
        if "telegramNotifications" in data.keys():
            if data["telegramNotifications"]:
                if self._settings.get(["telegramBotToken"]) and self._settings.get(["telegramChatId"]):
                    self._settings.set(["telegramNotifications"], True)
                else:
                    self._logger.info("Disabling telegram notifications, no bot token or chat ID found")
                    self._settings.set(["telegramNotifications"], False)
            else:
                self._settings.set(["telegramNotifications"], False)
        if "selectedWebcam" in data.keys() and self._printer.is_printing() and self._settings.get(["cvEnabled"]):
            if not self._webcam:
                return
            if data["selectedWebcam"] != self._webcam["name"]:
                webcam = self.get_current_webcam()
                self._webcam["name"] = webcam["name"]
                self._webcam["streamUrl"] = webcam["streamUrl"]
                self._webcam["snapshotUrl"] = webcam["snapshotUrl"]
        if self._settings.get(["selectedWebcam"]) == "cvprinting" and self._printer.is_printing() and self._settings.get(["cvEnabled"]):
            if not self._webcam:
                return
            if "cvprintingStreamUrl" in data.keys():
                self._webcam["streamUrl"] = data["cvprintingStreamUrl"]
            if "cvprintingSnapshotUrl" in data.keys():
                self._webcam["snapshotUrl"] = data["cvprintingSnapshotUrl"]
        return data
    
    def on_event(self,event, payload):
        #If new print is started, start monitoring and reset pausedOnError flag
        if event == "PrintStarted":
            if not self._settings.get(["cvEnabled"]):
                return
            self._currentConfidence = 0
            self._pausedOnError = False
            self._logger.info("Print started")
            self.start_monitoring()
        #If the print is paused, stop monitoring
        if event == "PrintPaused":
            self._logger.info("Stopping monitoring on pause")
            self.stop_monitoring()
        #If the print is cancelled, failed or done, stop monitoring
        if event == "PrintFailed" or event == "PrintDone" or event == "PrintCancelled":
            self._logger.info("Stopping monitoring on print end")
            self.stop_monitoring()
        #If the print is resumed, start monitoring
        if event == "PrintResumed":
            if not self._settings.get(["cvEnabled"]):
                return
            self._logger.info("Print resumed")
            self.start_monitoring()

    def is_blueprint_csrf_protected(self):
        return True

__plugin_name__ = "CVPrinting"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = cvpluginInit()