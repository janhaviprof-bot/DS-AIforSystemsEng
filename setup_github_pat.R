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

# Set the repo URLs for this project
origin_url = "https://github.com/janhaviprof-bot/DS-AIforSystemsEng.git"
upstream_url = "https://github.com/timothyfraser/dsai.git"

# Ensure remotes point to the correct repos
remotes = gert::git_remote_list()

origin = remotes[remotes$name == "origin", , drop = FALSE]
if (nrow(origin) == 0) {
  gert::git_remote_add(name = "origin", url = origin_url)
} else if (!identical(origin$url, origin_url)) {
  gert::git_remote_remove("origin")
  gert::git_remote_add(name = "origin", url = origin_url)
}

upstream = remotes[remotes$name == "upstream", , drop = FALSE]
if (nrow(upstream) == 0) {
  gert::git_remote_add(name = "upstream", url = upstream_url)
} else if (!identical(upstream$url, upstream_url)) {
  gert::git_remote_remove("upstream")
  gert::git_remote_add(name = "upstream", url = upstream_url)
}

# Pull the most recent changes from the professor's repo
gert::git_pull(remote = "upstream")

# Stage and commit only if there are local changes
status = gert::git_status()
if (nrow(status) > 0) {
  gert::git_add(dir(all.files = TRUE))
  gert::git_commit_all("my first commit")
} else {
  message("No local file changes to commit.")
}

# Push the commit to GitHub
gert::git_push(remote = "origin")
