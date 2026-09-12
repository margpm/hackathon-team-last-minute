# Starter Guide: How to Get a Free Cloud Server (VPS) on Oracle Cloud

This guide will walk you through getting a free, permanent cloud server (VPS) using Oracle Cloud's "Always Free" tier. This is perfect for hosting small web apps, bots, or hackathon projects!

---

## Step 1: Create Your Free Account

1. Go to the [Oracle Cloud Free Tier website](https://www.oracle.com/cloud/free/).
2. Click the **Start for free** button.
3. Follow the steps to create your account (you'll need to provide your email, country, and basic information).
4. **Important:** When asked to choose a **Home Region**, pick a location closest to where you (or your app users) are. *You cannot change this later!*
5. You will need to enter a credit or debit card. Oracle uses this just to verify you are a real person (they make a small temporary hold). **You will not be charged** unless you explicitly upgrade to a paid account.

## Step 2: Create Your Server (Instance)

Once your account is set up and you are logged into the Oracle Cloud Console:

1. Click the menu icon (≡) in the top left corner.
2. Go to **Compute** -> **Instances**.
3. Click the blue **Create Instance** button.
4. **Name:** Give your server a name (like `my-free-server`).
5. **Image and Shape (The Server Type):**
   * Under "Image and Shape", click **Edit**.
   * **Image:** We recommend selecting **Ubuntu 22.04** or **Ubuntu 24.04** (look for the "Always Free Eligible" tag).
   * **Shape:** Click "Change Shape". Choose **Ampere** and select `VM.Standard.A1.Flex`. You can move the sliders to get up to **4 Cores (OCPUs)** and **24 GB of RAM** for free! *(If it says "out of capacity", choose the `VM.Standard.E2.1.Micro` under "Specialty and Legacy" instead).*
6. **Add SSH Keys (Crucial Step):**
   * Scroll down to the "Add SSH keys" section.
   * Select **Generate a key pair for me**.
   * Click **Save Private Key**. A file (e.g., `ssh-key-2024-01-01.key`) will download to your computer. **Keep this file safe!** It is the "password" to log into your server, and you can't download it again.
7. Click the **Create** button at the very bottom.

Your server will now take a few minutes to start up. When the square icon turns green and says "RUNNING", you're ready to connect!

## Step 3: Connect to Your Server (via SSH)

To control your server, you need to connect to it using a terminal and the private key you downloaded.

1. On your Oracle Cloud instance page, look for **Public IP Address** (it will look like numbers separated by dots, e.g., `123.45.67.89`). Copy this.
2. Open your computer's terminal:
   * **Mac/Linux:** Open the `Terminal` app.
   * **Windows:** Open `Command Prompt` or `PowerShell`.
3. First, we need to make your key file secure so only you can read it. Run this command (replace the path with where your downloaded key is):
   
   **On Mac/Linux:**
   ```bash
   chmod 400 ~/Downloads/ssh-key-2024-01-01.key
   ```
   *(Note: Windows usually handles permissions automatically for SSH, so you can skip this step on Windows).*

4. Now, connect to the server! The default username for Ubuntu servers is `ubuntu`. Run this command:

   ```bash
   ssh -i ~/Downloads/ssh-key-2024-01-01.key ubuntu@YOUR_PUBLIC_IP
   ```
   *(Make sure to replace the path to your key and `YOUR_PUBLIC_IP` with the actual ones!)*

5. It will ask `Are you sure you want to continue connecting (yes/no)?`. Type **yes** and press Enter.

**Congratulations!** You are now logged into your free cloud server! You can start installing Python, Node.js, or whatever else you need for your project.
