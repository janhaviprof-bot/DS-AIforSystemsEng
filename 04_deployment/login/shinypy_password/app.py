# app.py
# Password-protected Shiny for Python app
# Tim Fraser
#
# This app demonstrates a minimal password gate to protect app content.
# This simulates protecting an API key (like OPENAI_API_KEY) from casual,
# unwanted queries. Note: This is educational only and does NOT provide
# real security, especially when code is client-visible (e.g., Shinylive).

import os
import faicons as fa
import pandas as pd

# Load data and compute static values
from shiny import reactive, render
from shiny.express import input, ui

# Password configuration
# This simulates protecting a secret like OPENAI_API_KEY from casual use
APP_PASSWORD = os.getenv("SHINY_APP_PASSWORD", "demo")

# Reactive authentication flag
# Tracks whether the current session has successfully authenticated
auth_ok = reactive.Value(False)

tips = pd.read_csv("data/tips.csv")
ui.include_css("styles.css")

bill_rng = (min(tips.total_bill), max(tips.total_bill))

# Add page title and sidebar
ui.page_opts(title="Restaurant tipping", fillable=True)

with ui.sidebar(open="desktop"):
    # Password authentication section
    ui.input_password("password", "Password", "")
    ui.input_action_button("login", "Log in")
    ui.hr()
    # Existing filter inputs (only visible after authentication)
    ui.input_slider(
        "total_bill",
        "Bill amount",
        min=bill_rng[0],
        max=bill_rng[1],
        value=bill_rng,
        pre="$",
    )
    ui.input_checkbox_group(
        "time",
        "Food service",
        ["Lunch", "Dinner"],
        selected=["Lunch", "Dinner"],
        inline=True,
    )
    ui.input_action_button("reset", "Reset filter")

# Add main content
ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "currency-dollar": fa.icon_svg("dollar-sign"),
}

with ui.layout_columns(fill=False):
    with ui.value_box(showcase=ICONS["user"]):
        "Total tippers"

        @render.express
        def total_tippers():
            if not auth_ok():
                "—"
            else:
                tips_data().shape[0]

    with ui.value_box(showcase=ICONS["wallet"]):
        "Average tip"

        @render.express
        def average_tip():
            if not auth_ok():
                "—"
            else:
                d = tips_data()
                if d.shape[0] > 0:
                    perc = d.tip / d.total_bill
                    f"{perc.mean():.1%}"

    with ui.value_box(showcase=ICONS["currency-dollar"]):
        "Average bill"

        @render.express
        def average_bill():
            if not auth_ok():
                "—"
            else:
                d = tips_data()
                if d.shape[0] > 0:
                    bill = d.total_bill.mean()
                    f"${bill:.2f}"


with ui.card(full_screen=True):
    ui.card_header("Tips data")

    @render.data_frame
    def table():
        if not auth_ok():
            return render.DataGrid(pd.DataFrame())
        else:
            return render.DataGrid(tips_data())




# --------------------------------------------------------
# Reactive calculations and effects
# --------------------------------------------------------


@reactive.calc
def tips_data():
    # Return empty DataFrame if not authenticated
    if not auth_ok():
        return pd.DataFrame()
    bill = input.total_bill()
    idx1 = tips.total_bill.between(bill[0], bill[1])
    idx2 = tips.time.isin(input.time())
    return tips[idx1 & idx2]


@reactive.effect
@reactive.event(input.login)
def _():
    # Check password and update authentication status
    if input.password() == APP_PASSWORD:
        auth_ok.set(True)
    else:
        auth_ok.set(False)
        ui.notification_show("Incorrect password", type="error", duration=3)


@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_slider("total_bill", value=bill_rng)
    ui.update_checkbox_group("time", selected=["Lunch", "Dinner"])
