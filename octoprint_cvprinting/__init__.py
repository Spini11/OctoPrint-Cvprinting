import multiprocessing
import os
import time
import flask
import threading

from flask import jsonify
import octoprint.plugin
from pathlib import Path
from octoprint.schema.webcam import Webcam, WebcamCompatibility
import octoprint.webcams
import yaml
import requests
from . import visionModule
from . import notifications

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

    #Need to be passed into the cv process

    #lastPauseTime = 0, lastDetectionTime = 1, currentConfidence = 2, pauseThreshold = 3, warningThreshold = 4
    _floatArray = multiprocessing.Array('d', [0] *5)

    #pausePrintOnIssue = 0, running = 1, pausedOnError = 2
    _flagsArray = multiprocessing.Array('b', [False] * 3)


    _discordSettings = multiprocessing.Manager().dict({"enabled": False, "webhookUrl": ""})
    _telegramSettings = multiprocessing.Manager().dict({"enabled": False, "botToken": "", "chatId": ""})
    _currentWebcam = multiprocessing.Manager().dict({"name": "", "streamUrl": "", "snapshotUrl": ""})

    def on_after_startup(self):
        self._logger.info("CVPrinting started")
        self._notificationsModule = notifications.Notificationscvprinting(None, self._logger)
        self.initConfigurations()
        #Create folder for storing images
        os.makedirs(os.path.join(self._basefolder, 'data/images'), exist_ok=True)

    def initConfigurations(self):
        self._discordSettings["enabled"] = self._settings.get(["discordNotifications"])
        self._discordSettings["webhookUrl"] = self._settings.get(["discordWebhookUrl"])
        self._telegramSettings["enabled"] = self._settings.get(["telegramNotifications"])
        self._telegramSettings["botToken"] = self._settings.get(["telegramBotToken"])
        self._telegramSettings["chatId"] = self._settings.get(["telegramChatId"])

        webcam = self.get_current_webcam()
        self._currentWebcam["name"] = webcam["name"]
        self._currentWebcam["streamUrl"] = webcam["streamUrl"]
        self._currentWebcam["snapshotUrl"] = webcam["snapshotUrl"]

        self._floatArray[3] = int(self._settings.get(["pauseThreshold"]))
        self._floatArray[4] = int(self._settings.get(["warningThreshold"]))
        self._flagsArray[0] = self._settings.get(["pausePrintOnIssue"])

    def on_shutdown(self):
        #Make sure monitoring process and listener thread are stopped
        self.stop_monitoring()
        #Delete all images in the folder
        image_folder = os.path.join(self._basefolder, 'data/images')
        for filename in os.listdir(image_folder):
            file_path = os.path.join(image_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        self._logger.info("CVPrinting stoped")


    def get_settings_defaults(self):
        return dict(pausePrintOnIssue=False, pauseThreshold=80, warningThreshold=50, cvprintingSnapshotUrl="", cvprintingStreamUrl="", discordNotifications=False, discordWebhookUrl="", selectedWebcam="classic", telegramNotifications=False, telegramBotToken="", telegramChatId="")

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
        return jsonify({"variable": self._floatArray[2]})
    
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
            
    
    def get_template_vars(self):
        return dict(currentDetection=self._floatArray[2])

    def get_assets(self):
        return dict(
            js=["js/cvprinting_settings.js", "js/cvprinting_sidebar.js"],
        )
    
    def start_monitoring(self):
        #If the monitoring thread is already running, return
        if self._flagsArray[1]:
            print("Monitoring already running")
            return
        #Delete all images in the folder before starting monitoring
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        with multiprocessing.Manager() as manager:  
            self._flagsArray[1] = True
            self._queue = multiprocessing.Queue()
            self._queueListener = threading.Thread(target=self.queue_listener, args=(self._queue,))
            self._queueListener.daemon = True
            self._queueListener.start()
            print("Queue listener started")
            if self._CVprocess:
                print("CV process already running")
            print("Starting monitoring")
            self._CVprocess = multiprocessing.Process(target=self.monitor, args=(self._currentWebcam, self._basefolder, self._discordSettings, self._telegramSettings, self._floatArray, self._flagsArray, self._queue,))
            self._CVprocess.start()
            print("Monitoring started")

    #queue implementation to send messages to the main thread, used for logging and pausing the print
    def queue_listener(self, queue):
        print("Queue listener starting")
        print(self._flagsArray[1])
        while self._flagsArray[1]:
            msg_type, data = queue.get()
            if msg_type == "EXIT":
                break
            if msg_type == "pause":
                #set the pausedOnError flag to true
                self._flagsArray[2] = True
                self._logger.info("Pausing print due to high confidence value")
                self._printer.pause_print()
            elif msg_type == "INFO":
                self._logger.info(data)
            elif msg_type == "ERROR":
                self._logger.error(data)
                                        
    def monitor(self, webcam, basefolder, discordSettings, telegramSettings, intArray, flagsArray, queue):
        intArray[2] = 0 #currentConfidence
        #If pausedOnError is true, update lastPauseTime and lastDetectionTime, otherwise set them to 0
        if flagsArray[2]:
            intArray[0] = time.time() #lastPauseTime
            intArray[1] = time.time() #lastDetectionTime
        else:
            intArray[0] = 0 #lastPauseTime
            intArray[1] = 0 #lastDetectionTime
        flagsArray[2] = False #pausedOnError
        notificationsconfig = {"discord": discordSettings, "telegram": telegramSettings}
        print("Initializing notifications module")
        notificationsModule = notifications.Notificationscvprinting(notificationsconfig,  None)
        print("Initializing vision module")
        visionModuleInstance = visionModule.visionModule(basefolder)
        lastConfidence = 0
        #flagsArray[1] is the running flag
        while flagsArray[1]:
            #Update the notifications module with the new settings
            print(discordSettings)
            notificationsconfig = {"discord": discordSettings, "telegram": telegramSettings}
            notificationsModule = notifications.Notificationscvprinting(notificationsconfig,  None)
            if not webcam:
                queue.put(("ERROR", "No webcam selected"))
                time.sleep(5)
                continue
            image, result = visionModuleInstance.CheckImage(webcam.get("snapshotUrl"))
            if result == 1:
                print("Error getting image")
                queue.put(("ERROR", "Error getting image"))
                time.sleep(5)
                continue
            if result == 2:
                print("Error processing image")
                queue.put(("ERROR", "Error processing image"))
                time.sleep(5)
                continue
            #intArray[2] is the current confidence value
            lastConfidence = intArray[2]
            if not result:
                intArray[2] = 0
                os.remove(image)
                time.sleep(5)
                continue
            intArray[2] = result.get("conf")
            #intArray[3] is the pause threshold, flagsArray[0] is the pauseOnError flag
            print("curr conf" + str(intArray[2]))
            print("pause threshold" + str(intArray[3]))
            print("pause flag" + str(flagsArray[0]))
            if intArray[2] > intArray[3] and flagsArray[0]:
                print("first if passsed")
                if lastConfidence < intArray[3]:
                    print("second if passed")
                    os.remove(image)
                    time.sleep(1)
                    continue
                #intArray[0] is the last pause time
                if (intArray[0] + 10*60) < time.time():
                    print("time if passed")
                    intArray[0] = time.time()
                    response = notificationsModule.notify("Error", {"image": image, "conf": intArray[2], "label": result.get("label")})
                    if response:
                        for message in response:
                            queue.put(("INFO", message))
                    queue.put(("pause", None))
                    break
            #intArray[4] is the warning threshold
            elif intArray[2] > intArray[4]:
                if lastConfidence < intArray[4]:
                    os.remove(image)
                    time.sleep(1)
                    continue
                #intArray[1] is the last detection time
                if (intArray[1] + 5*60) < time.time():
                    intArray[1] = time.time()
                    response = notificationsModule.notify("Warning", {"image": image, "conf": intArray[2], "label": result.get("label")})
                    if response:
                        for message in response:
                            queue.put(("INFO", message))
            os.remove(image)
            time.sleep(5)
        queue.put(("EXIT", None))
        return
            

    def stop_monitoring(self):
        self._flagsArray[1] = False
        if self._CVprocess:
            self._CVprocess.join()
            print("CV process exited")
            self._CVprocess = None
        else:
            print("CV process already exited")
        if self._queueListener:
            self._queue.put(("EXIT", None))
            self._queueListener.join()
            print("Queue listener exited")
            self._queueListener = None
        else:
            print("Queue listener already exited")
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)


    def on_settings_save(self, data):
        for key, value in data.items():
            print (key, value)
        if "discordWebhookUrl" in data.keys():
            self._discordSettings["webhookUrl"] = data["discordWebhookUrl"]
        if "discordNotifications" in data.keys():
            print("discordNotifications in data")
            print(data["discordNotifications"])
            if data["discordNotifications"]:
                #If the discord webhook URL is not set, don't enable discord notifications
                if not self._discordSettings.get("webhookUrl"):
                    self._logger.info("Discord webhook URL not set")
                    data["discordNotifications"] = False
                    self._discordSettings["enabled"] = False
                else:
                    self._logger.info("Discord notifications enabled")
                    self._discordSettings["enabled"] = True
            else:
                self._logger.info("Discord notifications disabled")
                self._discordSettings["enabled"] = False
        if "telegramBotToken" in data.keys():
            self._telegramSettings["botToken"] = data["telegramBotToken"]
        if "telegramChatId" in data.keys():
            if not self._telegramSettings.get("botToken"):
                self._logger.info("Telegram bot token not set")
                data["telegramChatId"] = ""
                self._telegramSettings["chatId"] = ""
            else:
                self._telegramSettings["chatId"] = data["telegramChatId"]  
        if "telegramNotifications" in data.keys():
            if data["telegramNotifications"]:
                if self._telegramSettings.get("botToken") and self._telegramSettings.get("chatId"):
                    self._telegramSettings["enabled"] = data["telegramNotifications"]
                else:
                    self._logger.info("Telegram bot token or chat ID not set")
                    data["telegramNotifications"] = False
                    self._telegramSettings["enabled"] = False
            else:
                self._telegramSettings["enabled"] = data["telegramNotifications"] 
        if "selectedWebcam" in data.keys():
            self._currentWebcam["name"] = data["selectedWebcam"]
            if data["selectedWebcam"] == "classic":
                webcams = self.get_webcam_list()
                for webcam in webcams:
                    if webcam["name"] == "classic":
                        self._currentWebcam["streamUrl"] = webcam["streamUrl"]
                        self._currentWebcam["snapshotUrl"] = webcam["snapshotUrl"]
            elif data["selectedWebcam"] == "cvprinting":
                if "cvprintingStreamUrl" in data.keys():
                    self._currentWebcam["streamUrl"] = data["cvprintingStreamUrl"]
                else:
                    self._currentWebcam["streamUrl"] = self._settings.get(["cvprintingStreamUrl"])
                if "cvprintingSnapshotUrl" in data.keys():
                    self._currentWebcam["snapshotUrl"] = data["cvprintingSnapshotUrl"]
                else:
                    self._currentWebcam["snapshotUrl"] = self._settings.get(["cvprintingSnapshotUrl"])
        elif self._settings.get(["selectedWebcam"]) == "cvprinting":
            if "cvprintingStreamUrl" in data.keys():
                self._currentWebcam["streamUrl"] = data["cvprintingStreamUrl"]
            if "cvprintingSnapshotUrl" in data.keys():
                self._currentWebcam["snapshotUrl"] = data["cvprintingSnapshotUrl"]
        if "pausePrintOnIssue" in data.keys():
            self._flagsArray[0] = data["pausePrintOnIssue"]
        if "pauseThreshold" in data.keys():
            self._floatArray[3] = int(data["pauseThreshold"])
        if "warningThreshold" in data.keys():
            self._floatArray[4] = int(data["warningThreshold"])
        #Save the new values to settings
        for key, value in data.items():
            self._settings.set([key], value)
        return data
    
    def on_event(self,event, payload):
        #If the print is started, start monitoring
        if event == "PrintStarted":
            self._logger.info("Print started")
            self.start_monitoring()
        #If the print is paused, stop monitoring
        if event == "PrintPaused":
            self._logger.info("Stopping monitoring")
            self.stop_monitoring()
        #If the print is cancelled, failed or done, stop monitoring and reset pausedOnError
        if event == "PrintFailed" or event == "PrintDone" or event == "PrintCancelled":
            self._logger.info("Stopping monitoring")
            self.stop_monitoring()
            self._flagsArray[2] = False
        #If the print is resumed, start monitoring
        if event == "PrintResumed":
            self._logger.info("Print resumed")
            self.start_monitoring()

    def is_blueprint_csrf_protected(self):
        return True

__plugin_name__ = "CVPrinting"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = cvpluginInit()