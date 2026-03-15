#!/bin/bash
cd 04_deployment/digitalocean/fastapi
Python -m uvicorn app:app --host 0.0.0.0 --port 8000
