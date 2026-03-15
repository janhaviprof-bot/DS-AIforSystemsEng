#!/bin/bash
# manifestme.sh

# Write a manifest.json file for a Shiny Python app,
# for deploying to Posit Connect.

# Install rsconnect package for Python
pip install rsconnect-python
# Write a manifest.json file for the Shiny Python app, directing it to the folder
rsconnect write-manifest shiny 04_deployment/positconnect/shinypy