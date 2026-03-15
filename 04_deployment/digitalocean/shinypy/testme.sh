#!/bin/bash
cd 04_deployment/digitalocean/shinypy
Python -m shiny run app.py --host 0.0.0.0 --port 8000
