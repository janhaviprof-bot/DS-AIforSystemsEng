# app.py
# UK Carbon Intensity Shiny App – main entry.
# Pairs with LAB_cursor_shiny_app.md
# Tim Fraser

# Runs the Shiny app that queries the UK Carbon Intensity API on user request.
# Structure: UI from ui_components, server logic from server, API helpers in utils.

# 0. SETUP ###################################

## 0.1 Imports #################################

from shiny import App, run_app

from ui_components import app_ui
from server import server

# 1. APP #####################################

# Wire the UI and server into a single Shiny App.
app = App(app_ui, server)

# Run with: python app.py  (or: shiny run app.py)
# Opens in your default browser; Cursor's Simple Browser often cannot load localhost.
if __name__ == "__main__":
    run_app(app, launch_browser=True)
