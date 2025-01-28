# OctoPrint-Cvprinting

CVPrinting is a plugin made for Octoprint that uses the power of the local machine to analyze pictures made using webcams in Octoprint with computer vision to detect printing defects.


## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
Open menu for installing plugins and then upload the downloaded zip file. Wait for the plugin to install and then restart Octoprint.

## Configuration

Once installed, open the settings and CVPrinting tab.
In the settings you can choose if you want the print to be paused when there is high confidence. Levels of confidence for pause and warning. And prefered webcam, you can choose between the classic or custom. For custom you input the snapshot URL and stream URL. 
Further down you can choose where you want the notifications to be sent.
How to set up discord notifications: [Discord webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
Follow the steps for "Making a webhook" and at the end click on "Copy Webhook URL", past this URL into the Discord WebhookURL in Octoprint and then tick "Enable Discord Notifications"
After that the plugin will be automatically enabled when you start a print.
