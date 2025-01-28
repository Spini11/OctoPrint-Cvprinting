# OctoPrint-Cvprinting

CVPrinting is a plugin made for Octoprint that uses the power of the local machine to analyze pictures made using webcams in Octoprint with computer vision to detect printing defects.
CVPrinting unlike others doesn't need remote server as it all runs on one machine.

## Hardware Requirements

CVPrinting uses computer vision to analyze webcam images, which requires more processing power than standard OctoPrint setups.

- **Minimum Recommended Hardware**:
  - The plugin has been tested on a **Raspberry Pi 5** and runs smoothly. Any system with similar or higher performance should also run it without issues.
  - While older Raspberry Pi models (e.g., Pi 4 or Pi 3) may also work, they have not been tested and cannot be guaranteed at this time.
  - Hardware with insufficient performance may potentially cause defects during the print.

If you're using older hardware, you might need to adjust settings like image resolution or detection frequency to ensure smooth operation.

---


## Setup

1. Download the plugin's zip file.
2. Install it via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html):
   - Open the **Plugin Manager** in OctoPrint.
   - Upload the downloaded zip file.
3. Wait for the installation to complete, then restart OctoPrint.

---

## Configuration
After installation, configure the plugin by navigating to **Settings > CVPrinting**. Below are the key configuration options:

### 1. Detection Settings
- **Pause on High Confidence**: Enable this to automatically pause the print when a defect is detected with high confidence.
- **Confidence Levels**:
  - Set the threshold for pausing the print.
  - Set the threshold for issuing warnings.

### 2. Webcam Settings
- **Preferred Webcam**:
  - *Classic*: Uses the default OctoPrint webcam setup.
  - *Custom*: Manually input the *Snapshot URL* and *Stream URL* for a different webcam.

### 3. Notification Settings
- **Notification Destinations**: Choose where you want notifications about detected defects to be sent.
- **Discord Notifications**:
  1. Set up a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks):
     - Follow the steps for "Making a Webhook."
     - Copy the Webhook URL.
  2. Paste the Webhook URL into the **Discord Webhook URL** field in the CVPrinting settings.
  3. Tick the "Enable Discord Notifications" checkbox.

---

## Usage

Once configured, the plugin automatically activates when you start a print. It will monitor the printing process, detect potential defects, and take action based on your configured settings.