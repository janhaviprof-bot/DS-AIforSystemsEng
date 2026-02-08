# **<u>UK Carbon Intensity Shiny App</u>**

A Shiny for Python dashboard that queries the **UK Carbon Intensity API** to show carbon intensity and electricity generation mix for a chosen date range. The app uses an IBM Carbon Design–inspired green-energy theme and displays results in a table plus charts (generation mix pie chart and actual vs forecast line plot).

---

## **<u>Table of Contents</u>**

- [Overview](#overview)
- [Installation](#installation)
- [How to Run the App](#how-to-run-the-app)
- [API Requirements](#api-requirements)
- [Screenshots](#screenshots)
- [Usage Instructions](#usage-instructions)

---

## **<u>Overview</u>**

The app lets you:

- **Pick a date range** (start and end date). *Times are interpreted as 00:00 UTC for start and 23:00 UTC for end.*
- **Run a query** to fetch carbon intensity and generation mix from the [UK Carbon Intensity API](https://api.carbonintensity.org.uk/).
- **View a merged table** of carbon intensity (forecast, actual, index) and generation mix by fuel (e.g. gas, wind, nuclear) as percentages.
- **See a visual summary**: an **average generation mix** pie chart and an **actual vs forecast** line plot over the selected period.

The UI is built with [app.py](app.py), [ui_components.py](ui_components.py), and [server.py](server.py); API calls and parsing are in [utils.py](utils.py).

---

## **<u>Installation</u>**

1. **Python:** Use Python 3.10+ with `pip` available.

2. **Clone or navigate** to the app directory:
   ```bash
   cd path/to/dsai/02_productivity/shiny_app
   ```

3. **Create a virtual environment** *(recommended)*:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

4. **Install dependencies** from [requirements.txt](requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```
   *This installs Shiny, pandas, requests, and matplotlib.*

---

## **<u>How to Run the App</u>**

From the `shiny_app` folder (with the virtual environment activated if you use one):

```bash
python app.py
```

*Alternatively:*

```bash
shiny run app.py
```

The app starts a local server and may open in your default browser automatically. **To open the app as a user**, go to: **<http://127.0.0.1:8000/>** in your browser. *If using Cursor’s Simple Browser, prefer an external browser and visit the URL above.*

---

## **<u>API Requirements</u>**

- **No API key is required.** The [UK Carbon Intensity API](https://api.carbonintensity.org.uk/) is public and does not use authentication.
- **Network access** is required so the app can call:
  - `https://api.carbonintensity.org.uk/intensity/{from}/{to}`
  - `https://api.carbonintensity.org.uk/generation/{from}/{to}`
- **No account or sign-up** is needed. *Just run the app and use a valid date range.*

---

## **<u>Screenshots</u>**

*Add your own screenshots to the [screenshots](screenshots) folder (e.g. `overview.png`, `charts.png`) and link them here for a quick visual of the app.*

| View | Description |
|------|-------------|
| [screenshots/overview.png](screenshots/overview.png) | *Header, query card, and results table* |
| [screenshots/charts.png](screenshots/charts.png) | *Generation mix pie chart and actual vs forecast line plot* |

---

## **<u>Usage Instructions</u>**

1. **Open the app** (see [How to Run the App](#how-to-run-the-app)).
2. **Set the date range** in the "Query parameters" card: click each date field and choose start and end dates. *Start is 00:00 UTC, end is 23:00 UTC.*
3. **Click "Run query"** to fetch intensity and generation mix for that range.
4. **Review the table** under "Carbon intensity and mix by source": each row is a time period with forecast/actual intensity and generation mix percentages by fuel.
5. **Check the visual summary** at the bottom:
   - **Pie chart:** average generation mix across all periods (green/teal Carbon theme).
   - **Line plot:** actual and forecast carbon intensity over time, with a legend.
6. **Change the date range** and click "Run query" again to explore different periods.

*If the API is unavailable or the request fails, an error message appears in the results area.*
