# How to Get Your Threads API Credentials (For Non-Technical Users)

Hello! To build our application for the hackathon, we need to connect it to a Threads account. Since Meta (the company that owns Threads, Instagram, and Facebook) protects user accounts, you will need to generate a special "Access Token" that gives our code permission to search and post on your behalf.

Don't worry—you don't need to write any code to do this. Just follow this step-by-step guide, and it will take about 5-10 minutes.

---

## Step 1: Create a Meta Developer Account
1. Open your web browser and go to [Meta for Developers](https://developers.facebook.com/).
2. Click **Log In** in the top right corner. You can log in using your Facebook or Instagram account.
3. If this is your first time here, click **Get Started** (or Register) and follow the on-screen prompts to verify your account (you may need to verify your email or phone number).

## Step 2: Create a Meta App
1. Once you are logged in, click on **My Apps** in the top right corner.
2. Click the green **Create App** button.
3. You will be asked what you want your app to do. Look for an option related to **Threads** or select **Other** -> **Business** (depending on Meta's current layout).
4. Give your app a name (e.g., `Hackathon Threads App`) and provide a contact email.
5. Click **Create app**. (You may be asked to re-enter your Facebook password for security).

## Step 3: Add the Threads Product to Your App
1. You will be taken to your App Dashboard. Scroll down until you see a list of products you can add to your app.
2. Find the one called **Threads API** and click the **Set up** button on it.
3. Follow any quick prompts to finalize adding it.

## Step 4: Add Yourself as a Tester
*Because this app isn't public yet, Meta requires you to explicitly allow your own Instagram/Threads account to use it.*
1. In the left-hand menu of your App Dashboard, click on **App Roles** and then **Roles** (or find the specific **Threads** section and look for **Testers**).
2. Click **Add People** and select **Threads Tester**.
3. Enter your Instagram/Threads username and click **Add**.
4. **Important:** Open the Instagram app on your phone, go to your **Settings**, find **Website permissions** -> **App Invites**, and **Accept** the invite you just sent yourself.

## Step 5: Generate the Access Token (The "Keys")
1. Go back to the Meta Developer website. 
2. In the top menu bar, click on **Tools**, and then select **Graph API Explorer**.
3. On the right side of the Graph API Explorer screen, you will see a settings panel:
   * **Meta App:** Make sure the app you just created (`Hackathon Threads App`) is selected.
   * **User or Page:** Make sure **User Token** is selected.
4. Under the **Permissions** section, click **Add a Permission**. You need to search for and select the following permissions so our app can do its job:
   * `threads_basic`
   * `threads_keyword_search` 
   * *(If we also need to post: `threads_content_publish`)*
5. Click the **Generate Access Token** button.
6. A popup window will appear asking you to log into Instagram and authorize the app. Click **Allow** or **Continue**.
7. Once authorized, a long string of random letters and numbers will appear in the "Access Token" box at the top.

## Step 6: Send the Credentials
1. Click the small "Copy" icon next to that long **Access Token** string.
2. Paste that long string into a secure message or email and send it to your developer.
3. Also, let the developer know your **exact Threads Username** (e.g., `@yourname`).

---
**Security Note:** Treat this Access Token like a password. Do not post it publicly. It allows whoever has it to interact with Threads on your behalf!
