$(function(){
    function cvprintingSettingsViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];
        self.telegramConnected = ko.observable(false);
        self.telegramConnecting = ko.observable(false);
        self.telegramConnectionUnauthorized = ko.observable(false);
        self.telegramConnectionError = ko.observable(false);
        self.telegramTokenChangedOnConnecting = ko.observable(false);
        self.telegramTimeOutResults = ko.observable(false);
        self.telegramTimeOutNoResults = ko.observable(false);
        self.telegramShowFoundChats = ko.observable(false);
        self.timeoutId = ko.observable(null);
        self.telegramChatIdFieldValue = ko.observable();
    

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
            self.clearErrors();
            self.telegramConnected(false);
            self.telegramConnecting(false);
            self.telegramShowFoundChats(false);
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

        self.onSettingsHidden = function() {
            self.stopFetching();
        };

        self.onSettingsBeforeSave = function() {
            self.stopFetching();
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
                self.settings.settings.plugins.cvprinting.telegramChatId("");
            }
            if(document.getElementById("telegramChatIdField").value !== ""){
                console.log("Setting chat id to: " + document.getElementById("telegramChatIdField").value);
                self.settings.settings.plugins.cvprinting.telegramChatId(document.getElementById("telegramChatIdField").value);
            }
            self.settings.settings.plugins.cvprinting.telegramBotToken(self.telegramToken());
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

        self.stopFetching = function() {
            clearTimeout(self.timeoutId());
            self.telegramConnecting(false);
        };

        self.clearErrors = function() {
            self.telegramConnectionUnauthorized(false);
            self.telegramConnectionError(false);
            self.telegramTokenChangedOnConnecting(false);
            self.telegramTimeOutResults(false);
            self.telegramTimeOutNoResults(false);
        }

        self.stopConnecting = function() {
            self.stopFetching();
        }

        self.connectBot = function () {
            self.stopFetching();
            let attempts = 0;
            let lastId = -1;
            let token = document.getElementById("telegramToken").value;
            self.telegramConnecting(true);
            self.telegramConnected(false);
            self.telegramShowFoundChats(false);
            document.getElementById("telegramChatIdField").options.length = 0;
            let option = document.createElement("option");
            option.text = "None";
            option.value = "";
            document.getElementById("telegramChatIdField").add(option);

            function fetchUpdates() {
                if (attempts >= 30)
                {
                    if (document.getElementById("telegramChatIdField").options.length <= 1)
                    {
                        self.telegramTimeOutNoResults(true);
                    }
                    else
                    {
                        self.telegramTimeOutResults(true);
                        self.telegramShowFoundChats(true);
                    }
                    self.stopFetching();
                    return;
                }
                fetch("https://api.telegram.org/bot" + token + "/getUpdates?offset=" + lastId)
                .then(response => {
                    if (!response.ok){
                        self.telegramConnecting(false);
                        if (response.status === 401)
                            self.telegramConnectionUnauthorized(true);
                        else
                            self.telegramConnectionError(true);
                        self.stopFetching();
                        return;
                    }
                    return response.json();
                }
                )
                .then(data => {
                    if (data && data.ok && attempts < 30){
                        self.clearErrors();
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
                        });
                    }
                }).catch(error => {
                    console.log("Error fetching Telegram updates:", error); 
                    self.telegramConnecting(false);
                    self.telegramConnected(false);
                    self.telegramConnectionError(true);
                    self.stopFetching();
                    return;
                });
                attempts++;
                self.timeoutId(setTimeout(fetchUpdates, 2000));
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