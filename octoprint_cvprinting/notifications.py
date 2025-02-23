import os
from discordwebhook import Discord
import requests

class Notificationscvprinting:
    destinations = []
    discordSettings = {}
    telegramSettings = {}
    _main = None
    _logger = None

    def __init__(self, notificationsConfig, logger):
        self.discordSettings = notificationsConfig.get("discord")
        self.telegramSettings = notificationsConfig.get("telegram")
        if self.discordSettings.get("enabled"):
            self.destinations.append("discord")
        if self.telegramSettings.get("enabled"):
            self.destinations.append("telegram")
        self._logger = logger
            
        

    def notify(self, type, data):
        if "discord" in self.destinations:
            self.notify_discord(type, data)
        if "telegram" in self.destinations:
            self.notify_telegram(type, data)
    
    def notify_discord(self, type, data):
        file = None
        discord = Discord(url=self.discordSettings.get("webhookUrl"))
        embeds=[
            {
                "author": {
                    "name": "CVPrinting",
                },
                "title": "Possible issue detected",
            },
                ]
        if type == "Warning":
            embeds[0]["description"] = "Possible issue triggered a warning"
        elif type == "Error":
            embeds[0]["description"] = "Issue triggered a printer pause"
        response = discord.post(embeds=embeds)
        if response.status_code not in [200, 204]:
            self._logger.error(f"Error sending discord notification: {response.text}")
            return
        if data.get("image"):
            with open(data.get("image"), "rb") as image_file:
                response = discord.post(file={"file": image_file})
        if response.status_code != 200:
            self._logger.error(f"Error sending discord notification: {response.text}")

    def notify_telegram(self, type, data):
        url = f"https://api.telegram.org/bot{self.telegramSettings.get('botToken')}/sendPhoto"
        payload = {"chat_id": self.telegramSettings.get("chatId"), "caption": ""}
        if type == "Warning":
            payload["caption"] = f"CVPrinting: {data.get('message')}\nPossible issue triggered a warning"
        elif type == "Error":
            payload["caption"] = f"CVPrinting: {data.get('message')}\nIssue triggered a printer pause"
        #Add image to payload
        response = None
        if data.get("image"):
            with open(data.get("image"), "rb") as image_file:
                files = {"photo": image_file}
                response = requests.post(url, data=payload, files=files)
        else:
            response = requests.post(url, data=payload)
        
        if response and response.status_code != 200:
            self._logger.error(f"Error sending telegram notification: {response.text}")