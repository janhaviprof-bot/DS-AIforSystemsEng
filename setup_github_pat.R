#' @name setup_github_pat.R
#' @title Use a GitHub PAT with gert and credentials
#' @author Prof. Tim Fraser
#' @description
#' Topic: GitHub Personal Access Tokens (PATs)
#'
#' This script shows how to install the needed packages, store a PAT in a local
#' .env file, and authenticate with GitHub using the gert and credentials
#' packages. It then pulls, stages, commits, and pushes changes.

# 0. SETUP ###################################

## 0.1 Install Packages #################################

# Install required packages if missing
packages = c("usethis", "gert", "credentials")
installed = rownames(installed.packages())
to_install = packages[!packages %in% installed]
if (length(to_install) > 0) {
  install.packages(to_install)
}

## 0.2 Load Packages ####################################

library(usethis) # for coding management helper functions
library(gert) # for GitHub operations like commit, pull, and push
library(credentials) # for authenticating with GitHub

# 1. STORE PAT LOCALLY ##################################

## 1.1 Create a .env File ################################

# Create a .env file if it does not exist
# Add a line like: GITHUB_PAT=your_token_here
if (!file.exists(".env")) {  file.create(".env")  }

# Add .env to project and global ignore lists so it is never committed
usethis::use_git_ignore(".env")
usethis::git_vaccinate()

## 1.2 Load .env (Optional) ##############################

# Load environment variables from .env if present
if (file.exists(".env")) {  readRenviron(".env")  }

# 2. AUTHENTICATE #######################################

# This prompts for your GitHub PAT in a secure popup
credentials::set_github_pat()

# 3. SYNC WITH GITHUB ####################################

# Optional: Set the repo URL if origin is not configured
# repo_url = "https://github.com/janhaviprof-bot/DS-AIforSystemsEng.git"
# gert::git_remote_add("origin", repo_url)

# Pull the most recent changes from GitHub
gert::git_pull()

# Stage all files in the repository
gert::git_add(dir(all.files = TRUE))

# Commit staged changes
gert::git_commit_all("my first commit")

# Push the commit to GitHub
gert::git_push()
