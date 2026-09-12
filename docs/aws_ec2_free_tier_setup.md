# Beginner's Guide: Setting Up a Free Linux VPS on AWS (EC2)

Amazon Web Services (AWS) offers a "Free Tier" that includes a free Linux cloud server (called an EC2 instance) for 12 months. This is a great way to host your hackathon project, bot, or web application for free!

Here is how to set it up from scratch.

---

## Step 1: Create an AWS Account

1. Go to the [AWS Free Tier page](https://aws.amazon.com/free/).
2. Click **Create a Free Account**.
3. Follow the registration steps. You will need to provide an email address, password, and a chosen AWS account name.
4. **Billing Information:** You *must* enter a valid credit or debit card. AWS does this to verify your identity. They will place a small temporary hold (usually $1) that will be refunded. **As long as you stay within the Free Tier limits, you will not be charged.**
5. Complete the identity verification (usually via a text message to your phone).
6. Choose the **Basic Support - Free** plan.

## Step 2: Access the EC2 Dashboard

1. Once your account is active, log into the [AWS Management Console](https://console.aws.amazon.com/).
2. Look at the top right corner of the screen to select your **Region** (e.g., *US East (N. Virginia)* or *Europe (Frankfurt)*). Pick the one closest to you or your users.
3. In the search bar at the top, type **EC2** and click on it. This is the service used for renting virtual servers.

## Step 3: Launch Your Free Server

1. On the EC2 Dashboard, click the bright orange **Launch instance** button.
2. **Name:** Give your server a name (e.g., `Hackathon-Server`).
3. **Application and OS Images (Amazon Machine Image):**
   * Select **Ubuntu** (it's the most beginner-friendly and widely used for tutorials).
   * Make sure the specific version you pick has a badge that says **Free tier eligible** underneath it (usually Ubuntu 22.04 LTS or 24.04 LTS).
4. **Instance Type:**
   * This is the hardware size. Select **`t2.micro`** (or `t3.micro` depending on your region). Make sure it has the **Free tier eligible** label next to it!
5. **Key Pair (Login):**
   * *This is very important! This acts as your password.*
   * Click **Create new key pair**.
   * Name it something recognizable (e.g., `my-aws-key`).
   * Key pair type: **RSA**.
   * Private key file format: **.pem** (if you use Mac/Linux) or **.ppk** (if you use Windows with PuTTY, though Windows 10/11 PowerShell supports .pem now).
   * Click **Create key pair**. The file will download to your computer. **Keep it safe!** You cannot download it again.
6. **Network Settings:**
   * Under Firewall (security groups), check the following boxes:
     * **Allow SSH traffic from** -> **Anywhere 0.0.0.0/0** (This lets you control the server).
     * **Allow HTTP traffic from the internet** (If you are hosting a web app).
     * **Allow HTTPS traffic from the internet** (If you are hosting a web app).
7. **Configure Storage:**
   * Leave it at the default (usually 8 GB). The Free Tier allows up to 30 GB of storage, so you can increase this up to 30 GB if needed.
8. Look at the Summary panel on the right side. Check that it says "Free tier eligible", then click **Launch instance**.

## Step 4: Connect to Your Server

1. After launching, click the **Instances** link on the left menu of the EC2 Dashboard to see your server. Wait for the "Instance state" to say **Running**.
2. Click on the Instance ID (the blue link).
3. Find your **Public IPv4 address** on this page and copy it.

Now, open your terminal (Mac/Linux) or PowerShell (Windows) on your personal computer:

4. First, make your downloaded `.pem` key file secure (Mac/Linux only, Windows can skip this):
   ```bash
   chmod 400 ~/Downloads/my-aws-key.pem
   ```
5. Connect to the server via SSH. The default username for Ubuntu on AWS is `ubuntu`:
   ```bash
   ssh -i ~/Downloads/my-aws-key.pem ubuntu@YOUR_PUBLIC_IP
   ```
   *(Replace the path to your key and YOUR_PUBLIC_IP with your actual details).*
6. If it asks `Are you sure you want to continue connecting (yes/no)?`, type **yes** and press Enter.

---
**Success!** You are now inside your free AWS cloud server. You can install Python, run your bots, or host your applications!

**Important Reminder:** The AWS Free Tier lasts for exactly **12 months** from the day you created your account. After 12 months, AWS will start charging your card for the server unless you turn it off (terminate it).
