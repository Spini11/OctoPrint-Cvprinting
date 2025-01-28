$(function(){
    function cvprintingSidebarViewModel(parameters) {
        var self = this;
        self.printerState = parameters[0];
        self.settings = parameters[1];
        self.pauseOnError = ko.observable();
        self.pauseConfidence = ko.observable();
        self.warningConfidence = ko.observable();
        self.dataSave = false;
        getConfidence().then(confidence => {
            document.getElementById("ConfidenceValue").innerText = confidence;
        });

        function updateDynamicVariable() {
            if (self.printerState.isPrinting() === undefined){
                return; 
            }
            if (self.printerState.isPrinting()) {
                document.getElementById("currentStatus").style.display = "block";
                document.getElementById("notPrinting").style.display = "none";
                document.getElementById("notLoaded").style.display = "none";
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
            }
        }

        self.onBeforeBinding = function() {
            self.pauseOnError(self.settings.settings.plugins.cvprinting.pausePrintOnIssue());
            self.pauseConfidence(self.settings.settings.plugins.cvprinting.pauseThreshold());
            self.warningConfidence(self.settings.settings.plugins.cvprinting.warningThreshold());
        };

        self.onAfterBinding = function() {
            updateDynamicVariable();
            setInterval(updateDynamicVariable, 5000);
        };

        self.onSettingsBeforeSave = function() {
            if(self.dataSave === false)
                return;
            self.settings.settings.plugins.cvprinting.pausePrintOnIssue(self.pauseOnError());
            self.settings.settings.plugins.cvprinting.pauseThreshold(self.pauseConfidence());
            self.settings.settings.plugins.cvprinting.warningThreshold(self.warningConfidence());
            self.dataSave = false;
        };


        function getConfidence() {
            return fetch("/plugin/cvprinting/get_confidence", {method: "POST"})
                .then(response => response.json())
                .then(data => Math.floor(data.variable))
                .catch(error => {
                    console.error("Error fetching variable:", error);
                    return -1; // Return a default value in case of error
                });
        }

        self.pauseOnError.subscribe(function (newValue) {
            self.dataSave = true;
            self.settings.saveData();
        });

        self.pauseConfidence.subscribe(function (newValue) {
            self.dataSave = true;
            self.settings.saveData();
        });

        self.warningConfidence.subscribe(function (newValue) {
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