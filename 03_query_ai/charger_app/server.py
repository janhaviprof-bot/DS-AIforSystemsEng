# server.py
# Server logic for EV Charger Shiny app.
# Tim Fraser

# Two-phase flow: (1) Look up -> Ollama extracts make/model -> show confirmation UI.
# (2) Confirm -> fetch EV data from API -> display make, model, battery, charge, charging time.

from shiny import reactive, render, Session, ui

from urllib.parse import quote

from utils import (
    parse_make_model_with_ollama,
    fetch_ev_from_api,
    fetch_ev_from_llama,
    charging_time_hours,
    fetch_intensity_48h,
    suggest_charging_slots_llama,
    utc_now_iso8601_halfhour,
    format_utc_to_uk_display,
    format_utc_to_uk_display_with_date,
    _parse_iso8601_utc,
    iso8601_to_google_date,
)


def server(input, output, session: Session):
    """
    Server function: on Look up, call Ollama and show confirm UI;
    on Confirm, call API and show EV data and charging time.
    """

    # Inferred make/model from Ollama (None or dict with make/model or error_message)
    inferred_result = reactive.Value(None)
    # EV data from API after confirm (None or dict with success, data, error_message)
    ev_result = reactive.Value(None)
    # Charging slots from Carbon Intensity + LLM (None or { success, slots, error_message })
    slots_result = reactive.Value(None)
    # Last 48h intensity data (list of { from, to, forecast, index }) for timeline strip
    intensity_data = reactive.Value(None)
    # True while slots recommendation is being fetched
    slots_loading = reactive.Value(False)

    @reactive.Effect
    @reactive.event(input.look_up)
    def _on_look_up():
        """When the user clicks Look up, call Ollama and store inferred make/model."""
        text = input.car_input()
        result = parse_make_model_with_ollama(text or "")
        if result["success"]:
            inferred_result.set({"make": result["make"], "model": result["model"]})
        else:
            inferred_result.set({"error_message": result["error_message"]})
        # Clear previous EV result and slots when starting a new lookup
        ev_result.set(None)
        slots_result.set(None)
        intensity_data.set(None)

    @render.ui
    def confirm_ui():
        """Show confirmation message and editable make/model fields with Confirm button."""
        inf = inferred_result()
        if inf is None:
            return ui.p("Enter a car above and click Look up.", class_="text-muted")
        if "error_message" in inf:
            return ui.div(
                ui.strong("Error: "),
                inf["error_message"],
                class_="alert alert-danger",
                role="alert",
            )
        make = inf.get("make") or ""
        model = inf.get("model") or ""
        return ui.TagList(
            ui.p(
                ui.strong("We understood: "),
                
            ),
            ui.div(
                {"class": "row g-2 mb-2"},
                ui.div(
                    {"class": "col-md-6"},
                    ui.input_text("make_edit", "Make", value=make),
                ),
                ui.div(
                    {"class": "col-md-6"},
                    ui.input_text("model_edit", "Model", value=model),
                ),
            ),
            ui.input_action_button("confirm_btn", "Confirm", class_="btn btn-primary"),
        )

    @render.ui
    def confirm_card_ui():
        """Show Confirm vehicle card only when user has clicked Look up (inferred_result set)."""
        if inferred_result() is None:
            return None
        return ui.div(
            {"class": "card card-confirm"},
            ui.div(
                {"class": "card-body"},
                ui.h5("Confirm vehicle", class_="card-title"),
                ui.output_ui("confirm_ui"),
            ),
        )

    @reactive.Effect
    @reactive.event(input.confirm_btn)
    def _on_confirm():
        """When the user clicks Confirm, fetch EV data from API; if none, fall back to LLM."""
        try:
            make = input.make_edit()
        except Exception:
            make = ""
        try:
            model = input.model_edit()
        except Exception:
            model = ""
        api_result = fetch_ev_from_api(make, model)
        if api_result.get("success") and api_result.get("data"):
            ev_result.set(api_result)
            slots_result.set(None)
            _run_slots_flow()
            return
        # API returned no data or error: try LLM fallback (only when API said "no vehicle found" or empty)
        llm_result = fetch_ev_from_llama(make, model)
        if llm_result.get("success") and llm_result.get("data"):
            ev_result.set(llm_result)
            slots_result.set(None)
            _run_slots_flow()
            return
        # Both failed: show API error or combined message
        if api_result.get("error_message") and llm_result.get("error_message"):
            api_result["error_message"] = (
                "No data from API and could not infer specs. "
                + api_result["error_message"]
                + " Try a different make/model."
            )
        elif llm_result.get("error_message"):
            api_result["error_message"] = (
                api_result.get("error_message") or ""
                + " Could not infer specs from LLM either. Try a different make/model."
            ).strip() or llm_result["error_message"]
        ev_result.set(api_result)
        slots_result.set(None)

    @render.ui
    def result_error():
        """Show error only when there is no data to display (hard failure)."""
        res = ev_result()
        if res is None:
            return None
        # Do not show error panel when we have data (e.g. LLM fallback)
        if res.get("success") and res.get("data"):
            return None
        msg = res.get("error_message") or "An error occurred."
        return ui.div(
            ui.strong("Error: "),
            msg,
            class_="alert alert-danger",
            role="alert",
        )

    @render.ui
    def result_ui():
        """Display EV data and charging time as premium card; show disclaimer when source is LLM fallback."""
        res = ev_result()
        if res is None:
            return ui.p("Confirm the vehicle above to fetch EV data.", class_="text-muted")
        if not res.get("success") or not res.get("data"):
            return None
        vehicles = res["data"]
        v = vehicles[0] if vehicles else {}
        make = v.get("make", "")
        model = v.get("model", "")
        battery_nominal = v.get("battery_capacity", "")
        battery_usable = v.get("battery_useable_capacity", "")
        charge = v.get("charge_power", "")
        battery_for_time = battery_usable if battery_usable else battery_nominal
        hours = charging_time_hours(battery_for_time, charge)
        # One battery value for display: usable if present, else nominal (hide nominal when premium placeholder)
        show_nominal = battery_nominal and "premium" not in str(battery_nominal).lower()
        battery_display = battery_usable if battery_usable else (battery_nominal if show_nominal else "")
        parts = []
        if res.get("source") == "llm":
            parts.append(
                ui.div(
                    ui.strong("Note: "),
                    "Authorized data for this model could not be found through the API. "
                    "The following values are from public/general information and may vary.",
                    class_="alert alert-warning mb-3",
                    role="alert",
                )
            )
        spec_rows = []
        if battery_display:
            spec_rows.append(
                ui.div(
                    ui.span("\U0001f50b", class_="ev-spec-icon"),
                    ui.span("Battery", class_="ev-spec-label"),
                    ui.span(battery_display, class_="ev-spec-value"),
                    class_="ev-spec-row",
                )
            )
        if charge:
            spec_rows.append(
                ui.div(
                    ui.span("\u26a1", class_="ev-spec-icon"),
                    ui.span("Charge power", class_="ev-spec-label"),
                    ui.span(charge, class_="ev-spec-value"),
                    class_="ev-spec-row",
                )
            )
        if hours is not None:
            spec_rows.append(
                ui.div(
                    ui.span("\u23f1", class_="ev-spec-icon"),
                    ui.span("Charging time", class_="ev-spec-label"),
                    ui.span(f"~{hours} hours", class_="ev-spec-value"),
                    class_="ev-spec-row",
                )
            )
        if hours is not None and battery_usable:
            insight_text = f"0–100% in ~{hours} hours based on usable capacity."
        elif hours is not None and battery_nominal and "premium" not in str(battery_nominal).lower():
            insight_text = f"0–100% in ~{hours} hours based on nominal capacity."
        elif hours is not None:
            insight_text = f"0–100% in ~{hours} hours."
        else:
            insight_text = "Set battery and charge power above for charging time estimate."
        card = ui.div(
            ui.div(f"{make} {model}".strip() or "Vehicle", class_="ev-vehicle-header"),
            *spec_rows,
            ui.div(insight_text, class_="ev-vehicle-insight"),
            class_="ev-vehicle-card ev-vehicle-card-enter",
        )
        parts.append(card)
        return ui.TagList(parts)

    @render.ui
    def ev_data_card_ui():
        """Show EV data and charging time card only when a vehicle has been confirmed (ev_result set)."""
        if ev_result() is None:
            return None
        return ui.div(
            {"class": "card card-results"},
            ui.div(
                {"class": "card-body"},
                ui.h5("EV data and charging time", class_="card-title"),
                ui.output_ui("result_error"),
                ui.output_ui("result_ui"),
            ),
        )

    def _run_slots_flow():
        """Run slots flow: effective_hours from left (slot length) and/or right (vehicle). Fetch intensity, call LLM, set slots_result."""
        slots_loading.set(True)
        try:
            try:
                user_slot_length = float(input.slot_length_hours() or 4)
            except (TypeError, ValueError):
                user_slot_length = 4.0
            user_slot_length = max(0.5, min(24.0, user_slot_length))
            res = ev_result()
            if res and res.get("success") and res.get("data"):
                vehicles = res["data"]
                v = vehicles[0] if vehicles else {}
                battery_usable = v.get("battery_useable_capacity", "")
                battery_nominal = v.get("battery_capacity", "")
                charge = v.get("charge_power", "")
                battery_for_time = battery_usable if battery_usable else battery_nominal
                hours = charging_time_hours(battery_for_time, charge)
                if hours is not None and hours > 0:
                    effective_hours = max(hours, user_slot_length)
                else:
                    effective_hours = user_slot_length
            else:
                effective_hours = user_slot_length
            if effective_hours < 0.5:
                slots_result.set({"success": False, "slots": [], "error_message": "Slot length must be at least 0.5 hours."})
                return
            from_ts = utc_now_iso8601_halfhour()
            intensity_res = fetch_intensity_48h(from_ts)
            if not intensity_res.get("success") or not intensity_res.get("data"):
                slots_result.set({"success": False, "slots": [], "error_message": intensity_res.get("error_message") or "Failed to fetch carbon intensity."})
                return
            intensity_data.set(intensity_res["data"])
            llm_res = suggest_charging_slots_llama(effective_hours, intensity_res["data"])
            slots_result.set(llm_res)
        finally:
            slots_loading.set(False)

    @reactive.Effect
    @reactive.event(input.confirm_slot_hours_btn)
    def _on_confirm_slot_hours():
        """When user confirms slot length (hours), run the slots flow."""
        _run_slots_flow()

    @reactive.Effect
    @reactive.event(input.get_slots_btn)
    def _on_get_slots():
        """Manual refresh: run the slots flow."""
        _run_slots_flow()

    MAX_CALENDAR_SLOTS = 10

    def _show_calendar_modal_for_slot(slot_index: int):
        """Build and show 'Add to calendar' modal for the slot at the given index."""
        slots_res = slots_result()
        if not slots_res or not slots_res.get("success"):
            return
        slot_list = slots_res.get("slots") or []
        if slot_index < 0 or slot_index >= len(slot_list):
            return
        slot = slot_list[slot_index]
        start_iso = slot.get("start") or ""
        end_iso = slot.get("end") or ""
        start_google = iso8601_to_google_date(start_iso)
        end_google = iso8601_to_google_date(end_iso)
        if not start_google or not end_google:
            return
        title = "EV Charging (Low carbon window)"
        description = "Best time to charge based on low carbon intensity"
        location = "Home"
        base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
        params = f"&text={quote(title)}&dates={start_google}/{end_google}&details={quote(description)}&location={quote(location)}"
        google_url = base + params
        modal = ui.modal(
            ui.div(
                ui.tags.a(
                    "Add to Google Calendar",
                    href=google_url,
                    target="_blank",
                    rel="noopener noreferrer",
                    class_="ev-calendar-btn ev-calendar-btn-primary",
                ),
                ui.tags.a(
                    "Use Apple/Outlook? Download .ics",
                    href="#",
                    class_="ev-ics-download ev-calendar-fallback",
                    data_start=start_google,
                    data_end=end_google,
                ),
                class_="ev-calendar-modal-body",
            ),
            title="Add charging slot to calendar",
            size="s",
            easy_close=True,
            footer=None,
        )
        ui.modal_show(modal)

    @reactive.Effect
    @reactive.event(input.charge_now_btn)
    def _on_charge_now():
        """Show calendar modal for hero (slot 0)."""
        _show_calendar_modal_for_slot(0)

    for _slot_idx in range(MAX_CALENDAR_SLOTS):
        _inp = input[f"calendar_slot_{_slot_idx}"]

        @reactive.Effect
        @reactive.event(_inp)
        def _show_calendar_for_slot(idx=_slot_idx):
            _show_calendar_modal_for_slot(idx)

    @render.ui
    def hero_recommendation_ui():
        """Single prominent card: #1 slot only — large time, intensity badge, reason, CTA. Shown when slots loaded."""
        if slots_loading():
            return None
        slots_res = slots_result()
        if slots_res is None or not slots_res.get("success"):
            return None
        slot_list = slots_res.get("slots") or []
        if not slot_list:
            return None
        slot = slot_list[0]
        start_uk = format_utc_to_uk_display_with_date(slot.get("start", ""))
        end_uk = format_utc_to_uk_display_with_date(slot.get("end", ""))
        reason = (slot.get("reason") or "").strip()
        idx = (slot.get("intensity_index") or "moderate").lower()
        slot_bg = {"low": "#22c55e", "moderate": "#eab308", "high": "#ef4444"}
        slot_fg = {"low": "#ffffff", "moderate": "#1e293b", "high": "#ffffff"}
        bg = slot_bg.get(idx, slot_bg["moderate"])
        fg = slot_fg.get(idx, slot_fg["moderate"])
        badge_label = idx.capitalize()
        return ui.div(
            ui.span(badge_label, class_="hero-recommendation-badge", style=f"background: {bg}; color: {fg};"),
            ui.div(
                f"{start_uk} – {end_uk}",
                class_="hero-recommendation-time",
                style=f"color: var(--ev-text);",
            ),
            ui.p(reason or "Lowest carbon intensity in the next 48 hours.", class_="hero-recommendation-reason", style=f"color: var(--ev-muted);"),
            ui.input_action_button("charge_now_btn", "Charge in this window", class_="btn btn-primary"),
            class_="hero-recommendation",
        )

    @render.ui
    def insight_ui():
        """Short copy (1–2 sentences) why this time was recommended. Muted block below graph."""
        if slots_loading():
            return None
        slots_res = slots_result()
        if slots_res is None or not slots_res.get("success"):
            return None
        slot_list = slots_res.get("slots") or []
        if not slot_list:
            return None
        reason = (slot_list[0].get("reason") or "").strip()
        if reason:
            text = f"This window has the lowest carbon intensity in the next 48 hours. {reason}"
        else:
            text = "This window has the lowest carbon intensity in the next 48 hours."
        return ui.div(text, class_="insight-section")

    @render.ui
    def intensity_ui():
        """Carbon intensity (next 48h) bar strip with highlighted region over the recommended slot."""
        data = intensity_data()
        if not data or not isinstance(data, list):
            return None
        rows = data[:96]
        bar_colors = {"low": "#22c55e", "moderate": "#eab308", "high": "#ef4444"}
        max_forecast = 400
        bars = []
        for row in rows:
            idx = (row.get("index") or "moderate").strip().lower()
            color = bar_colors.get(idx, bar_colors["moderate"])
            f = row.get("forecast")
            try:
                pct = min(100, (float(f) / max_forecast) * 100) if f is not None else 50
            except (TypeError, ValueError):
                pct = 50
            from_val = row.get("from", "")
            title = f"{from_val}: {idx} ({f} gCO2/kWh)" if f is not None else from_val
            bars.append(
                ui.span(
                    title=title,
                    class_="intensity-bar",
                    style=f"background-color: {color}; height: {max(12, pct)}%;",
                )
            )
        if not bars:
            return None
        strip_el = ui.div(*bars, class_="intensity-strip")
        highlight_left_pct = 0.0
        highlight_width_pct = 0.0
        slots_res = slots_result()
        if slots_res and slots_res.get("success"):
            slot_list = slots_res.get("slots") or []
            if slot_list and rows:
                slot = slot_list[0]
                start_dt = _parse_iso8601_utc(slot.get("start") or "")
                end_dt = _parse_iso8601_utc(slot.get("end") or "")
                if start_dt is not None and end_dt is not None:
                    first_from = _parse_iso8601_utc(str(rows[0].get("from") or ""))
                    if first_from is not None and len(rows) > 0:
                        last_row = rows[-1]
                        last_to = _parse_iso8601_utc(str(last_row.get("to") or ""))
                        if last_to is not None:
                            total_span = (last_to - first_from).total_seconds()
                            if total_span > 0:
                                start_sec = max(0, min(total_span, (start_dt - first_from).total_seconds()))
                                end_sec = max(0, min(total_span, (end_dt - first_from).total_seconds()))
                                highlight_left_pct = 100 * start_sec / total_span
                                highlight_width_pct = 100 * (end_sec - start_sec) / total_span
        if highlight_width_pct > 0:
            overlay = ui.div(
                class_="intensity-highlight",
                style=f"left: {highlight_left_pct}%; width: {highlight_width_pct}%;",
            )
            return ui.div(ui.div(strip_el, overlay, class_="intensity-graph-wrap"))
        return ui.div(ui.div(strip_el, class_="intensity-graph-wrap"))

    @render.ui
    def intensity_card_ui():
        """Show Carbon intensity card only when intensity data is available."""
        data = intensity_data()
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        return ui.div(
            {"class": "card card-results"},
            ui.div(
                {"class": "card-body"},
                ui.h5("Carbon intensity (next 48h)", class_="card-title"),
                ui.output_ui("intensity_ui"),
            ),
        )

    @render.ui
    def slots_ui():
        """Slot list (vertical cards, scroll when >3). Loading shows spinner."""
        if slots_loading():
            return ui.div("Finding best times…", class_="slots-loading")
        slots_res = slots_result()
        if slots_res is None:
            return ui.p(
                "Set duration above and click Get recommendations to see slots.",
                class_="text-muted",
            )
        if not slots_res.get("success"):
            return ui.div(
                ui.strong("Error: "),
                slots_res.get("error_message") or "Could not get slots.",
                class_="alert alert-danger",
                role="alert",
            )
        slot_list = slots_res.get("slots") or []
        if not slot_list:
            return ui.p("No slots could be suggested. Try again later.", class_="text-muted")
        slot_bg = {"low": "#22c55e", "moderate": "#eab308", "high": "#ef4444"}
        slot_fg = {"low": "#ffffff", "moderate": "#1e293b", "high": "#ffffff"}
        scrollable = len(slot_list) > 3
        card_flex = "0 0 200px" if scrollable else "1 1 200px"
        slot_cards = []
        for i in range(len(slot_list)):
            slot = slot_list[i]
            start_uk = format_utc_to_uk_display_with_date(slot.get("start", ""))
            end_uk = format_utc_to_uk_display_with_date(slot.get("end", ""))
            reason = slot.get("reason", "")
            idx = (slot.get("intensity_index") or "moderate").lower()
            bg = slot_bg.get(idx, slot_bg["moderate"])
            fg = slot_fg.get(idx, slot_fg["moderate"])
            card_class = "card slot-card slot-card-hero-dupe mb-0" if i == 0 else "card slot-card mb-0"
            card_style = f"background-color: {bg}; color: {fg}; min-width: 200px; flex: {card_flex};"
            card_body_children = [
                ui.h6(f"Slot {i + 1}", class_="card-title mb-2"),
                ui.p(f"{start_uk} – {end_uk}", class_="mb-1 small"),
                ui.span(reason, style="opacity: 0.9;", class_="small"),
            ]
            if i < MAX_CALENDAR_SLOTS:
                card_body_children.append(
                    ui.div(
                        ui.input_action_button(
                            f"calendar_slot_{i}",
                            "Add to calendar",
                            class_="ev-slot-calendar-btn btn btn-sm mt-2",
                        ),
                        class_="ev-slot-calendar-wrap",
                    ),
                )
            card = ui.div(
                ui.div(
                    *card_body_children,
                    class_="card-body",
                ),
                class_=card_class,
                style=card_style,
            )
            slot_cards.append(card)
        if scrollable:
            scroll_id = "slots-scroll-container"
            scroll_amt = 220
            left_btn = ui.tags.button(
                "\u2190",
                type="button",
                class_="btn btn-outline-secondary slots-scroll-arrow",
                style="min-width: 2.5rem;",
                onclick=f"var e=document.getElementById('{scroll_id}'); if(e) e.scrollLeft -= {scroll_amt};",
            )
            right_btn = ui.tags.button(
                "\u2192",
                type="button",
                class_="btn btn-outline-secondary slots-scroll-arrow",
                style="min-width: 2.5rem;",
                onclick=f"var e=document.getElementById('{scroll_id}'); if(e) e.scrollLeft += {scroll_amt};",
            )
            return ui.div(
                left_btn,
                ui.div(
                    ui.div(
                        *slot_cards,
                        class_="d-flex flex-row flex-nowrap gap-2 mt-2",
                    ),
                    id=scroll_id,
                    class_="mb-2 flex-grow-1 slots-scroll-area",
                    style="overflow-x: auto; overflow-y: hidden; max-width: 100%; min-width: 0;",
                ),
                right_btn,
                class_="d-flex flex-row align-items-center gap-1 mt-2",
                style="max-width: 100%;",
            )
        return ui.div(
            *slot_cards,
            class_="d-flex flex-row flex-wrap gap-2 mt-2",
        )

    @render.ui
    def slots_card_ui():
        """Show All recommended slots card only when slots have been requested (loading or result)."""
        if slots_loading() or slots_result() is not None:
            return ui.div(
                {"class": "card card-results"},
                ui.div(
                    {"class": "card-body"},
                    ui.h5("All recommended slots", class_="card-title"),
                    ui.output_ui("slots_ui"),
                ),
            )
        return None
