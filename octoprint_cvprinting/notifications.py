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
    _settings = None

    def __init__(self, settings, logger):
        self._settings = settings
        self._logger = logger

    def getConfig(self):
        if self._settings.get(["discordNotifications"]):
            if not "discord" in self.destinations:
                self.destinations.append("discord")
        else:
            if "discord" in self.destinations:
                self.destinations.remove("discord")
        if self._settings.get(["telegramNotifications"]):
            if not "telegram" in self.destinations:
                self.destinations.append("telegram")
        else:
            if "telegram" in self.destinations:
                self.destinations.remove("telegram")
        self.discordSettings["webhookUrl"] = self._settings.get(["discordWebhookUrl"])
        self.telegramSettings["botToken"] = self._settings.get(["telegramBotToken"])
        self.telegramSettings["chatId"] = self._settings.get(["telegramChatId"])
            
        

    def notify(self, type, data):
        if type == "Test":
            if data.get("target") == "discord":
                return self.notify_discord("Test", data)
            elif data.get("target") == "telegram":
                return self.notify_telegram("Test", data)
            return
        #Update notification settings
        self.getConfig()
        if "discord" in self.destinations:
            self.notify_discord(type, data)
        if "telegram" in self.destinations:
            self.notify_telegram(type, data)
        return    
    
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
        #If type is test, change webhookURL to the supplied one
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
            self._logger.info(f"Error sending discord notification: {response.status_code} {response.text}")
            return 1
        return 0

    def notify_telegram(self, type, data):
        botToken = self.telegramSettings.get("botToken")
        payload = {"chat_id": self.telegramSettings.get("chatId"), "caption": ""}
        if type == "Warning":
            payload["caption"] = self._warningTemplate.format(label=data.get("label"), conf=data.get("conf"))
        elif type == "Error":
            payload["caption"] = self._errorTemplate.format(label=data.get("label"), conf=data.get("conf"))
        #If type is test, change token and chat_id to the supplied one
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
            self._logger.info(f"Error sending telegram notification: {response.status_code} {response.text}")
            return 1
        return 0