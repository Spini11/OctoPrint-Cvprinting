import os
import time
import threading

from flask import jsonify
import octoprint.plugin
from pathlib import Path
from octoprint.schema.webcam import Webcam, WebcamCompatibility
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
                       octoprint.plugin.BlueprintPlugin):
    _notificationsModule = None
    _lastDetection = 0
    _lastPause = 0
    _running = False
    _thread = None
    _currentJob = None
    _pausedOnError = False
    _currentDetection = 0


    def on_after_startup(self):
        self._logger.info("cvprinting plugin started!")
        webcam = self.get_webcam_configurations()
        self._logger.info(webcam[0].compat.snapshot)
        #Unless user has set the snapshot and stream URL manually, use the ones from the classic webcam plugin
        self._logger.info("Plugin test")
        self._logger.info(self._settings.get(["snapshotUrlSetManually"]))
        if(self._settings.get(["snapshotUrlSetManually"]) == False):
            self._settings.set(["snapshot_url"], webcam[0].compat.snapshot)
            self._logger.info("Snapshot URL set")
            self._logger.info(self._settings.get(["snapshot_url"]))
        if(self._settings.get(["streamUrlSetManually"]) == False):
            self._settings.set(["stream_url"], webcam[0].compat.stream)
        #Initialize the notifications module
        self._notificationsModule = notifications.Notificationscvprinting(self._settings.get(["discordNotifications"]),self._settings.get(["discordWebhookUrl"]))
        #Create folder for storing images
        os.makedirs(os.path.join(self._basefolder, 'data/images'), exist_ok=True)


    def get_settings_defaults(self):
        return dict(pausePrintOnIssue=False, pauseThreshold=80, warningThreshold=50, snapshot_url="", stream_url="", snapshotUrlSetManually=False, streamUrlSetManually=False, discordNotifications=False, discordWebhookUrl="")

    def get_webcam_configurations(self):
        urls = self.get_webcam_links()
        return [
            Webcam(
                name="cvprinting",
                displayName="Classic webcam",
                canSnapshot=True,
                compat=WebcamCompatibility(
                    snapshot=urls.get("snapshot_url"),
                    stream=urls.get("stream_url"),
                ),
            )
        ]
    
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True, template="cvprinting_settings.jinja2"),
            dict(type="sidebar", custom_bindings=True, template="cvprinting_sidebar.jinja2"),
        ]
    
    @octoprint.plugin.BlueprintPlugin.route("/get_variable", methods=["GET"])
    def get_variable(self):
        return jsonify({"variable": self._currentDetection})
    
    def get_template_vars(self):
        return dict(currentDetection=self._currentDetection)

    def get_assets(self):
        return dict(
            js=["js/cvprinting_settings.js", "js/cvprinting_sidebar.js"],
        )

    def get_webcam_links(self):
        configLocation = self.get_config_location()
        try:
            with open(configLocation, "r") as file:
                config = yaml.safe_load(file)
            classicwebcam_config = config.get("plugins", {}).get("classicwebcam", {})
            snapshot_url = classicwebcam_config.get("snapshot")
            stream_url = classicwebcam_config.get("stream")
            return dict(snapshot_url=snapshot_url, stream_url=stream_url)
        except FileNotFoundError:
            self._logger.error(f"Config file not found at {configLocation}")
            return dict(snapshot_url="", stream_url="")
        except yaml.YAMLError as e:
            self._logger.error(f"Error parsing config file: {e}")
            return dict(snapshot_url="", stream_url="")

    
    def get_config_location(self):
        return Path(self.get_plugin_data_folder()).parent.parent.joinpath("config.yaml")
    
    def start_monitoring(self):
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self.monitor)
        self._thread.start()
    
    def monitor(self):
        while self._running:
            #Call vision module to check the image for printing errors
            image, result = visionModule.CheckImage(self._settings.get(["snapshot_url"]), os.path.join(self._basefolder, 'data'))
            if result == 1:
                self._logger.error("Error downloading image")
                time.sleep(5)
                continue
            elif result == 2:
                self._logger.error("Error processing image")
                time.sleep(5)
                continue
                    #Convert confidence to percentage 
            if not result:
                self._currentDetection = 0
                time.sleep(5)
                continue
            conf = result.get("conf") * 100
            self._currentDetection = conf
            print(self._currentDetection)
            #If the confidence is above the pause threshold, send a notification, pause the print 
            if conf > float(self._settings.get(["pauseThreshold"])) and float(self._settings.get(["pausePrintOnIssue"])):
                #If the last pause was more than 10 minutes ago, send a notification and pause the print
                if((self._lastPause + 10*60) < time.time()):
                    self._lastPause = time.time()
                    self._notificationsModule.notify("Error", {"message": "Possible issue detected", "image": image})
                    self._pausedOnError = True
                    self._printer.pause_print()
                    break
                #If the last pause was less than 10 minutes ago, update the last pause time to prevent repeated pause on false positives
                else:
                    self._lastPause = time.time()
            #If the confidence is above the warning threshold, send a notification
            elif conf > float(self._settings.get(["warningThreshold"])):
                #If the last detection was more than 5 minutes ago, send a notification
                if((self._lastDetection + 5*60) < time.time()):
                    self._lastDetection = time.time()
                    self._notificationsModule.notify("Warning", {"message": "Possible issue detected", "image": image})
                #If the last detection was less than 5 minutes ago, update the last detection time to prevent repeated notifications
                else:
                    self._lastDetection = time.time()
            #Delete the image after processing and wait for 5 seconds before checking the next image
            os.remove(image)
            time.sleep(5)

    def stop_monitoring(self):
        for filename in os.listdir(os.path.join(self._basefolder, 'data/images/')):
            file_path = os.path.join(os.path.join(self._basefolder, 'data/images/'), filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def on_settings_save(self, data):
        if "discordWebhookUrl" in data.keys():
            self._logger.info("Discord webhook URL updated")
            self._notificationsModule.discordSettings["webhookUrl"] = data["discordWebhookUrl"]
        if "discordNotifications" in data.keys():
            if data["discordNotifications"]:
                #If the discord webhook URL is not set, don't enable discord notifications
                if not self._notificationsModule.discordSettings.get("webhookUrl"):
                    self._logger.info("Discord webhook URL not set")
                    data["discordNotifications"] = False
                else:
                    self._logger.info("Discord notifications enabled")
                    self._notificationsModule.destinations.append("discord")
            else:
                self._logger.info("Discord notifications disabled")
                self._notificationsModule.destinations.remove("discord")
        #Save the data
        for key, value in data.items():
            self._settings.set([key], value)
        return data
    
    def on_event(self,event, payload):
        #If the print is started, start monitoring
        if event == "PrintStarted":
            self._logger.info("Print started")
            self.start_monitoring()
        #If the print is done, failed, paused or cancelled, stop monitoring
        if event == "PrintPaused":
            self._logger.info("Stopping monitoring")
            self.stop_monitoring()
        if event == "PrintFailed" or event == "PrintDone" or event == "PrintCancelled":
            self._logger.info("Stopping monitoring")
            self.stop_monitoring()
            self._pausedOnError = False
            self._lastDetection = 0
            self._lastPause = 0

        #If the print is resumed, start monitoring
        if event == "PrintResumed":
            self._logger.info("Print resumed")
            #If the print was paused due to an error, reset the pause flag and update the last detection time to prevent repeated notifications and pauses on false positives
            if self._pausedOnError:
                self._pausedOnError = False
                self._lastDetection = time.time()
                self._lastPause = time.time()
            self.start_monitoring()

__plugin_name__ = "CVPrinting"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = cvpluginInit()