# app.py
# Minimal Shiny for Python app
# Template for DigitalOcean App Platform deployment
# Tim Fraser

# Single-file Shiny app: title, sidebar slider, and reactive output.

from shiny import reactive, render
from shiny.express import input, ui

ui.page_opts(title="Minimal Shiny (Python)", fillable=True)

with ui.sidebar(open="desktop"):
    ui.input_slider("n", "Number of points", min=1, max=100, value=50)
    ui.input_text("label", "Label", value="Shiny for Python")

with ui.card():
    ui.card_header("Output")
    @render.text
    def out():
        n = input.n()
        lbl = input.label()
        return f"{lbl}: value is {n}"
