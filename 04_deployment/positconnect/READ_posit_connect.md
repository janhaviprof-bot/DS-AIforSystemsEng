# 📌 READ

## Posit Connect - A private deployment server

🕒 *Estimated Time: 2-3 minutes*

---

## What is **Posit Connect**?

> **Posit Connect** is a publishing platform for deploying **R and Python applications** privately. It supports **Shiny apps** (both R and Python), **Plumber APIs**, **FastAPI**, **Quarto documents**, and other data science content. Our program has an **Enhanced License** courtesy of Posit, which allows us to deploy applications **privately** - meaning only authorized users can access them.

**Posit Connect** provides a streamlined way to share data science work within an organization. Unlike public deployment platforms, **Posit Connect** gives you control over who can access your applications.

## 👥 User Management

Students are added to the **Posit Connect** server for our Cornell Systems Engineering Program at `connect.systems-apps.com` by their **netid** (Cornell network ID). Here's how it works:

1. **Invitation**: You receive an email invitation to join the server. (**CHECK YOUR SPAM FOLDER!**)
2. **Password Setup**: You'll be prompted to set your password when you first access the server
3. **Roles**: You can be assigned one of two roles:
   - **Viewer**: Can view and interact with deployed applications
   - **Publisher**: Can deploy new applications and update existing ones

## 🔑 API Keys

**Posit Connect** uses API keys for authentication. You can create API keys with different permissions:

- **Viewer API Keys**: Use these in the authorization headers when querying deployed APIs. These keys allow you to access content but not deploy it.
- **Publisher API Keys**: Use these in **GitHub Actions** workflows to automatically deploy your applications. These keys have permission to publish and update content.

To create API keys, log into **Posit Connect** and navigate to your account settings. You can create multiple keys for different purposes.

## 🏢 For Companies

**Posit Connect** is available for commercial use. Companies can purchase licenses to deploy their own **Posit Connect** server for internal use. This allows organizations to:

- Deploy data science applications privately
- Control access to sensitive data and analyses
- Share work securely within the organization
- Automate deployments via CI/CD pipelines

For more information about **Posit Connect** features and capabilities, see the [official Posit Connect documentation](https://docs.posit.co/connect/).

---

![](../../docs/images/icons.png)

---

← 🏠 [Back to Top](#READ)
