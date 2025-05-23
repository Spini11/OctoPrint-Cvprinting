$(function(){
    function cvprintingSidebarViewModel(parameters) {
        var self = this;
        self.printerState = parameters[0];
        self.settings = parameters[1];
        self.pauseOnError = ko.observable();
        self.pauseConfidence = ko.observable();
        self.warningConfidence = ko.observable();
        self.cvprintingEnabled = ko.observable();
        self.dataSave = false;
        self.pauseSubscriptions = false;
        getConfidence().then(confidence => {
            document.getElementById("ConfidenceValue").innerText = confidence;
        });

        function updateDynamicVariable() {
            if (self.printerState.isPrinting() === undefined) {
                return; 
            }
            if (self.cvprintingEnabled() === false){
                document.getElementById("currentStatus").style.display = "none";
                document.getElementById("notPrinting").style.display = "none";
                document.getElementById("notLoaded").style.display = "none";
                document.getElementById("disabled").style.display = "block";
                return;
            };
            if (self.printerState.isPrinting()) {
                document.getElementById("currentStatus").style.display = "block";
                document.getElementById("notPrinting").style.display = "none";
                document.getElementById("notLoaded").style.display = "none";
                document.getElementById("disabled").style.display = "none";
                document.getElementById("ConfidenceText").innerText = "Current Error confidence:";
                
                getConfidence().then(confidence => {
                    if (confidence >= 0){
                        document.getElementById("ConfidenceValue").innerText = confidence;
                        document.getElementById("ConfidenceColorStatus").style.color = self.warningConfidence() > confidence ? "#32cd32" : self.pauseConfidence() > confidence ? "orange" : "red";
                    }
                    else{
                        document.getElementById("ConfidenceValue").innerText = "N/A";
                    }
                });
                
            }
            else if (self.printerState.isPaused() || self.printerState.isPausing()){
                document.getElementById("currentStatus").style.display = "block";
                document.getElementById("ConfidenceText").innerText = "Last recorded Error confidence:";
                document.getElementById("notLoaded").style.display = "none";
                document.getElementById("notPrinting").style.display = "none";

                getConfidence().then(confidence => {
                    if (confidence >= 0){
                        document.getElementById("ConfidenceValue").innerText = confidence;
                        document.getElementById("ConfidenceColorStatus").style.color = self.warningConfidence() > confidence ? "#32cd32" : self.pauseConfidence() > confidence ? "orange" : "red";
                    }
                    else{
                        document.getElementById("ConfidenceValue").innerText = "N/A";
                    }
                });
            }
            else{              
                document.getElementById("notPrinting").style.display = "block";
                document.getElementById("currentStatus").style.display = "none";
                document.getElementById("notLoaded").style.display = "none";
                document.getElementById("disabled").style.display = "none";
            }
        }

        self.onBeforeBinding = function() {
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.pauseConfidence(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.warningConfidence(self.settings.settings.plugins.cvprinting.warningThreshold());
            self.cvprintingEnabled(self.settings.settings.plugins.cvprinting.cvEnabled());
        };

        self.onAfterBinding = function() {
            self.dataSave = false;
            updateDynamicVariable();
            setInterval(updateDynamicVariable, 5000);
        };

        self.onSettingsBeforeSave = function() {
            //If save was not triggered by sidebar, do not save and update the values from the settings
            if(self.dataSave === false)
            {
                self.pauseSubscriptions = true;
                // Update values
                self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
                self.pauseConfidence(self.settings.settings.plugins.cvprinting.pauseThreshold());
                self.warningConfidence(self.settings.settings.plugins.cvprinting.warningThreshold());
                self.cvprintingEnabled(self.settings.settings.plugins.cvprinting.cvEnabled());
                self.pauseSubscriptions = false;
        
            return;
            }

            self.settings.settings.plugins.cvprinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.cvprinting.pauseThreshold(self.pauseConfidence());
            self.settings.settings.plugins.cvprinting.warningThreshold(self.warningConfidence());
            self.settings.settings.plugins.cvprinting.cvEnabled(self.cvprintingEnabled());
            self.dataSave = false;
        };


        function getConfidence() {
            var url = OctoPrint.getBlueprintUrl("cvprinting") + "get_confidence";
            return OctoPrint.post(url)
            .then(function(response) {
                return Math.floor(response.variable);
            });
        }

        self.pauseOnError.subscribe(function (newValue) {
            if(self.pauseSubscriptions === true)
                return;
            self.dataSave = true;
            self.settings.saveData();
        });

        self.pauseConfidence.subscribe(function (newValue) {
            if(self.pauseSubscriptions === true)
                return;
            self.dataSave = true;
            self.settings.saveData();
        });

        self.warningConfidence.subscribe(function (newValue) {
            if(self.pauseSubscriptions === true)
                return;
            self.dataSave = true;
            self.settings.saveData();
        });
    
        self.cvprintingEnabled.subscribe(function (newValue) {
            if(self.pauseSubscriptions === true)
                return;
            self.dataSave = true;
            self.settings.saveData();
        });

    }

    OCTOPRINT_VIEWMODELS.push(
        {
            construct: cvprintingSidebarViewModel,
            dependencies: ["printerStateViewModel", "settingsViewModel"],
            elements: ["#cvprinting_sidebar"]
        }
    );
});