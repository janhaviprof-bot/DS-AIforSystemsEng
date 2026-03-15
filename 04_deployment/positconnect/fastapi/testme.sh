#!/bin/bash
cd 04_deployment/positconnect/fastapi
# Use fastapi_app directly for local uvicorn testing (ASGI)
python -m uvicorn app:fastapi_app --host 0.0.0.0 --port 8000
