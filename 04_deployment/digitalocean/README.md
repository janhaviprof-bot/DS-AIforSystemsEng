# README `/digitalocean`

# 🚀 Deploying a Plumber API to DigitalOcean App Platform

This tutorial will walk you through deploying your R Plumber API to DigitalOcean's App Platform. This guide is designed for graduate students who are new to coding and deployment.

*Reminder: Screenshots will be added to each section to provide visual guidance through the deployment process.*


## 🎯 What You'll Learn

- 🐳 How to containerize your R Plumber API using Docker
- ☁️ How to deploy your API to DigitalOcean App Platform
- 🔍 How to access and test your deployed API
- 🌐 Basic concepts of cloud deployment

---

## 📋 Prerequisites

Before starting, make sure you have:

1. 🌐 **DigitalOcean Account**: Sign up at [digitalocean.com](https://digitalocean.com) if you don't have one. Use my [**Referall Code**](https://m.do.co/c/c2c1db7e897d) for $200 in free credits.

<a href="https://www.digitalocean.com/?refcode=c2c1db7e897d&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge"><img src="https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg" alt="DigitalOcean Referral Badge" /></a>

1. 💻 **GitHub Account**: Your code needs to be in a GitHub repository (public or private; you must authorize DigitalOcean to be able to access that repository.)



3. 📊 **Basic R Knowledge**: Familiarity with R and Plumber APIs
4. 🔁 **Git Knowledge**: Basic understanding of version control

## 📁 Project Structure

This deployment folder contains three essential files:

- 📄 `plumber.R` - Your Plumber API code
- 🐳 `dockerfile` - Instructions for containerizing your app
- 📚 `README.md` - This tutorial


<br>

---

## 🔧 Step 1: Prepare Your Plumber API

Your Plumber API is already set up in `plumber.R`. This file contains:

- 💬 An echo endpoint (`/echo`) that returns a message
- 📊 A plotting endpoint (`/plot`) that generates a histogram
- 🧮 A sum endpoint (`/sum`) that adds two numbers

The API uses the `plumber` package and includes proper serialization for JSON responses.

<br>

---

## 🐳 Step 2: Understanding the Dockerfile

The `dockerfile` contains instructions for creating a containerized version of your app:

```dockerfile
FROM rstudio/plumber
RUN R -e "install.packages(c('dplyr', 'plumber'))"
COPY plumber.R /app/plumber.R
EXPOSE 8000
CMD ["/app/plumber.R"]
```

**🔍 What each line does:**

- `FROM rstudio/plumber`: 🏗️ Uses a pre-built R image with Plumber
- `RUN R -e "install.packages(...)"`: 📦 Installs required R packages
- `COPY plumber.R /app/plumber.R`: 📄 Copies your API code into the container
- `EXPOSE 8000`: 🌐 Tells Docker which port your app will use
- `CMD ["/app/plumber.R"]`: 🚀 Runs your Plumber API when the container starts

## 📤 Step 3: Push Your Code to GitHub

1. 🆕 **Create a new repository** on GitHub
2. 📤 **Upload your files** to the repository:
   - 📄 Upload `plumber.R`
   - 🐳 Upload `dockerfile` (note: no file extension)
   - 📚 Upload this `README.md`

3. 💾 **Commit and push** your changes:
   ```bash
   git add .
   git commit -m "Initial Plumber API deployment files"
   git push origin main
   ```

<br>

---


## ☁️ Step 4: Deploy to DigitalOcean App Platform

### 4.1 🆕 Create a New App

1. 🌐 **Log into DigitalOcean** and navigate to the App Platform
2. ➕ **Click "Create App"**
3. 🔗 **Connect your GitHub account** if you haven't already
4. 📁 **Select your repository** containing the Plumber API files

### 4.2 ⚙️ Configure Your App

1. 🏷️ **App Name**: Choose a unique name for your app
2. 📂 **Source Directory**: Leave blank (root directory)
3. 🔨 **Build Command**: Leave blank (Docker will handle this)
4. 🚀 **Run Command**: Leave blank (Docker will handle this)

### 4.3 💰 Configure Resources

1. 📋 **Plan**: Start with the Basic plan ($5/month)
2. 💻 **Instance**: Choose the smallest instance (512MB RAM)
3. 🌍 **Region**: Select a region close to your users

### 4.4 🚀 Deploy

1. 👀 **Review your configuration**
2. ✅ **Click "Create Resources"**
3. ⏰ **Wait for deployment** (this may take 5-10 minutes)

<br>

---

## 🧪 Step 5: Test Your Deployed API

Once deployment is complete:

1. 🔗 **Find your app URL** in the DigitalOcean dashboard
2. 🧪 **Test the endpoints**:

   **💬 Echo endpoint:**
   ```
   https://your-app-name.ondigitalocean.app/echo?msg=Hello%20World
   ```

   **📊 Plot endpoint:**
   ```
   https://your-app-name.ondigitalocean.app/plot
   ```

   **🧮 Sum endpoint (POST):**
   ```bash
   curl -X POST "https://your-app-name.ondigitalocean.app/sum" \
        -H "Content-Type: application/json" \
        -d '{"a": 5, "b": 3}'
   ```
<br>

---

## 📊 Step 6: Monitor and Manage Your App

### 📋 Viewing Logs
- 🏠 Go to your app in the DigitalOcean dashboard
- 📋 Click on "Runtime Logs" to see what's happening
- 🔍 Check for any error messages

### 🔄 Updating Your App
1. ✏️ **Make changes** to your `plumber.R` file
2. 💾 **Commit and push** to GitHub
3. 🔄 **DigitalOcean will automatically redeploy** your app

### 📈 Scaling Your App
- ⚙️ You can increase resources in the DigitalOcean dashboard
- 🚀 Add more instances for better performance
- 🌐 Set up custom domains if needed

<br>

---

## 🔧 Troubleshooting Common Issues

### 🚫 App Won't Start
- 🔍 Check that your `dockerfile` is named correctly (no extension)
- 📦 Verify all required packages are listed in the `RUN` command
- 📋 Check the runtime logs for error messages

### 🔌 API Endpoints Not Working
- ✅ Ensure your Plumber API code is syntactically correct
- 🔍 Check that endpoints are properly annotated with `#*`
- 🌐 Verify the port (8000) matches what's exposed in the Dockerfile

### 📦 Package Installation Errors
- ➕ Add missing packages to the `RUN` command in your Dockerfile
- 🧩 Some packages may require system dependencies

<br>

---

## 💰 Cost Considerations

- 💵 **Basic plan**: $5/month for 512MB RAM
- 💎 **Professional plan**: $12/month for 1GB RAM
- 📈 **Additional resources**: Scale up as needed

## 🚀 Next Steps

Once your API is deployed:

1. ➕ **Add more endpoints** to your `plumber.R` file
2. 🔐 **Implement authentication** if needed
3. 💾 **Add data persistence** with a database
4. 📊 **Set up monitoring** and alerts
5. 🌐 **Create a custom domain** for your API

## 📚 Additional Resources

- 📖 [Plumber Documentation](https://www.rplumber.io/)
- ☁️ [DigitalOcean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- 🐳 [Docker Documentation](https://docs.docker.com/)

## 🤝 Support

If you encounter issues:
1. 📋 Check the DigitalOcean App Platform logs
2. 📖 Review the Plumber documentation
3. 💬 Consult the DigitalOcean community forums
4. 👥 Reach out to your instructor or TA

---
