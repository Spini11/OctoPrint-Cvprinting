import os
import time
import threading
import octoprint.plugin
from pathlib import Path
from octoprint.schema.webcam import Webcam, WebcamCompatibility
import yaml
import requests
from . import visionModule
from . import notifications

class CVPluginInit(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.WebcamProviderPlugin,
                       octoprint.plugin.AssetPlugin,
                       octoprint.plugin.EventHandlerPlugin):
    notificationsModule = None
    def on_after_startup(self):
        # Print all the current settings
        self._running = False
        self._thread = None
        self._logger.info("CVPrinting plugin started!")
        #self._logger.info("Current settings: PausePrint: %s  PauseThreshold %s  WarningTeshold %s  snapshotUrl %s streamUrl %s snapshotManual %s streamManual %s" % (self._settings.get(["pausePrintOnIssue"]), self._settings.get(["pauseThreshold"]), self._settings.get(["warningThreshold"]), self._settings.get(["snapshot_url"]), self._settings.get(["stream_url"]), self._settings.get(["snapshotUrlSetManually"]), self._settings.get(["streamUrlSetManually"])))
        self._logger.info(self.get_plugin_data_folder())
        self._logger.info(self._data_folder)
        self._logger.info(self._basefolder)
        webcam = self.get_webcam_configurations()
        if(self._settings.get(["snapshotUrlSetManually"]) == False):
            self._settings.set(["snapshot_url"], webcam[0].compat.snapshot)
        if(self._settings.get(["streamUrlSetManually"]) == False):
            self._settings.set(["stream_url"], webcam[0].compat.stream)
        self.notificationsModule = notifications.NotificationsCVPrinting(self._settings.get(["discordNotifications"]),self._settings.get(["discordWebhookUrl"]))
        print("type of settings")
        print(type(self._settings))


    def get_settings_defaults(self):
        return dict(pausePrintOnIssue=False, pauseThreshold=80, warningThreshold=50, snapshot_url="", stream_url="", snapshotUrlSetManually=False, streamUrlSetManually=False, discordNotifications=False, discordWebhookUrl="")

    def get_webcam_configurations(self):
        urls = self.get_webcam_links()
        return [
            Webcam(
                name="CVPrinting",
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
        ]

    def get_assets(self):
        return dict(
            js=["js/cvprinting_settings.js"],
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
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self.monitor)
        self._thread.start()
    
    def monitor(self):
        while self._running:
            image, result = visionModule.CheckImage(self._settings.get(["snapshot_url"]), self._basefolder)
            #Print pauseThreshold and warningThreshold
            self._logger.info(f"PauseThreshold: {self._settings.get(['pauseThreshold'])} WarningThreshold: {self._settings.get(['warningThreshold'])}")
            for r in result:
                 # Get the confidence and class index
                confidences = r.boxes.conf
                class_ids = r.boxes.cls 

                # Iterate through detected boxes
                for conf, cls in zip(confidences, class_ids):
                    #Convert confidence to percentage 
                    conf = conf*100
                    label = r.names[int(cls)]

                    self._logger.info(f"Confidence: {conf} {label}")
                    if conf > float(self._settings.get(["pauseThreshold"])) and label == "PrintNotOk" and float(self._settings.get(["pausePrintOnIssue"])):
                        self._logger.info("Pausing print due to high confidence")
                        self.notificationsModule.notify("Error", {"message": "Possible issue detected", "image": image})
                        self._printer.pause_print()
                        break
                    elif conf > float(self._settings.get(["warningThreshold"])) and label == "PrintNotOk":
                        self._logger.info("High confidence detected for PrintNotOk")
                        self.notificationsModule.notify("Warning", {"message": "Possible issue detected", "image": image})
            os.remove(image)
            time.sleep(5)

    def stop_monitoring(self):
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def on_settings_save(self, data):
        self._logger.info(data)
        if "discordWebhookUrl" in data.keys():
            self._logger.info("Discord webhook URL updated")
            self.notificationsModule.discordSettings["webhookUrl"] = data["discordWebhookUrl"]
        if "discordNotifications" in data.keys():
            if data["discordNotifications"]:
                if not self.notificationsModule.discordSettings.get("webhookUrl"):
                    self._logger.info("Discord webhook URL not set")
                else:
                    self._logger.info("Discord notifications enabled")
                    self.notificationsModule.destinations.append("discord")
            else:
                self._logger.info("Discord notifications disabled")
                self.notificationsModule.destinations.remove("discord")
        #Save the data
        for key, value in data.items():
            self._settings.set([key], value)
        return data
    
    def on_event(self,event, payload):
        if event == "PrintStarted":
            self._logger.info("Print started")
            self.start_monitoring()
        if event == "PrintFailed":
            self._logger.info("Print failed")
            self.stop_monitoring()
        if event == "PrintDone":
            self._logger.info("Print done")
            self.stop_monitoring()
        if event == "PrintPaused":
            self._logger.info("Print paused")
            self.stop_monitoring()
        if event == "PrintResumed":
            self._logger.info("Print resumed")
            self.start_monitoring()
        if event == "PrintCancelled":
            self._logger.info("Print cancelled")
            self.stop_monitoring()
        if event == "SettingsUpdated":
            self._logger.info("Settings updated")

__plugin_name__ = "CVPrinting"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = CVPluginInit()