$(function(){
    function cvprintingSettingsViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];

        self.warningThreshold = ko.observable();
        self.pauseThreshold = ko.observable();
        self.pauseOnError = ko.observable();
        self.snapshotUrl = ko.observable();
        self.streamUrl = ko.observable();
        self.snapshotUrlSetManually = ko.observable();
        self.streamUrlSetManually = ko.observable();
        self.webhookUrl = ko.observable();
        self.discordEnabled = ko.observable();

        self.onBeforeBinding = function() {
            self.warningThreshold(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.snapshotUrl(self.settings.settings.plugins.cvprinting.snapshot_url());
            self.streamUrl(self.settings.settings.plugins.cvprinting.stream_url());
            self.webhookUrl(self.settings.settings.plugins.cvprinting.discordWebhookUrl());
            self.discordEnabled(self.settings.settings.plugins.cvprinting.discordNotifications());
        };

        self.onSettingsBeforeSave = function() {
            self.settings.settings.plugins.cvprinting.warningThreshold(self.warningThreshold());
            self.settings.settings.plugins.cvprinting.pauseThreshold(self.pauseThreshold());
            self.settings.settings.plugins.cvprinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.cvprinting.discordWebhookUrl(self.webhookUrl());
            self.settings.settings.plugins.cvprinting.discordNotifications(self.discordEnabled());
            if (self.snapshotUrl() !== self.settings.settings.plugins.cvprinting.snapshot_url()) {
                self.settings.settings.plugins.cvprinting.snapshot_url(self.snapshotUrl());
                self.settings.settings.plugins.cvprinting.snapshot_url_set_manually(true);
            }
            if (self.streamUrl() !== self.settings.settings.plugins.cvprinting.stream_url()) {
                self.settings.settings.plugins.cvprinting.stream_url(self.streamUrl());
                self.settings.settings.plugins.cvprinting.stream_url_set_manually(true);
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push(
        {
            construct: cvprintingSettingsViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#cvprinting_settings"]
        }
    );
});