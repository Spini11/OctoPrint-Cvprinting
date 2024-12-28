class NotificationsCVPrinting:
    def notify(self, type, data, destinations):
        if "discord" in destinations:
            self._notify_discord(type, data)
        if "email" in destinations:
            self._notify_email(type, data)
    
    def notify_discord(self, type, data):
        if type == "Warning":