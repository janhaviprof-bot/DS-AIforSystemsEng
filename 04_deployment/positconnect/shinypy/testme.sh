#!/bin/bash
cd 04_deployment/positconnect/shinypy
python -m shiny run app.py --host 0.0.0.0 --port 8000
