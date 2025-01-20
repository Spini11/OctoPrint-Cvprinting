$(function(){
    function cvprintingSettingsViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];

        self.warningThreshold = ko.observable();
        self.pauseThreshold = ko.observable();
        self.pauseOnError = ko.observable();
        self.cvprintingSnapshotUrl = ko.observable();
        self.cvprintingStreamUrl = ko.observable();
        self.webhookUrl = ko.observable();
        self.discordEnabled = ko.observable();
        self.selectedWebcam = ko.observable();
        self.classicSnapshotUrl = ko.observable();
        self.classicStreamUrl = ko.observable();
        self.currentStream = ko.observable();

        self.onBeforeBinding = function() {
            self.warningThreshold(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.cvprintingSnapshotUrl(self.settings.settings.plugins.cvprinting.cvprintingSnapshotUrl());
            self.cvprintingStreamUrl(self.settings.settings.plugins.cvprinting.cvprintingStreamUrl());
            self.webhookUrl(self.settings.settings.plugins.cvprinting.discordWebhookUrl());
            self.discordEnabled(self.settings.settings.plugins.cvprinting.discordNotifications());
            self.selectedWebcam(self.settings.settings.plugins.cvprinting.selectedWebcam());
        };

        self.onSettingsShown = function() {
            self.warningThreshold(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.selectedWebcam(self.settings.settings.plugins.cvprinting.selectedWebcam());
            getWebcams().then(webcams => {
                webcams.forEach(element => {
                    if (element.name === "classic")
                    {
                        self.classicSnapshotUrl(element.snapshotUrl);
                        self.classicStreamUrl(element.streamUrl);
                        if(self.selectedWebcam() === "classic")
                            self.currentStream(self.classicStreamUrl());
                    }
                    
                });
            });
            if (self.selectedWebcam() === "cvprinting"){
                self.currentStream(self.cvprintingStreamUrl());
            }
        };

        self.onSettingsBeforeSave = function() {
            self.settings.settings.plugins.cvprinting.warningThreshold(self.warningThreshold());
            self.settings.settings.plugins.cvprinting.pauseThreshold(self.pauseThreshold());
            self.settings.settings.plugins.cvprinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.cvprinting.discordWebhookUrl(self.webhookUrl());
            self.settings.settings.plugins.cvprinting.discordNotifications(self.discordEnabled());
            self.settings.settings.plugins.cvprinting.cvprintingSnapshotUrl(self.cvprintingSnapshotUrl());
            self.settings.settings.plugins.cvprinting.cvprintingStreamUrl(self.cvprintingStreamUrl());
            if (self.selectedWebcam() === "classic")
                self.settings.settings.plugins.cvprinting.selectedWebcam("classic");
            else if (self.selectedWebcam() === "cvprinting")
                self.settings.settings.plugins.cvprinting.selectedWebcam("cvprinting");
        };

        self.selectedWebcam.subscribe(function(newValue){
            if (newValue === "classic"){
                document.getElementById("cvprintingCam_settings").style.display = "none";
                document.getElementById("classicCam_settings").style.display = "block";
                document.getElementById("videoStream").src=self.classicStreamUrl();
            }
            else if (newValue === "cvprinting"){
                document.getElementById("cvprintingCam_settings").style.display = "block";
                document.getElementById("classicCam_settings").style.display = "none";
                document.getElementById("videoStream").src=self.cvprintingStreamUrl();
            }
        });

        function getWebcams() {
            return fetch("/plugin/cvprinting/get_webcams", {method: "POST"})
                .then(Response => Response.json())
                .catch(error => {
                    console.error("Error fetching webcams:", error);
                    return [];
                });
        }

    }

    OCTOPRINT_VIEWMODELS.push(
        {
            construct: cvprintingSettingsViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#cvprinting_settings"]
        }
    );
});