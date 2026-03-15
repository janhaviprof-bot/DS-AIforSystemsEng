#!/bin/bash
# pushme.sh

# Push the FastAPI app to Posit Connect

# Install rsconnect package for Python
pip install rsconnect-python
# Navigate to the FastAPI app folder
cd 04_deployment/positconnect/fastapi
# Load the env file to get the CONNECT_SERVER and CONNECT_API_KEY
source .env
# Push the FastAPI app to Posit Connect
rsconnect deploy fastapi \
    --server $CONNECT_SERVER \
    --api-key $CONNECT_API_KEY \
    --entrypoint app:app ./
