# ui_components.py
# UI layout and inputs for EV Charger Shiny app.
# Tim Fraser

# Defines the app UI: header, car make/model text input, Look up button,
# confirmation area (output_ui), and result area (output_ui). Server
# fills confirmation and result via two-phase flow.

from shiny import ui

# YC / Tesla energy dashboard theme (no premium dashboard)
CUSTOM_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

:root {
  --ev-background: #f5f5f7;
  --ev-layer: #ffffff;
  --ev-border: rgba(0,0,0,0.06);
  --ev-text: #1d1d1f;
  --ev-muted: #6e6e73;
  --ev-accent: #0d9488;
  --ev-accent-hover: #0b7a70;
  --ev-slot-low: #22c55e;
  --ev-slot-medium: #eab308;
  --ev-slot-high: #ef4444;
}

@media (prefers-color-scheme: dark) {
  :root {
    --ev-background: #0c0c0e;
    --ev-layer: #161618;
    --ev-border: rgba(255,255,255,0.08);
    --ev-text: #f5f5f7;
    --ev-muted: #a1a1a6;
    --ev-accent: #2dd4bf;
    --ev-accent-hover: #5eead4;
  }
}

* { -webkit-font-smoothing: antialiased; }

body {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--ev-background);
  min-height: 100vh;
  color: var(--ev-text);
  font-size: 15px;
  line-height: 1.5;
}

.ev-dashboard {
  width: 80%;
  margin: 0 10%;
  padding: 2rem 1.5rem 4rem;
}

/* Hero banner card – matches page (dashboard) width */
.ev-hero-banner {
  width: 100%;
  padding: 2.5rem 2rem;
  margin-bottom: 2rem;
  background: linear-gradient(135deg, #0d9488 0%, #14b8a6 40%, #99f6e4 100%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s ease;
}

.ev-hero-banner:hover {
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
}

.ev-hero-banner-inner {
  width: 100%;
}

.ev-hero-title {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #fff;
  margin: 0 0 0.5rem 0;
  line-height: 1.25;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.ev-hero-subtext {
  font-size: 1rem;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.88);
  margin: 0;
  letter-spacing: 0.01em;
  line-height: 1.5;
}

@media (prefers-color-scheme: dark) {
  .ev-hero-banner {
    background: linear-gradient(135deg, #0f172a 0%, #0d9488 50%, #134e4a 100%);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
  }
  .ev-hero-banner:hover {
    box-shadow: 0 8px 32px rgba(13, 148, 136, 0.2);
  }
  .ev-hero-title {
    color: #f5f5f7;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  }
  .ev-hero-subtext {
    color: rgba(245, 245, 247, 0.8);
  }
}

.slot-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}

.slot-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}

.intensity-strip {
  display: flex;
  gap: 1px;
  height: 2.25rem;
  align-items: flex-end;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 0.75rem;
  background: var(--ev-border);
}

.intensity-bar {
  flex: 1;
  min-width: 2px;
  border-radius: 2px 2px 0 0;
  transition: opacity 0.15s ease;
}

.intensity-bar:hover {
  opacity: 0.9;
}

/* Hero recommendation: main focus when slots loaded */
.hero-recommendation {
  border-radius: 16px;
  border: 2px solid var(--ev-accent);
  box-shadow: 0 8px 32px rgba(13,148,136,0.12);
  padding: 2rem 2rem 2.25rem;
  margin-bottom: 1.5rem;
  background: var(--ev-layer);
  transition: box-shadow 0.2s ease;
}

@media (prefers-color-scheme: dark) {
  .hero-recommendation {
    box-shadow: 0 8px 32px rgba(45,212,191,0.15);
  }
}

.hero-recommendation-badge {
  display: inline-block;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  margin-bottom: 0.75rem;
}

.hero-recommendation-time {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
  line-height: 1.2;
}

.hero-recommendation-reason {
  font-size: 0.9375rem;
  opacity: 0.95;
  margin-bottom: 1.25rem;
  line-height: 1.4;
}

/* Carbon intensity graph with highlight overlay */
.intensity-graph-wrap {
  position: relative;
  margin-top: 0.75rem;
}

.intensity-strip {
  min-height: 2.5rem;
}

.intensity-bar {
  min-width: 4px;
}

.intensity-highlight {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(13,148,136,0.18);
  border-radius: 8px;
  pointer-events: none;
  border: 1px solid rgba(13,148,136,0.35);
}

@media (prefers-color-scheme: dark) {
  .intensity-highlight {
    background: rgba(45,212,191,0.2);
    border-color: rgba(45,212,191,0.4);
  }
}

/* Insight: muted block below graph */
.insight-section {
  font-size: 0.9375rem;
  color: var(--ev-muted);
  padding: 1rem 1.25rem;
  margin: 1rem 0 1.25rem;
  border-left: 4px solid var(--ev-accent);
  border-radius: 0 10px 10px 0;
  background: rgba(13,148,136,0.04);
  line-height: 1.5;
}

@media (prefers-color-scheme: dark) {
  .insight-section {
    background: rgba(45,212,191,0.06);
  }
}

/* First slot in list can be de-emphasised (same as hero) */
.slot-card-hero-dupe {
  opacity: 0.85;
}

.slots-loading {
  padding: 2.5rem;
  text-align: center;
  color: var(--ev-muted);
  font-size: 0.9375rem;
}

.slots-loading::after {
  content: "";
  display: inline-block;
  width: 1rem;
  height: 1rem;
  margin-left: 0.5rem;
  border: 2px solid var(--ev-border);
  border-top-color: var(--ev-accent);
  border-radius: 50%;
  animation: slots-spin 0.6s linear infinite;
  vertical-align: middle;
}

@keyframes slots-spin {
  to { transform: rotate(360deg); }
}

/* Premium dashboard cards (same feel as EV vehicle card) */
.card-query, .card-confirm, .card-results {
  border-radius: 16px;
  border: 1px solid var(--ev-border);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  background: linear-gradient(145deg, var(--ev-layer) 0%, rgba(13,148,136,0.04) 100%);
  margin-bottom: 1.25rem;
  overflow: hidden;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  animation: ev-vehicle-card-enter 0.4s ease-out backwards;
}

.card-query:nth-of-type(1), .card-confirm:nth-of-type(1), .card-results:nth-of-type(1) { animation-delay: 0.02s; }
.card-query:nth-of-type(2), .card-confirm:nth-of-type(2), .card-results:nth-of-type(2) { animation-delay: 0.06s; }
.card-query:nth-of-type(3), .card-confirm:nth-of-type(3), .card-results:nth-of-type(3) { animation-delay: 0.1s; }
.card-query:nth-of-type(4), .card-confirm:nth-of-type(4), .card-results:nth-of-type(4) { animation-delay: 0.14s; }
.card-query:nth-of-type(5), .card-confirm:nth-of-type(5), .card-results:nth-of-type(5) { animation-delay: 0.18s; }

.card-query:hover, .card-confirm:hover, .card-results:hover {
  box-shadow: 0 8px 28px rgba(0,0,0,0.08);
}

.card-body { padding: 1.5rem 1.75rem; }

.ev-choice-card {
  margin-bottom: 1.5rem;
  border-radius: 16px;
  border: 1px solid var(--ev-border);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.ev-choice-recommended-tag {
  display: inline-block;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: var(--ev-accent);
  color: #fff;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  vertical-align: middle;
  margin-left: 0.5rem;
}

.card-query .card-title,
.card-confirm .card-title,
.card-results .card-title {
  font-weight: 600;
  font-size: 0.8125rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ev-muted);
  margin-bottom: 1rem;
  line-height: 1.3;
}

.slot-card .card-title {
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.9375rem;
  color: inherit;
}

.btn-primary {
  background: var(--ev-accent) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 500 !important;
  font-size: 0.9375rem !important;
  padding: 0.5rem 1.25rem !important;
  border-radius: 10px !important;
  transition: background 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
}

.btn-primary:hover {
  background: var(--ev-accent-hover) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(13,148,136,0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-outline-secondary {
  border-radius: 50% !important;
  border: 1px solid var(--ev-border) !important;
  background: var(--ev-layer) !important;
  color: var(--ev-text) !important;
  transition: transform 0.15s ease !important;
}

.slots-scroll-area {
  scrollbar-width: none;
}

.slots-scroll-area::-webkit-scrollbar {
  display: none;
}

.slot-card .card-body {
  padding: 1.25rem 1.5rem;
}

.ev-slot-calendar-wrap {
  margin-top: 0.75rem;
  width: 100%;
}

.ev-slot-calendar-btn {
  width: 100%;
  padding: 0.4rem 0.75rem !important;
  font-size: 0.8125rem !important;
  border-radius: 8px !important;
  background: rgba(255, 255, 255, 0.25) !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  color: inherit !important;
  transition: background 0.2s ease;
  font-weight: 500 !important;
}

.ev-slot-calendar-btn:hover {
  background: rgba(255, 255, 255, 0.4) !important;
  color: inherit !important;
}

.slots-scroll-arrow {
  border-radius: 50%;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.help-text {
  font-size: 0.8125rem;
  color: var(--ev-muted);
  margin-top: 0.375rem;
  line-height: 1.45;
}

.form-control, .form-select {
  border-radius: 10px !important;
  border-color: var(--ev-border) !important;
  font-size: 0.9375rem !important;
}

/* Premium EV vehicle card */
.ev-vehicle-card {
  background: linear-gradient(145deg, var(--ev-layer) 0%, rgba(13,148,136,0.04) 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  padding: 1.5rem 1.75rem;
  overflow: hidden;
  border: 1px solid var(--ev-border);
  animation: ev-vehicle-card-enter 0.45s ease-out forwards;
}

@keyframes ev-vehicle-card-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.ev-vehicle-card .ev-vehicle-header {
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ev-text);
  margin-bottom: 1.25rem;
  line-height: 1.2;
}

.ev-vehicle-card .ev-spec-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--ev-border);
  animation: ev-vehicle-card-enter 0.4s ease-out backwards;
}

.ev-vehicle-card .ev-spec-row:nth-child(2) { animation-delay: 0.05s; }
.ev-vehicle-card .ev-spec-row:nth-child(3) { animation-delay: 0.1s; }
.ev-vehicle-card .ev-spec-row:nth-child(4) { animation-delay: 0.15s; }
.ev-vehicle-card .ev-spec-row:nth-child(5) { animation-delay: 0.2s; }

.ev-vehicle-card .ev-spec-row:last-of-type {
  border-bottom: none;
}

.ev-vehicle-card .ev-spec-icon {
  width: 1.25rem;
  text-align: center;
  font-size: 1.125rem;
  flex-shrink: 0;
}

.ev-vehicle-card .ev-spec-label {
  font-size: 0.8125rem;
  color: var(--ev-muted);
  min-width: 6rem;
}

.ev-vehicle-card .ev-spec-value {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--ev-text);
  margin-left: auto;
}

.ev-vehicle-insight {
  font-size: 0.9375rem;
  color: var(--ev-muted);
  padding: 1rem 1.25rem;
  margin-top: 1rem;
  border-left: 4px solid var(--ev-accent);
  border-radius: 0 10px 10px 0;
  background: rgba(13,148,136,0.06);
  line-height: 1.5;
}

@media (prefers-color-scheme: dark) {
  .card-query, .card-confirm, .card-results {
    background: linear-gradient(145deg, var(--ev-layer) 0%, rgba(45,212,191,0.06) 100%);
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  }
  .card-query:hover, .card-confirm:hover, .card-results:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.35);
  }
  .ev-vehicle-card {
    background: linear-gradient(145deg, var(--ev-layer) 0%, rgba(45,212,191,0.06) 100%);
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  }
  .ev-vehicle-insight {
    background: rgba(45,212,191,0.08);
  }
}

.alert { border-radius: 10px; border: none; }

/* Add to calendar modal – Stripe/Notion style */
.ev-calendar-modal-body {
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: stretch;
}

.ev-calendar-btn {
  display: inline-block;
  text-align: center;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9375rem;
  padding: 0.625rem 1.25rem;
  border-radius: 10px;
  transition: background 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
  border: none;
}

.ev-calendar-btn-primary {
  background: #2563eb;
  color: #fff;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
}

.ev-calendar-btn-primary:hover {
  background: #1d4ed8;
  color: #fff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

.ev-calendar-fallback {
  display: block;
  font-size: 0.8125rem;
  color: var(--ev-muted);
  text-decoration: none;
  padding: 0.5rem 0;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s ease;
}

.ev-calendar-fallback:hover {
  color: var(--ev-accent);
}

/* Shiny modal container – gradient background, soft shadow, rounded, optional glass */
.shiny-modal .modal-content {
  background: linear-gradient(to bottom, #f0fdfa, #d9f7f4);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border: 1px solid var(--ev-border);
  transition: background 0.3s ease, box-shadow 0.3s ease, backdrop-filter 0.3s ease;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

@media (prefers-color-scheme: dark) {
  .shiny-modal .modal-content {
    background: linear-gradient(to bottom, #1a1a1d, #161618);
  }
}
"""


def app_ui(request):
    """
    Two-column layout: left = Charging slot preferences + Best charging slots (intensity + slots);
    right = Car make/model, Confirm vehicle, EV data.
    """
    CALENDAR_SCRIPT = """
(function() {
  function createCalendarEvent(slotStart, slotEnd) {
    var title = "EV Charging (Low carbon window)";
    var description = "Best time to charge based on low carbon intensity";
    var location = "Home";
    var crlf = "\\r\\n";
    var ics = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "BEGIN:VEVENT",
      "DTSTART:" + slotStart,
      "DTEND:" + slotEnd,
      "SUMMARY:" + title.replace(/[,;\\\\]/g, "\\\\$&"),
      "DESCRIPTION:" + description.replace(/[,;\\\\]/g, "\\\\$&"),
      "LOCATION:" + location.replace(/[,;\\\\]/g, "\\\\$&"),
      "END:VEVENT",
      "END:VCALENDAR"
    ].join(crlf);
    return ics;
  }
  document.addEventListener("click", function(e) {
    var el = e.target.closest && e.target.closest(".ev-ics-download");
    if (!el) return;
    e.preventDefault();
    var start = el.getAttribute("data-start");
    var end = el.getAttribute("data-end");
    if (!start || !end) return;
    var ics = createCalendarEvent(start, end);
    var blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "ev-charging-slot.ics";
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
})();
"""
    return ui.page_fluid(
        ui.tags.head(
            ui.tags.style(CUSTOM_CSS),
            ui.tags.script(CALENDAR_SCRIPT),
        ),
        ui.div(
            {"class": "ev-dashboard"},
            ui.div(
                {"class": "ev-hero-banner"},
                ui.div(
                    {"class": "ev-hero-banner-inner"},
                    ui.h1(
                        "\u26a1 Smart Charge – Your Smart EV Charging Assistant",
                        class_="ev-hero-title",
                    ),
                    ui.p("Get optimal charging slots in UK", class_="ev-hero-subtext"),
                ),
            ),
            ui.div(
                {"class": "card ev-choice-card"},
                ui.div(
                    {"class": "card-body"},
                    ui.h5("Choose how to set your charging time", class_="card-title"),
                ),
            ),
            ui.div(
                {"class": "row g-4"},
                ui.div(
                    {"class": "col-md-8", "id": "ev-slot-prefs"},
                    ui.div(
                        {"class": "card card-query"},
                        ui.div(
                            {"class": "card-body"},
                            ui.h5("Charging slot preferences", class_="card-title"),
                            ui.input_numeric(
                                "slot_length_hours",
                                "Duration (hours)",
                                value=4,
                                min=0.5,
                                max=24,
                                step=0.5,
                            ),
                            ui.tags.p(
                                "Set how long you want to charge, then click Confirm to apply and refresh slots.",
                                class_="help-text",
                            ),
                            ui.input_action_button("confirm_slot_hours_btn", "Confirm", class_="btn btn-primary mt-2"),
                        ),
                    ),
                    ui.output_ui("hero_recommendation_ui"),
                    ui.output_ui("intensity_card_ui"),
                    ui.output_ui("insight_ui"),
                    ui.output_ui("slots_card_ui"),
                ),
                ui.div(
                    {"class": "col-md-4", "id": "ev-car-make"},
                    ui.div(
                        {"class": "card card-query"},
                        ui.div(
                            {"class": "card-body"},
                            ui.h5(
                                ui.span("Car make and model"),
                                " ",
                                ui.span("Recommended", class_="ev-choice-recommended-tag"),
                                class_="card-title",
                            ),
                            ui.input_text(
                                "car_input",
                                "Describe the vehicle",
                                placeholder="e.g. Tesla Model 3 or Nissan Leaf",
                                value="",
                            ),
                            ui.tags.p("We'll extract make and model.", class_="help-text"),
                            ui.input_action_button("look_up", "Look up", class_="btn btn-primary mt-2"),
                        ),
                    ),
                    ui.output_ui("confirm_card_ui"),
                    ui.output_ui("ev_data_card_ui"),
                ),
            ),
        ),
        title="Smart Charge",
    )
