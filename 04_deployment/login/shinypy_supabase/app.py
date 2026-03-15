# app.py
# Supabase-authenticated Shiny for Python app
# Tim Fraser
#
# This app demonstrates Supabase email/password authentication to protect app content.
# Users must sign up or sign in with Supabase before accessing the restaurant tipping dashboard.

import os
import time
import requests
import faicons as fa
import pandas as pd

# Load data and compute static values
from shiny import reactive, render
from shiny.express import input, ui

# Supabase configuration
# Get credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_PUBLIC_KEY = os.getenv("SUPABASE_PUBLIC_KEY", "")

# Reactive authentication state
# Tracks whether the current session has successfully authenticated
auth_ok = reactive.Value(False)
user_email = reactive.Value("")
session_token = reactive.Value("")
refresh_token = reactive.Value("")
token_expires_at = reactive.Value(0.0)

tips = pd.read_csv("data/tips.csv")
bill_rng = (min(tips.total_bill), max(tips.total_bill))

# Supabase authentication functions
def normalize_auth_payload(data: dict) -> dict:
    """Normalize auth responses across REST and SDK-like response shapes."""
    user = data.get("user") or {}
    session = data.get("session")

    # Raw GoTrue REST responses return token fields at top level.
    if not session and data.get("access_token"):
        session = {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in")
        }

    return {"user": user, "session": session}


def supabase_sign_up(email: str, password: str) -> dict:
    """Create a new user account in Supabase"""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={
                "apikey": SUPABASE_PUBLIC_KEY,
                "Content-Type": "application/json"
            },
            json={"email": email, "password": password}
        )
        # Supabase signup can return 200 OK or 201 Created
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                normalized = normalize_auth_payload(data)
                return {"success": True, "user": normalized["user"], "session": normalized["session"]}
            except ValueError:
                return {"success": False, "error": "Invalid response format from server"}
        else:
            # Handle error response
            try:
                error_data = response.json()
                # Check multiple possible error field names
                error_msg = (
                    error_data.get("error_description") or 
                    error_data.get("message") or 
                    error_data.get("error") or 
                    f"Signup failed (status {response.status_code})"
                )
            except ValueError:
                # Non-JSON error response
                error_msg = f"Signup failed (status {response.status_code}): {response.text[:200]}"
            return {"success": False, "error": error_msg}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def supabase_sign_in(email: str, password: str) -> dict:
    """Authenticate user with email/password via Supabase"""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_PUBLIC_KEY,
                "Content-Type": "application/json"
            },
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            try:
                data = response.json()
                normalized = normalize_auth_payload(data)
                return {"success": True, "user": normalized["user"], "session": normalized["session"]}
            except ValueError:
                return {"success": False, "error": "Invalid response format from server"}
        else:
            # Handle error response
            try:
                error_data = response.json()
                # Check multiple possible error field names
                error_msg = (
                    error_data.get("error_description") or 
                    error_data.get("message") or 
                    error_data.get("error") or 
                    f"Login failed (status {response.status_code})"
                )
            except ValueError:
                # Non-JSON error response
                error_msg = f"Login failed (status {response.status_code}): {response.text[:200]}"
            return {"success": False, "error": error_msg}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def supabase_refresh_session(refresh_token_value: str) -> dict:
    """Refresh access token using a Supabase refresh token."""
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={
                "apikey": SUPABASE_PUBLIC_KEY,
                "Content-Type": "application/json"
            },
            json={"refresh_token": refresh_token_value}
        )
        if response.status_code == 200:
            data = response.json()
            normalized = normalize_auth_payload(data)
            return {"success": True, "user": normalized["user"], "session": normalized["session"]}

        try:
            error_data = response.json()
            error_msg = (
                error_data.get("error_description")
                or error_data.get("message")
                or error_data.get("error")
                or f"Token refresh failed (status {response.status_code})"
            )
        except ValueError:
            error_msg = f"Token refresh failed (status {response.status_code}): {response.text[:200]}"
        return {"success": False, "error": error_msg}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def supabase_remote_sign_out(access_token: str) -> None:
    """Best-effort Supabase sign-out to invalidate remote refresh tokens."""
    if not access_token:
        return
    try:
        requests.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            headers={
                "apikey": SUPABASE_PUBLIC_KEY,
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )
    except Exception:
        # Local sign-out still proceeds if remote sign-out fails.
        pass

def supabase_sign_out():
    """Sign out user (clears local session state)"""
    auth_ok.set(False)
    user_email.set("")
    session_token.set("")
    refresh_token.set("")
    token_expires_at.set(0.0)

# Add page title and sidebar
ui.page_opts(title="Restaurant tipping", fillable=True)

with ui.sidebar(open="desktop"):
    if not auth_ok():
        # Authentication section (shown when not logged in)
        ui.h5("Sign In or Sign Up")
        ui.input_text("auth_email", "Email", "")
        ui.input_password("auth_password", "Password", "")
        ui.input_action_button("sign_in_btn", "Sign In")
        ui.input_action_button("sign_up_btn", "Sign Up")
        ui.hr()
        ui.output_ui("auth_message")
    else:
        # User info and logout (shown when logged in)
        ui.h5(f"Logged in as:")
        ui.p(user_email())
        ui.input_action_button("sign_out_btn", "Sign Out")
        ui.hr()
        # Filter inputs (only visible after authentication)
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
@reactive.event(input.sign_in_btn)
def _():
    """Handle sign in button click"""
    if not SUPABASE_URL or not SUPABASE_PUBLIC_KEY:
        ui.notification_show(
            "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
            type="error",
            duration=5
        )
        return
    
    email = input.auth_email()
    password = input.auth_password()
    
    if not email or not password:
        ui.notification_show("Please enter both email and password", type="error", duration=3)
        return
    
    result = supabase_sign_in(email, password)
    
    if result["success"]:
        auth_ok.set(True)
        user_email.set((result.get("user") or {}).get("email", email))
        session_data = result.get("session") or {}
        session_token.set(session_data.get("access_token", ""))
        refresh_token.set(session_data.get("refresh_token", ""))
        expires_in = session_data.get("expires_in") or 0
        token_expires_at.set(time.time() + max(0, int(expires_in) - 30))
        ui.notification_show("Signed in successfully!", type="message", duration=3)
    else:
        ui.notification_show(f"Sign in failed: {result['error']}", type="error", duration=5)

@reactive.effect
@reactive.event(input.sign_up_btn)
def _():
    """Handle sign up button click"""
    if not SUPABASE_URL or not SUPABASE_PUBLIC_KEY:
        ui.notification_show(
            "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
            type="error",
            duration=5
        )
        return
    
    email = input.auth_email()
    password = input.auth_password()
    
    if not email or not password:
        ui.notification_show("Please enter both email and password", type="error", duration=3)
        return
    
    result = supabase_sign_up(email, password)
    
    if result["success"]:
        ui.notification_show("Account created! Please sign in.", type="message", duration=3)
    else:
        ui.notification_show(f"Sign up failed: {result['error']}", type="error", duration=5)

@reactive.effect
@reactive.event(input.sign_out_btn)
def _():
    """Handle sign out button click"""
    supabase_remote_sign_out(session_token())
    supabase_sign_out()
    ui.notification_show("Signed out successfully", type="message", duration=2)

@reactive.effect
def _():
    """Refresh session token periodically for longer sessions."""
    reactive.invalidate_later(60)
    if not auth_ok():
        return

    # Refresh shortly before expiration.
    expires_at = token_expires_at()
    if not expires_at or (expires_at - time.time()) > 90:
        return

    current_refresh_token = refresh_token()
    if not current_refresh_token:
        return

    result = supabase_refresh_session(current_refresh_token)
    if result["success"] and result.get("session"):
        session_data = result["session"]
        session_token.set(session_data.get("access_token", ""))
        refresh_token.set(session_data.get("refresh_token", current_refresh_token))
        expires_in = session_data.get("expires_in") or 0
        token_expires_at.set(time.time() + max(0, int(expires_in) - 30))
    else:
        # If refresh fails, treat session as expired and require sign-in again.
        supabase_sign_out()
        ui.notification_show("Session expired. Please sign in again.", type="warning", duration=5)

@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_slider("total_bill", value=bill_rng)
    ui.update_checkbox_group("time", selected=["Lunch", "Dinner"])

@render.ui
def auth_message():
    """Display authentication status message"""
    if not SUPABASE_URL or not SUPABASE_PUBLIC_KEY:
        return ui.p(
            "⚠️ Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
            class_="text-warning"
        )
    return ui.p("")
