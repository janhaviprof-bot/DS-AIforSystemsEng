#!/bin/bash
# manifestme.sh

# Write a manifest.json file for a Shiny FastAPI,
# for deploying to Posit Connect.

# Install rsconnect package for Python
pip install rsconnect-python
# Write a manifest.json file for the Shiny FastAPI app, directing it to the folder
rsconnect write-manifest api 04_deployment/positconnect/fastapi