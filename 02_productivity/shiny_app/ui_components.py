# ui_components.py
# UI layout and inputs for Carbon Intensity Shiny app.
# Pairs with LAB_cursor_shiny_app.md
# Tim Fraser

# Defines the app UI: page layout, query parameter inputs, and output placeholders.
# Uses Shiny Core: nested ui components for clear structure.

from shiny import ui

# IBM Carbon Design theme — green-energy AI dashboard (Carbon Gray 10 + green accent).
# Typography: IBM Plex Sans (Carbon). Backgrounds and cards styled for visual appeal.
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  --carbon-background: #f4f4f4;
  --carbon-background-warm: #f0f7f2;
  --carbon-layer: #ffffff;
  --carbon-border: #e0e0e0;
  --carbon-border-subtle: #e8e8e8;
  --carbon-text-primary: #161616;
  --carbon-text-secondary: #525252;
  --carbon-green-60: #198038;
  --carbon-green-50: #24a148;
  --carbon-green-40: #42be65;
  --carbon-green-20: #a7f0ba;
  --carbon-green-10: #defbe6;
  --carbon-font: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body {
  font-family: var(--carbon-font) !important;
  background: linear-gradient(165deg, var(--carbon-background-warm) 0%, var(--carbon-background) 45%, #e8f0ea 100%) !important;
  min-height: 100vh;
}

@keyframes header-gradient-shift {
  0%, 100% { opacity: 1; transform: scale(1) translate(0, 0); }
  33% { opacity: 0.9; transform: scale(1.05) translate(2%, 1%); }
  66% { opacity: 1; transform: scale(1.02) translate(-1%, 2%); }
}

@keyframes header-blob-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(15px, -10px) scale(1.1); }
}

.app-header {
  position: relative;
  border-radius: 14px;
  padding: 2rem 2rem 2.25rem;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(25, 128, 56, 0.15);
  overflow: hidden;
}

.app-header::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg,
    rgba(25, 128, 56, 0.12) 0%,
    rgba(8, 189, 186, 0.06) 40%,
    rgba(222, 251, 230, 0.2) 70%,
    rgba(25, 128, 56, 0.08) 100%);
  background-size: 200% 200%;
  animation: header-gradient-shift 12s ease-in-out infinite;
  z-index: 0;
}

.app-header::after {
  content: '';
  position: absolute;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(66, 190, 101, 0.2) 0%, transparent 70%);
  top: -80px;
  right: -60px;
  animation: header-blob-float 8s ease-in-out infinite;
  z-index: 0;
}

.app-header .header-content {
  position: relative;
  z-index: 1;
}

.app-title {
  font-family: var(--carbon-font);
  font-weight: 700;
  font-size: 2.75rem;
  letter-spacing: -0.03em;
  color: var(--carbon-text-primary);
  margin-bottom: 0.35rem;
  text-shadow: 0 1px 2px rgba(255,255,255,0.8);
}

.app-subtitle {
  font-family: var(--carbon-font);
  font-weight: 400;
  font-size: 1rem;
  color: var(--carbon-text-secondary);
  line-height: 1.5;
}

.card-query {
  border-radius: 10px;
  border: 1px solid var(--carbon-border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  background-color: var(--carbon-layer);
  border-left: 4px solid var(--carbon-green-60);
  transition: box-shadow 0.2s ease;
}

.card-query:hover {
  box-shadow: 0 4px 12px rgba(25, 128, 56, 0.08);
}

.card-results {
  border-radius: 10px;
  border: 1px solid var(--carbon-border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  background: linear-gradient(180deg, #ffffff 0%, #fafbfa 100%);
  transition: box-shadow 0.2s ease;
}

.card-results:hover {
  box-shadow: 0 4px 14px rgba(0,0,0,0.07);
}

.card-body {
  font-family: var(--carbon-font);
}

.card-title {
  font-family: var(--carbon-font);
  font-weight: 600;
  font-size: 1.15rem;
  letter-spacing: -0.01em;
  color: var(--carbon-text-primary);
}

.btn-primary {
  font-family: var(--carbon-font) !important;
  font-weight: 600 !important;
  background-color: var(--carbon-green-60) !important;
  border-color: var(--carbon-green-60) !important;
  color: #ffffff !important;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.btn-primary:hover {
  background-color: #166f31 !important;
  border-color: #166f31 !important;
  color: #ffffff !important;
  transform: translateY(-1px);
}

.help-text {
  font-family: var(--carbon-font);
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--carbon-text-secondary);
  margin-top: 0.25rem;
  line-height: 1.4;
}

.result-summary {
  font-family: var(--carbon-font);
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--carbon-text-primary);
  line-height: 1.5;
}

.text-muted {
  color: var(--carbon-text-secondary) !important;
}
"""


def app_ui(request):
    """
    Build the full app UI: title, query card with inputs, and results area.
    Returns the root UI object for use in App(app_ui, server).
    Shiny calls this with the request object; we ignore it for static UI.
    """
    return ui.page_fluid(
        ui.tags.head(ui.tags.style(CUSTOM_CSS)),
        ui.div(
            {"class": "container-fluid py-4"},
            # Header (animated gradient + floating blob behind title)
            ui.div(
                {"class": "app-header"},
                ui.div(
                    {"class": "header-content"},
                    ui.h1("UK Carbon Intensity", class_="app-title"),
                    ui.p(
                        "Carbon intensity and power by source (generation mix) for a date range.",
                        class_="app-subtitle",
                    ),
                ),
            ),
            # Query parameters card
            ui.div(
                {"class": "card card-query mb-4"},
                ui.div(
                    {"class": "card-body"},
                    ui.h5("Query parameters", class_="card-title mb-3"),
                    ui.div(
                        {"class": "row g-3 align-items-end"},
                        ui.div(
                            {"class": "col-md-9"},
                            ui.input_date_range(
                                "date_range",
                                "Date range",
                                start="2018-05-15",
                                end="2018-05-17",
                                min="2016-01-01",
                                format="yyyy-mm-dd",
                                startview="month",
                            ),
                            ui.tags.p(
                                "Click each field to open the calendar. Times: start 00:00 UTC, end 23:00 UTC.",
                                class_="help-text",
                            ),
                        ),
                        ui.div(
                            {"class": "col-md-3"},
                            ui.input_action_button(
                                "run_query",
                                "Run query",
                                class_="btn btn-primary",
                            ),
                        ),
                    ),
                ),
            ),
            # Results: Carbon intensity
            ui.div(
                {"class": "card card-results mb-4"},
                ui.div(
                    {"class": "card-body"},
                    ui.h5("Carbon intensity and mix by source", class_="card-title mb-3"),
                    ui.output_ui("result_summary"),
                    ui.output_ui("result_error"),
                    ui.output_data_frame("result_table"),
                ),
            ),
            # Visual summary for a selected period
            ui.div(
                {"class": "card card-results"},
                ui.div(
                    {"class": "card-body"},
                    ui.h5("Visual summary for period", class_="card-title mb-3"),
                    ui.p(
                        "Averages across all periods in your query: generation mix (pie) and actual vs forecast (line).",
                        class_="result-summary text-muted mb-3",
                    ),
                    ui.div(
                        {"class": "row g-3 mt-2"},
                        ui.div(
                            {"class": "col-md-6"},
                            ui.output_plot("pie_chart", height="320px"),
                        ),
                        ui.div(
                            {"class": "col-md-6"},
                            ui.output_plot("actual_forecast_chart", height="320px"),
                        ),
                    ),
                ),
            ),
        ),
        title="UK Carbon Intensity",
    )
