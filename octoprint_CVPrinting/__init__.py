import os
import time
import octoprint.plugin
from pathlib import Path
from octoprint.schema.webcam import Webcam, WebcamCompatibility
import yaml

class CVPluginInit(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.WebcamProviderPlugin,
                       octoprint.plugin.AssetPlugin):
    def on_after_startup(self):
        # Print all the current settings
        self._logger.info("CVPrinting plugin started!")
        self._logger.info("Current settings: PausePrint: %s  PauseTreshold %s  WarningTeshold %s  snapshotUrl %s streamUrl %s snapshotManual %s streamManual %s" % (self._settings.get(["pausePrintOnIssue"]), self._settings.get(["pauseTreshold"]), self._settings.get(["warningTreshold"]), self._settings.get(["snapshot_url"]), self._settings.get(["stream_url"]), self._settings.get(["snapshotUrlSetManually"]), self._settings.get(["streamUrlSetManually"])))
        webcam = self.get_webcam_configurations()
        if(self._settings.get(["snapshotUrlSetManually"]) == False):
            self._settings.set(["snapshot_url"], webcam[0].compat.snapshot)
        if(self._settings.get(["streamUrlSetManually"]) == False):
            self._settings.set(["stream_url"], webcam[0].compat.stream)
    
    def get_settings_defaults(self):
        return dict(pausePrintOnIssue=False, pauseTreshold=0.8, warningTreshold=0.5, snapshot_url="", stream_url="", snapshotUrlSetManually=False, streamUrlSetManually=False)

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

    def get_assets(self):
        return dict(
            js=["js/cvprinting_settings.js"],
        )

__plugin_name__ = "CVPrinting"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = CVPluginInit()