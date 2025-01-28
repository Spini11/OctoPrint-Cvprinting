from discordwebhook import Discord

class Notificationscvprinting:
    destinations = []
    discordSettings = {}
    folder = ""

    def __init__(self,dicordEnabled, discordWebhookUrl):
            self.discordSettings["webhookUrl"] = discordWebhookUrl
            if dicordEnabled:
                self.destinations.append("discord")
        

    def notify(self, type, data):
        if "discord" in self.destinations:
            self.notify_discord(type, data)
    
    def notify_discord(self, type, data):
        print(self.discordSettings)
        if type == "Warning":
            discord = Discord(url=self.discordSettings.get("webhookUrl"))
            discord.post(embeds=[
            {
                "author": {
                    "name": "CVPrinting",
                },
                "title": f"{data.get('message')}",
                "description": "Possible issue triggered a warning",
            },
                ],)
            discord.post(file={"file": open(data.get("image"), "rb")})
        elif type == "Error":
            discord = Discord(url=self.discordSettings.get("webhookUrl"))
            discord.post(embeds=[
            {
                "author": {
                    "name": "CVPrinting",
                },
                "title": f"{data.get('message')}",
                "description": "Issue triggered a printer pause",
            },
                ],)
            discord.post(file={"file": open(data.get("image"), "rb")})