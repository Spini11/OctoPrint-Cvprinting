import os
from discordwebhook import Discord
import requests

class Notificationscvprinting:
    destinations = []
    discordSettings = {}
    telegramSettings = {}
    _warningTemplate = "CVPrinting has detected possible {label} with confidence {conf} which triggered a warning"
    _errorTemplate = "CVPrinting has detected possible {label} with confidence {conf} which triggered a printer PAUSE"
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
        print(data)
    
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
            embeds[0]["description"] = self._warningTemplate.format(label=data.get("label"), conf=data.get("conf"))
        elif type == "Error":
            embeds[0]["description"] = self._errorTemplate.format(label=data.get("label"), conf=data.get("conf"))
        response = None
        if data.get("image"):
            if os.path.exists(data.get("image")):
                file={"file": open(data.get("image"), "rb")}
                file_name=os.path.basename(data.get("image"))
                embeds[0]["image"] = {"url": f"attachment://{file_name}"}
                response = discord.post(embeds=embeds, file=file)
            else:
                response = discord.post(embeds=embeds)
        if response.status_code not in [200, 204]:
            self._logger.error(f"Error sending discord notification: {response.text}")
            return

    def notify_telegram(self, type, data):
        url = f"https://api.telegram.org/bot{self.telegramSettings.get('botToken')}/"
        payload = {"chat_id": self.telegramSettings.get("chatId"), "caption": ""}
        if type == "Warning":
            payload["caption"] = self._warningTemplate.format(label=data.get("label"), conf=data.get("conf"))
        elif type == "Error":
            payload["caption"] = self._errorTemplate.format(label=data.get("label"), conf=data.get("conf"))
        #Add image to payload
        response = None
        if data.get("image") and os.path.exists(data.get("image")):
            files = {"photo": open(data.get("image"), "rb")}
            response = requests.post(url + "sendPhoto", data=payload, files=files)
        else:
            payload["text"] = payload["caption"]
            response = requests.post(url + "sendMessage", data=payload)   
        if response and response.status_code != 200:
            self._logger.error(f"Error sending telegram notification: {response.text}")