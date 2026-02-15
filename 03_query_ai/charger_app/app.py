# app.py
# EV Charger Shiny App – main entry.
# Tim Fraser

# Runs the Shiny app that infers car make/model via Ollama, asks for confirmation,
# then fetches EV data from API Ninjas and shows battery, charge power, and charging time.
# Structure: UI from ui_components, server logic from server, API/Ollama helpers in utils.

# 0. SETUP ###################################

## 0.1 Imports #################################

import os
import sys
from pathlib import Path

# Ensure the app directory is on the path first so that server/utils/ui_components can be found.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)

from shiny import App, run_app

from ui_components import app_ui
from server import server

# 1. APP #####################################

# Wire the UI and server into a single Shiny App.
app = App(app_ui, server)

# Run with: python app.py  (or: shiny run app.py)
# Requires root .env: OLLAMA_API_KEY (Ollama Cloud), EV_API_KEY (API Ninjas), OPENAI_API_KEY (Best charging slots).
# Opens in your default browser.
if __name__ == "__main__":
    try:
        run_app(app, launch_browser=True)
    except Exception as e:
        print("Error starting the app:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        input("\nPress Enter to close this window...")
        sys.exit(1)
