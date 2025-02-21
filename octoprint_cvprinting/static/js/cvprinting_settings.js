$(function(){
    function cvprintingSettingsViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];
        self.telegramConnected = ko.observable(false);
        self.telegramConnecting = ko.observable(false);
        self.telegramConnectionUnauthorized = ko.observable(false);
        self.telegramConnectionError = ko.observable(false);


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
        self.telegramEnabled = ko.observable();
        self.telegramToken = ko.observable();
        self.telegramChatId = ko.observable();

        self.onBeforeBinding = function() {
            self.warningThreshold(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.cvprintingSnapshotUrl(self.settings.settings.plugins.cvprinting.cvprintingSnapshotUrl());
            self.cvprintingStreamUrl(self.settings.settings.plugins.cvprinting.cvprintingStreamUrl());
            self.webhookUrl(self.settings.settings.plugins.cvprinting.discordWebhookUrl());
            self.discordEnabled(self.settings.settings.plugins.cvprinting.discordNotifications());
            self.selectedWebcam(self.settings.settings.plugins.cvprinting.selectedWebcam());
            self.telegramEnabled(self.settings.settings.plugins.cvprinting.telegramNotifications());
            self.telegramToken(self.settings.settings.plugins.cvprinting.telegramBotToken());
            self.telegramChatId(self.settings.settings.plugins.cvprinting.telegramChatId());
        };

        self.onSettingsShown = function() {
            self.warningThreshold(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.pauseThreshold(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.selectedWebcam(self.settings.settings.plugins.cvprinting.selectedWebcam());
            self.telegramToken(self.settings.settings.plugins.cvprinting.telegramBotToken());
            self.telegramChatId(self.settings.settings.plugins.cvprinting.telegramChatId());
            if (self.telegramToken() !== "" && self.telegramChatId() !== ""){
                self.telegramConnected(true);
            }
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
            console.log("saving settings");
            self.settings.settings.plugins.cvprinting.warningThreshold(self.warningThreshold());
            self.settings.settings.plugins.cvprinting.pauseThreshold(self.pauseThreshold());
            self.settings.settings.plugins.cvprinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.cvprinting.discordWebhookUrl(self.webhookUrl());
            self.settings.settings.plugins.cvprinting.discordNotifications(self.discordEnabled());
            self.settings.settings.plugins.cvprinting.cvprintingSnapshotUrl(self.cvprintingSnapshotUrl());
            self.settings.settings.plugins.cvprinting.cvprintingStreamUrl(self.cvprintingStreamUrl());
            if (self.telegramToken() === ""){
                self.telegramConnected(false);
                self.telegramEnabled(false);
                document.getElementById("telegramChatIdField").options.length = 0;
            }
            if(document.getElementById("telegramChatIdField").value === ""){
                self.telegramConnected(false);
                self.telegramEnabled(false);
            }
            self.settings.settings.plugins.cvprinting.telegramBotToken(self.telegramToken());
            self.settings.settings.plugins.cvprinting.telegramChatId(document.getElementById("telegramChatIdField").value);
            self.settings.settings.plugins.cvprinting.telegramNotifications(self.telegramEnabled());
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

        self.connectBot = function () {
            let attempts = 0;
            let lastId = -1;
            let token = document.getElementById("telegramToken").value;
            self.telegramConnecting(true);
            self.telegramConnected(false);

            function fetchUpdates() {
            if (attempts >= 30) return; 
                fetch("https://api.telegram.org/bot" + token + "/getUpdates?offset=" + lastId)
                .then(response => response.json())
                .then(data => {
                    console.log("Attempts: " + attempts);
                    if (data.ok && data.result.length > 0){
                        data.result.forEach(element => {
                            let chat = element.message.chat;
                            let chatId = chat.id;
                            lastId = element.update_id + 1;
                            let username = chat.username;
                            let option = document.createElement("option");
                            option.text = username + " (" + chatId + ")";
                            option.value = chatId;
                            let chatIdfield = document.getElementById("telegramChatIdField");
                            //Only add option if it doesn't exist already
                            if (![...chatIdfield.options].some(option => Number(option.value) === chatId)){
                                chatIdfield.add(option);
                            }
                            console.log("Chat ID: " + chatId);
                        });
                        
                    }
                }).catch(error => {
                    //If error code 401, token is invalid
                    if (error.code === 401){
                        self.telegramConnecting(false);
                        self.telegramConnected(false);
                        self.telegramConnectionUnauthorized(true);
                    }
                    else{
                        console.error("Error fetching Telegram udpates:", error);
                        self.telegramConnecting(false);
                        self.telegramConnected(false);
                        self.telegramConnectionError(true);
                    }
                    return;
                });
                attempts++;
                setTimeout(fetchUpdates, 2000);
            }
            fetchUpdates();
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