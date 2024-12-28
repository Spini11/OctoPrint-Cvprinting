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

        self.onBeforeBinding = function() {
            console.log("onBeforeBinding");
            console.log(self.settings.settings.plugins.CVPrinting);
            self.warningThreshold(self.settings.settings.plugins.CVPrinting.warningTreshold());
            self.pauseThreshold(self.settings.settings.plugins.CVPrinting.pauseTreshold());
            self.pauseOnError(self.settings.settings.plugins.CVPrinting.pausePrintOnIssue());
            self.snapshotUrl(self.settings.settings.plugins.CVPrinting.snapshot_url());
            self.streamUrl(self.settings.settings.plugins.CVPrinting.stream_url());
            self.snapshotUrlSetManually(self.settings.settings.plugins.CVPrinting.snapshotUrlSetManually());
            self.streamUrlSetManually(self.settings.settings.plugins.CVPrinting.streamUrlSetManually());
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