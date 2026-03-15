#!/bin/bash
cd 04_deployment/positconnectcloud/shinypy_password
python -m shiny run app.py --host 0.0.0.0 --port 8000
