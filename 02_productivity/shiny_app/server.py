# server.py
# Server logic for UK Carbon Intensity Shiny app.
# Pairs with LAB_cursor_shiny_app.md
# Tim Fraser

# Handles query button click, calls API via utils, and renders summary, errors, and table.
# Uses Shiny Core: server(input, output, session) with @render decorators.
# Chart colors: IBM Carbon Design green-energy theme.

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for Shiny
import matplotlib.pyplot as plt
from shiny import reactive, render, Session, ui

from utils import fetch_intensity, fetch_generation

# IBM Carbon Design System — green-energy palette (green + teal)
CARBON_GREEN_TEAL = [
    "#24a148", "#198038", "#42be65", "#6fdc8c", "#a7f0ba",
    "#007d79", "#08bdba", "#3ddbd9", "#9ef0f0", "#d9fbfb",
]
CARBON_BG = "#ffffff"
CARBON_TEXT = "#161616"
CARBON_GREEN_60 = "#198038"
CARBON_TEAL_60 = "#007d79"


def server(input, output, session: Session):
    """
    Server function: runs API query on user request and updates result_summary,
    result_error, and result_table.
    """

    # Store last query results so we show them only after "Run query" is clicked.
    query_result = reactive.Value(None)
    generation_result = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.run_query)
    def _run_query_on_click():
        """When the user clicks Run query, fetch intensity and generation mix."""
        start_date, end_date = input.date_range()
        from_ts = f"{start_date}T00:00Z"
        to_ts = f"{end_date}T23:00Z"
        query_result.set(fetch_intensity(from_ts, to_ts))
        generation_result.set(fetch_generation(from_ts, to_ts))

    @render.ui
    def result_summary():
        """Show a short summary when we have successful data."""
        result = query_result()
        if result is None:
            return ui.p("Select a date range and click Run query.", class_="result-summary text-muted")
        if not result["success"]:
            return None
        df = result["data"]
        if df is None or df.empty:
            return ui.p("No rows returned.", class_="result-summary")
        n = len(df)
        gen = generation_result()
        has_mix = gen and gen.get("success") and gen.get("data") is not None and not gen["data"].empty
        msg = f"Found {n} period(s)." + (" Intensity and mix by source (%)." if has_mix else "")
        return ui.p(msg, class_="result-summary")

    @render.ui
    def result_error():
        """Show an error message when the query failed."""
        result = query_result()
        if result is None or result["success"]:
            return None
        msg = result.get("error_message") or "An error occurred."
        return ui.div(
            ui.div(
                ui.strong("Error: "),
                msg,
                class_="alert alert-danger",
                role="alert",
            ),
        )

    @render.data_frame
    def result_table():
        """
        Render carbon intensity plus intensity mix (generation % by source) in one table.
        Merges intensity with generation on from/to when both are available.
        """
        result = query_result()
        if result is None or not result["success"]:
            return render.DataGrid(pd.DataFrame(), height="200px")
        df = result["data"]
        if df is None or df.empty:
            return render.DataGrid(pd.DataFrame(), height="200px")
        # Merge with generation mix (fuel percentages) when available.
        # Use "from" only as key in case intensity and generation use slightly different "to".
        gen = generation_result()
        if gen and gen.get("success") and gen.get("data") is not None and not gen["data"].empty:
            gen_df = gen["data"].copy()
            fuel_cols = [c for c in gen_df.columns if c not in ("from", "to")]
            if fuel_cols:
                gen_merge = gen_df[["from"] + fuel_cols].drop_duplicates(subset=["from"])
                df = df.merge(gen_merge, on="from", how="left")
                # Rename fuel columns so the header shows "Generation mix: <fuel>"
                group_header = "Generation mix"
                df = df.rename(columns={c: f"{group_header}: {c}" for c in fuel_cols})
        return render.DataGrid(df, height="400px")

    @render.plot
    def pie_chart():
        """Pie chart of average generation mix across all periods in the query."""
        gen = generation_result()
        if not gen or not gen.get("success") or gen.get("data") is None or gen["data"].empty:
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "Run a query to see average generation mix.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        gen_df = gen["data"]
        fuel_cols = [c for c in gen_df.columns if c not in ("from", "to")]
        if not fuel_cols:
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "No mix data.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        avg = gen_df[fuel_cols].mean()
        sizes = avg.tolist()
        if not sizes or all(s == 0 for s in sizes):
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "No mix data.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        # Labels with percentage: "Gas (4.2%)"
        pcts = [s / max(sum(sizes), 1e-9) * 100 for s in sizes]
        labels_with_pct = [f"{c.capitalize()} ({pcts[i]:.1f}%)" for i, c in enumerate(fuel_cols)]
        colors = [CARBON_GREEN_TEAL[i % len(CARBON_GREEN_TEAL)] for i in range(len(sizes))]
        fig, ax = plt.subplots(figsize=(8, 8), facecolor=CARBON_BG)
        ax.set_facecolor(CARBON_BG)
        wedges, _ = ax.pie(
            sizes,
            colors=colors[: len(sizes)],
            startangle=90,
            shadow=False,
            wedgeprops=dict(edgecolor="#e0e0e0", linewidth=0.5),
        )
        ax.legend(
            wedges,
            labels_with_pct,
            title="Generation mix",
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=9,
        )
        ax.set_title("Average generation mix", fontsize=14, fontweight="600", pad=24, color=CARBON_TEXT)
        ax.axis("equal")
        plt.tight_layout(rect=[0, 0, 0.82, 0.88])
        return fig

    @render.plot
    def actual_forecast_chart():
        """Line plot: actual and forecast carbon intensity over the selected period."""
        result = query_result()
        if not result or not result.get("success") or result.get("data") is None or result["data"].empty:
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "Run a query to see actual vs forecast.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        df = result["data"].copy()
        if "from" not in df.columns or ("forecast" not in df.columns and "actual" not in df.columns):
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "No actual/forecast data.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        df["from"] = pd.to_datetime(df["from"], utc=True)
        df = df.sort_values("from")
        has_forecast = "forecast" in df.columns and df["forecast"].notna().any()
        has_actual = "actual" in df.columns and df["actual"].notna().any()
        if not (has_forecast or has_actual):
            fig, ax = plt.subplots(figsize=(4, 4), facecolor=CARBON_BG)
            ax.set_facecolor(CARBON_BG)
            ax.text(0.5, 0.5, "No actual/forecast data.", ha="center", va="center", fontsize=10, color=CARBON_TEXT)
            ax.axis("off")
            return fig
        fig, ax = plt.subplots(figsize=(7, 4), facecolor=CARBON_BG)
        ax.set_facecolor(CARBON_BG)
        if has_forecast:
            ax.plot(df["from"], df["forecast"], color=CARBON_TEAL_60, marker="o", markersize=1.5, label="Forecast", linewidth=0.8)
        if has_actual:
            ax.plot(df["from"], df["actual"], color=CARBON_GREEN_60, marker="s", markersize=1.5, label="Actual", linewidth=0.8)
        ax.set_ylabel("Carbon intensity (gCO₂/kWh)", color=CARBON_TEXT)
        ax.set_xlabel("Time", color=CARBON_TEXT)
        ax.set_title("Actual vs forecast over period", fontsize=14, fontweight="600", pad=24, color=CARBON_TEXT)
        ax.tick_params(colors=CARBON_TEXT)
        for spine in ax.spines.values():
            spine.set_color("#e0e0e0")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=25)
        plt.tight_layout()
        return fig

