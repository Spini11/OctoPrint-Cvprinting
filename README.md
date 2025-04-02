# OctoPrint-Cvprinting

CVPrinting is a plugin made for Octoprint that uses the power of the local machine to analyze pictures made using webcams in Octoprint with computer vision to detect printing defects.
Unlike other solutions, CVPrinting does not require a remote server, as it runs entirely on a single machine.

## Hardware Requirements

CVPrinting uses computer vision to analyze webcam images, which requires more processing power than standard OctoPrint setups.

- **Minimum Recommended Hardware**:
  - The plugin has been tested on a **Raspberry Pi 5** and runs smoothly. Any system with similar or higher performance should also run it without issues.
  - While older Raspberry Pi models (e.g., Pi 4 or Pi 3) may also work, they have not been tested and cannot be guaranteed at this time.
  - Hardware with insufficient performance may potentially cause defects during the print.

---


## Setup
### Manually installing plugin from a file
1. Download the plugin's zip file.
2. Install it via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html) (right-click or middle-click to open in a new tab):
   - Open the **Plugin Manager** in OctoPrint.
   - Click on "+ Get More" button
   - Upload the downloaded zip file.
3. Wait for the installation to complete, then restart OctoPrint.
### Installing through a link
1. Open [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)(right-click or middle-click to open in a new tab) in Octoprint
2. Click on "+ Get More" button
3. Copy this link: https://github.com/Spini11/OctoPrint-Cvprinting/archive/refs/heads/master.zip and paste it into the URL field in your plugin manager and hit Install.
4. Wait for the installation to complete, then restart OctoPrint.


---

## Configuration
After installation, configure the plugin by navigating to **Settings > CVPrinting**. Below are the key configuration options:

### 1. Detection Settings
- **Enable computer vision for detecting issues**: This enables printing issue detection
- **Pause on High Confidence**: Enable this to automatically pause the print when a defect is detected with high confidence.
- **Confidence Levels**(Those values control how confident model has to be about issue, before starting an action):
  - Set the confidence threshold for pausing the print. (Recommended: 80+).
  - Set the confidence threshold for issuing warnings.
  Note: Setting the confidence threshold too low may result in frequent false positives, causing unnecessary pauses during printing. Adjust based on your preference and testing.

### 2. Webcam Settings
- **Preferred Webcam**:
  - *Classic*: Uses the default OctoPrint webcam setup.
  - *Custom*: Manually input the *Snapshot URL* and *Stream URL* for a different webcam.

### 3. Notification Settings
- **Notification Destinations**: Choose where you want notifications about detected defects to be sent.
- **Discord Notifications**:
  1. Set up a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) (right-click or middle-click to open in a new tab):
     - Follow the steps for "Making a Webhook."
     - Copy the Webhook URL.
  2. Paste the Webhook URL into the **Webhook URL** field in the CVPrinting settings.
  3. Tick the "Enable Discord Notifications" checkbox.
  4. (Optional) Use "Send Test Notification to Discord" button to test notifications.
  5. Save

- **Telegram notifications**:
  1. Create a telegram bot following this [Guide](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) and obtain your token
  2. Input token into the **Bot Token** field in the CVPrinting settings and hit Connect.
  3. Within the next 60 seconds, send a message to the bot on Telegram.
  4. Once a message is sent check the chat ID drop down menu and pick a field containing your name.
  5. Tick the "Enable Telegram Notifications" checkbox.
  6. (Optional) Use "Send Test Notification to Telegram" button to test notifications.
  7. Save

---

## Usage

Once configured, the plugin automatically activates when you start a print. It will monitor the printing process, detect potential defects, and take action based on your configured settings.

## Support
If you encounter any problems, notification even when no issue is present or no notifications when an issue happens, contact me at cvprinting@spini.eu. For incorrect detections, please include the picture from notification. Pictures will be used to further train the computer vision model and enhance its performance.