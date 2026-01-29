# 📌 ACTIVITY

## Create App Platform with DigitalOcean

🕒 *Estimated Time: 10 minutes*

---

## ✅ Your Task: Deploy a Live App with DigitalOcean's App Platform

In this task, you will deploy a live app with **DigitalOcean's App Platform**!

### 🧱 Create App Platform

- [ ] Go to your **DigitalOcean Project** main page.
- [ ] Select **Create** >> **App Platform** (marked in yellow in the image below). This will open the **Create App** menu.

![Digital Ocean Create App Platform](../../docs/images/digitalocean_create_app_platform.PNG)

### 🔗 Select Git Repository

- [ ] Select **Git repository**
- [ ] Select **Connect and select a repository**
- [ ] Under **Git provider**, select **GitHub** 
- [ ] Under **Repository**, click [**Edit your GitHub Permissions**](https://cloud.digitalocean.com/apps/github/install).

### 🔐 Authorize Specific Repository

- Here, we will login to **GitHub** and authorize **GitHub** to use the **DigitalOcean Integration** for specific repositories of yours, public or private.
- [ ] Navigate to **Repository Access**
- [ ] Select **Only select repositories**
- [ ] Click **Select repositories** dropdown menu.
- [ ] Select any repositories you need, e.g., your team project repository, a test repository, etc. **Select the repository that contains your app's code.**
- [ ] Click **Save**.

![Digital Ocean Create App Platform](../../docs/images/digitalocean_select_repo_initial.PNG)

### ✅ Complete Git Repo Selection

- [ ] Back on the **Create an App** page, select the repository.
- [ ] Select the branch of the repo to deploy from. Typically `main`.
- [ ] If your code is in a folder, optionally enter the path to that folder.
- [ ] Select **Autodeploy** to deploy this code every time.
- [ ] Select **Next**.

![Digital Ocean Create App Platform](../../docs/images/digitalocean_select_repo_next.PNG)

### ✅ Review and configure settings

- [ ] Set the instance size to the lowest payment tier - eg. $5/month.
- If you are deploying our test `plumber.R` app:
  - [ ] set the **Build strategy** to **Dockerfile**
  - [ ] leave the **Run command** undefined - because by default, that docker image runs the script specied in the `Dockerfile` in R on startup.
- If you are deploying a different kind of app, I encourage you to specify the startup command in the `Dockerfile` itself.

---

## 📤 To Submit

- For credit: Upon completion, enter into the **CANVAS** assignment textbox entry a screenshot of (1) your live app on **DigitalOcean**, and of (2) your internal **DigitalOcean App Platform** page for that app!

---

![](../../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)