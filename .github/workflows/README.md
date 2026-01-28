# Canvas Assignment Sync Workflow

This GitHub Actions workflow automatically syncs changed ACTIVITY, LAB, HOMEWORK, and TOOL markdown files to Canvas when you push to the `main` branch.

## How It Works

1. **Triggers**: Runs automatically on push to `main` branch when `.md` files are changed
2. **Detection**: Identifies changed files matching patterns:
   - `ACTIVITY_*.md`
   - `LAB_*.md`
   - `HOMEWORK*.md`
   - `TOOL*.md`
3. **Filtering**: Only syncs files that have a `github_path` mapping in `canvastest/assignments_metadata_5381.json` (from private canvastest repository)
4. **Syncing**: Updates Canvas assignment descriptions using the `canvastest` submodule

## Setup

### 1. Required GitHub Secrets

You must configure the following secrets in your GitHub repository settings:

1. **`CANVAS_API_KEY`**
   - Your Canvas API authentication token
   - Get it from: Canvas → Account → Settings → New Access Token
   - **Important**: Never commit this key to the repository

2. **`CANVAS_COURSE_ID`**
   - Your Canvas course ID (integer)
   - Found in the Canvas course URL: `https://canvas.cornell.edu/courses/COURSE_ID`
   - Example: If URL is `https://canvas.cornell.edu/courses/81764`, the ID is `81764`

3. **`SUBMODULE_SSH_KEY`** (Required if canvastest is private)
   - SSH private key for accessing the private `canvastest` submodule
   - See "Setting Up SSH Access for Private Submodule" below for detailed instructions

#### How to Add Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact names above

### 1a. Setting Up SSH Access for Private Submodule

If your `canvastest` repository is private, you need to set up SSH authentication so the workflow can access it.

#### Step 1: Generate SSH Key Pair

On your local machine, generate a new SSH key (if you don't already have one for this purpose):

```bash
ssh-keygen -t ed25519 -C "github-actions-canvastest" -f ~/.ssh/github_actions_canvastest
```

**Important**: Do NOT use a passphrase (press Enter when prompted).

This creates two files:
- `~/.ssh/github_actions_canvastest` (private key) - **Keep this secret!**
- `~/.ssh/github_actions_canvastest.pub` (public key) - You'll add this to GitHub

#### Step 2: Add Public Key as Deploy Key 

1. Go to your **private** `canvastest` repository on GitHub
2. Click **Settings** → **Deploy keys** → **Add deploy key**
3. **Title**: `GitHub Actions - dsai sync`
4. **Key**: Paste the contents of `~/.ssh/github_actions_canvastest.pub`
5. ✅ Check **Allow write access** (if you need to update the repo, otherwise read-only is fine)
6. Click **Add key**

#### Step 3: Add Private Key as Secret

1. Go to your **public** `dsai` repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. **Name**: `SUBMODULE_SSH_KEY`
4. **Secret**: Paste the **entire contents** of `~/.ssh/github_actions_canvastest` (the private key)
   - Include the `-----BEGIN OPENSSH PRIVATE KEY-----` header
   - Include the `-----END OPENSSH PRIVATE KEY-----` footer
   - Include all lines in between
5. Click **Add secret**

#### Step 4: Verify Setup

After pushing to `main`, check the workflow logs:
- Look for "Setup SSH for private submodule" step
- Should see "Checkout submodules" step completing successfully
- If you see authentication errors, verify the SSH key was copied correctly

**Security Notes**:
- The private key is stored securely as a GitHub secret
- Deploy keys are repository-specific and more secure than PATs
- The workflow automatically configures SSH before checking out submodules

### 2. Submodule Setup

The workflow requires the `canvastest` submodule to be initialized:

```bash
git submodule update --init --recursive
```

### 3. Assignments Metadata File

The workflow uses `canvastest/assignments_metadata_5381.json` from the **private** `canvastest` repository. This file must exist with `github_path` mappings for each assignment you want to sync.

#### Why Private?

The metadata file contains assignment IDs, names, and mappings that you may prefer to keep private. By storing it in the private `canvastest` repository, it's not exposed in the public `dsai` repository.

#### Creating/Updating the Metadata File

1. In your local `canvastest` repository, run the fetch script (see [canvastest README](../../canvastest/README.md))
2. Save the metadata as `assignments_metadata_5381.json` (or copy and rename from `assignments_metadata.json`)
3. Edit the file to add `github_path` entries for each assignment
4. Commit and push to the **private** `canvastest` repository

Example entry:

```json
{
  "id": 123456,
  "name": "Install Git and Git Bash",
  "points_possible": 10,
  "github_path": "00_quickstart/ACTIVITY_git.md"
}
```

**Important**: 
- Only files with `github_path` entries will be synced
- Files without mappings will be skipped
- The file must be named `assignments_metadata_5381.json` in the `canvastest` repository root

## Workflow Behavior

### What Gets Synced

- Only files that:
  1. Match the assignment patterns (ACTIVITY_, LAB_, HOMEWORK*, TOOL*)
  2. Were changed in the push
  3. Have a `github_path` mapping in `assignments_metadata.json`

### What Gets Skipped

- Files that don't match assignment patterns
- Files without `github_path` mappings
- Non-markdown files

### Error Handling

- If a single file fails to sync, the workflow logs the error and continues with other files
- The workflow fails only if critical setup fails (R installation, submodule checkout)
- Check workflow logs for detailed error messages

## Workflow Logs

After pushing to `main`, you can view workflow runs:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select the **Canvas Assignment Sync** workflow
4. Click on a run to see detailed logs

## Troubleshooting

### Workflow doesn't run

- **Check**: Did you push to `main` branch?
- **Check**: Did you change any `.md` files?
- **Check**: Is the workflow file in `.github/workflows/canvas-sync.yml`?

### "No changed assignment files found"

- This is normal if you didn't change any ACTIVITY/LAB/HOMEWORK/TOOL files
- The workflow will skip syncing

### "assignments_metadata_5381.json not found"

- **Cause**: The file doesn't exist in the private `canvastest` repository, or SSH authentication failed
- **Solution**: 
  1. Verify `assignments_metadata_5381.json` exists in the `canvastest` repository root
  2. Check that `SUBMODULE_SSH_KEY` secret is configured correctly
  3. Verify the deploy key was added to the `canvastest` repository
  4. Check workflow logs for SSH authentication errors

### "No assignment found with github_path"

- **Cause**: The changed file doesn't have a `github_path` entry in `assignments_metadata.json`
- **Solution**: Add the `github_path` mapping for that file in the metadata file
- The workflow will skip files without mappings (this is expected behavior)

### "CANVAS_API_KEY not found"

- **Cause**: Secret not configured or incorrectly named
- **Solution**: Verify the secret is named exactly `CANVAS_API_KEY` in repository settings

### "Failed to sync" errors

- Check the workflow logs for specific error messages
- Common causes:
  - Invalid Canvas API key
  - Network issues
  - Canvas API rate limits (workflow will retry automatically)
  - Invalid markdown content

### Submodule issues

- **Error**: "Cannot find canvastest/R directory"
- **Solution**: Ensure submodule is initialized:
  ```bash
  git submodule update --init --recursive
  ```

## Security Notes

Since this is a **public repository**:

- ✅ **Secrets are secure**: GitHub Actions secrets are never exposed in logs or code
- ✅ **Workflow is visible**: Anyone can see the workflow file (this is fine - no secrets in it)
- ✅ **Private metadata**: `assignments_metadata_5381.json` stays in private `canvastest` repo
- ✅ **SSH keys**: Private SSH key is stored securely as a secret, never exposed
- ⚠️ **Be careful**: Never log or echo secrets in workflow steps
- ⚠️ **Check logs**: Ensure R scripts don't accidentally print API keys
- ⚠️ **SSH key security**: The SSH private key should only be used as a deploy key for `canvastest`

The workflow automatically masks secrets in logs. The `.env` file created during workflow execution is temporary and never committed.

**Why keep metadata private?**
- Assignment IDs and Canvas course structure details
- Internal mapping information
- While not highly sensitive, keeping it private provides an extra layer of security

## Cost

**Free!** Since this is a public repository, GitHub Actions provides unlimited free minutes. You can run this workflow as frequently as needed without any cost concerns.

## Manual Testing

To test the sync script locally:

```bash
# Create a test file with changed files
echo "00_quickstart/ACTIVITY_git.md" > test_changed.txt

# Run the sync script (from repository root)
Rscript canvastest/scripts/sync_changed_files.R \
  test_changed.txt \
  course_config.json \
  canvastest/assignments_metadata_5381.json
```

**Note**: The sync script and SSH setup scripts are located in the private `canvastest` repository at `canvastest/scripts/` to keep sensitive setup information secure.

## Related Documentation

- [canvastest Module README](../canvastest/README.md) - Detailed documentation of the sync module
- [canvastest Workflow Documentation](../canvastest/docs/WORKFLOW.md) - Step-by-step workflow procedures
- [canvastest Configuration Guide](../canvastest/docs/CONFIGURATION.md) - Configuration options

## Scripts Location

All scripts (including `sync_changed_files.R` and SSH setup scripts) are located in the **private** `canvastest` repository at `canvastest/scripts/`. This ensures sensitive setup information and scripts are not exposed in the public `dsai` repository.

## Support

If you encounter issues:

1. Check the workflow logs in the **Actions** tab
2. Review the troubleshooting section above
3. Consult the canvastest documentation
4. Verify all secrets are configured correctly

---

# GitHub Pages Site Generator Workflow

This GitHub Actions workflow automatically generates and deploys a comprehensive static website from your repository's markdown files, HTML files, and code files to GitHub Pages.

## Overview

The GitHub Pages Site Generator workflow:

- **Converts** all `.md` files to HTML with proper styling and syntax highlighting
- **Preserves** existing `.html` files
- **Displays** code files (`.R`, `.py`, `.sh`) with syntax highlighting and download links
- **Generates** automatic navigation based on directory structure
- **Deploys** automatically to GitHub Pages on every push to `main`

## How It Works

1. **Triggers**: Runs automatically on push to `main` branch or can be manually triggered
2. **Build**: 
   - Sets up Python environment
   - Installs dependencies (`markdown`, `pygments`)
   - Runs the site generator script (`.github/scripts/generate_site.py`)
   - Generates static site in `_site/` directory
3. **Deploy**: Uploads and deploys the generated site to GitHub Pages

## Features

### Markdown Processing
- GitHub Flavored Markdown support
- Code block syntax highlighting (via Pygments)
- Table of contents generation
- Image path handling
- Link rewriting for site navigation
- Emoji support

### Code File Features
- Syntax highlighting for R, Python, Bash, and other languages
- Line numbers
- Download button (links to raw GitHub file)
- Copy-to-clipboard functionality
- File metadata (size, lines, language)

### Navigation Features
- Hierarchical navigation tree based on directory structure
- Collapsible sidebar navigation
- Mobile-responsive design
- Breadcrumbs support

### Styling
- Modern, clean design using Tailwind CSS (via CDN)
- Responsive layout (mobile-friendly)
- Accessible semantic HTML
- Print-friendly styles

## Setup

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under **Source**, select:
   - **Deploy from a branch**: `gh-pages`
   - **Branch**: `gh-pages` / `/ (root)`
4. Click **Save**

**Note**: The workflow automatically creates and updates the `gh-pages` branch, so you don't need to create it manually.

### 2. Workflow Permissions

The workflow requires the following permissions (already configured in `pages.yml`):

- `contents: read` - To checkout the repository
- `pages: write` - To deploy to GitHub Pages
- `id-token: write` - For OIDC authentication

These are automatically granted when you enable GitHub Pages.

## File Structure

The site generator creates the following structure:

```
_site/
├── index.html (from README.md)
├── 00_quickstart/
│   ├── index.html (from README.md)
│   ├── ACTIVITY_git.html
│   ├── dependencies.sh.html (code file page)
│   └── CHEATSHEET_git_bash.html (preserved)
├── 01_query_api/
│   └── ...
├── assets/
│   ├── css/
│   │   ├── style.css
│   │   └── syntax.css
│   └── js/
│       └── syntax-highlight.js
└── _navigation.json (for dynamic nav)
```

## Manual Site Generation

You can also generate the site locally for testing:

```bash
# Install dependencies
pip install markdown pygments

# Run the generator script
python .github/scripts/generate_site.py

# Preview the site
cd _site
python -m http.server 8000
# Open http://localhost:8000 in your browser
```

## Configuration

### Ignored Directories

The following directories are automatically excluded from site generation:

- `.git`
- `.github`
- `_site`
- `__pycache__`
- `node_modules`
- `.cursor`

### File Type Detection

The generator automatically categorizes files:

- **README**: Files named `README.md`
- **Activity**: Files starting with `ACTIVITY_`
- **Lab**: Files starting with `LAB_`
- **Homework**: Files starting with `HOMEWORK`
- **Tool**: Files starting with `TOOL`
- **Code**: Files with extensions `.R`, `.r`, `.py`, `.sh`, `.bash`
- **HTML**: Files with extensions `.html`, `.htm`

## Workflow Logs

After pushing to `main`, you can view workflow runs:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select the **Build and Deploy GitHub Pages** workflow
4. Click on a run to see detailed logs

## Troubleshooting

### Site not updating

- **Check**: Did you push to `main` branch?
- **Check**: Is the workflow file in `.github/workflows/pages.yml`?
- **Check**: Are there any errors in the workflow logs?
- **Check**: Is GitHub Pages enabled in repository settings?

### "No module named 'markdown'"

- **Cause**: Python dependencies not installed
- **Solution**: The workflow should install dependencies automatically. Check workflow logs for installation errors.

### Navigation not showing correctly

- **Check**: Verify `_navigation.json` is generated in `_site/` directory
- **Check**: Check browser console for JavaScript errors
- **Check**: Verify CSS files are copied to `_site/assets/css/`

### Code syntax highlighting not working

- **Check**: Verify `pygments` is installed
- **Check**: Check browser console for JavaScript errors
- **Check**: Verify syntax CSS file is loaded (`/assets/css/syntax.css`)

### Images not loading

- **Check**: Verify image paths are relative to repository root
- **Check**: Check that images are copied to `_site/` directory
- **Check**: Verify image paths in generated HTML

## Customization

### Styling

Edit `.github/scripts/assets/css/style.css` to customize:
- Colors and themes
- Layout and spacing
- Typography
- Responsive breakpoints

### Templates

Edit templates in `.github/scripts/templates/`:
- `base.html` - Base template structure
- `markdown.html` - Markdown page template
- `code.html` - Code file page template

### Navigation

The navigation structure is automatically generated from your directory structure. To customize:
- Edit `.github/scripts/generate_site.py`
- Modify the `generate_navigation()` function
- Adjust the `get_file_type()` function for custom file categorization

## Cost

**Free!** Since this is a public repository, GitHub Actions provides unlimited free minutes. The workflow runs automatically on every push to `main` without any cost.

## Related Files

- **Workflow**: `.github/workflows/pages.yml`
- **Generator Script**: `.github/scripts/generate_site.py`
- **Templates**: `.github/scripts/templates/`
- **Assets**: `.github/scripts/assets/`
