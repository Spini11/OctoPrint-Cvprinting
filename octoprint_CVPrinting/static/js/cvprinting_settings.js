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
            self.warningThreshold(self.settings.settings.plugins.CVPrinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.CVPrinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.CVPrinting.pausePrintOnIssue());
            self.snapshotUrl(self.settings.settings.plugins.CVPrinting.snapshot_url());
            self.streamUrl(self.settings.settings.plugins.CVPrinting.stream_url());
            self.webhookUrl(self.settings.settings.plugins.CVPrinting.discordWebhookUrl());
            self.discordEnabled(self.settings.settings.plugins.CVPrinting.discordNotifications());
        };

        self.onSettingsBeforeSave = function() {
            self.settings.settings.plugins.CVPrinting.warningThreshold(self.warningThreshold());
            self.settings.settings.plugins.CVPrinting.pauseThreshold(self.pauseThreshold());
            self.settings.settings.plugins.CVPrinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.CVPrinting.discordWebhookUrl(self.webhookUrl());
            self.settings.settings.plugins.CVPrinting.discordNotifications(self.discordEnabled());
            if (self.snapshotUrl() !== self.settings.settings.plugins.CVPrinting.snapshot_url()) {
                self.settings.settings.plugins.CVPrinting.snapshot_url(self.snapshotUrl());
                self.settings.settings.plugins.CVPrinting.snapshot_url_set_manually(true);
            }
            if (self.streamUrl() !== self.settings.settings.plugins.CVPrinting.stream_url()) {
                self.settings.settings.plugins.CVPrinting.stream_url(self.streamUrl());
                self.settings.settings.plugins.CVPrinting.stream_url_set_manually(true);
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