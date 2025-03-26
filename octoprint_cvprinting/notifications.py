import os
from discordwebhook import Discord
import requests

class Notificationscvprinting:
    destinations = []
    discordSettings = {}
    telegramSettings = {}
    _warningTemplate = "CVPrinting has detected possible {label} with confidence {conf:.0f} which triggered a warning"
    _errorTemplate = "CVPrinting has detected possible {label} with confidence {conf:.0f} which triggered a printer PAUSE"
    _testTemplate = "This is a test notification"
    _main = None
    _logger = None

    def __init__(self, notificationsConfig, logger):
        if notificationsConfig:
            self.discordSettings = notificationsConfig.get("discord")
            self.telegramSettings = notificationsConfig.get("telegram")
            if self.discordSettings.get("enabled"):
                self.destinations.append("discord")
            elif "discord" in self.destinations:
                self.destinations.remove("discord")
            if self.telegramSettings.get("enabled"):
                self.destinations.append("telegram")
            elif "telegram" in self.destinations:
                self.destinations.remove("telegram")
        self._logger = logger
            
        

    def notify(self, type, data):
        response = []
        if type == "Test":
            if data.get("target") == "discord":
                code, message = self.notify_discord("Test", data)
                if code != 0:
                    self._logger.info(message)
            elif data.get("target") == "telegram":
                code, message = self.notify_telegram("Test", data)
                if code != 0:
                    self._logger.info(message)
            return
        if "discord" in self.destinations:
            code, message = self.notify_discord(type, data)
            if code != 0:
                response.append(message)
        if "telegram" in self.destinations:
            code, message = self.notify_telegram(type, data)    
            if code != 0:
                response.append(message)
        return response
    
    def notify_discord(self, type, data):
        file = None
        webhookUrl = self.discordSettings.get("webhookUrl")
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
        elif type == "Test":
            embeds[0]["description"] = self._testTemplate
            embeds[0]["title"] = "Test notification"
            webhookUrl = data.get("webhook_url")
        discord = Discord(url=webhookUrl)
        response = None
        if data.get("image") and os.path.exists(data.get("image")):
            file={"file": open(data.get("image"), "rb")}
            file_name=os.path.basename(data.get("image"))
            embeds[0]["image"] = {"url": f"attachment://{file_name}"}
            response = discord.post(embeds=embeds, file=file)
        else:
            response = discord.post(embeds=embeds)
        if response.status_code not in [200, 204]:
            return 1, f"Error sending discord notification: {response.text}"
        return 0, None

    def notify_telegram(self, type, data):
        botToken = self.telegramSettings.get("botToken")
        payload = {"chat_id": self.telegramSettings.get("chatId"), "caption": ""}
        if type == "Warning":
            payload["caption"] = self._warningTemplate.format(label=data.get("label"), conf=data.get("conf"))
        elif type == "Error":
            payload["caption"] = self._errorTemplate.format(label=data.get("label"), conf=data.get("conf"))
        elif type == "Test":
            payload["caption"] = self._testTemplate
            botToken = data.get("token")
            payload["chat_id"] = data.get("chat_id")
        #Add image to payload
        url = f"https://api.telegram.org/bot{botToken}/"
        response = None
        if data.get("image") and os.path.exists(data.get("image")):
            files = {"photo": open(data.get("image"), "rb")}
            response = requests.post(url + "sendPhoto", data=payload, files=files)
        else:
            payload["text"] = payload["caption"]
            response = requests.post(url + "sendMessage", data=payload)
        if not response or response.status_code != 200:
            print(response.text)
            return 1, f"Error sending telegram notification: {response.text}"
        return 0, None