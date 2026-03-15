#!/bin/bash
cd 04_deployment/login/shinypy_supabase
python -m shiny run app.py --host 0.0.0.0 --port 8000
