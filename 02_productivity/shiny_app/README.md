# **<u>UK Carbon Intensity Shiny App</u>**

A Shiny for Python dashboard that queries the **UK Carbon Intensity API** to show carbon intensity and electricity generation mix for a chosen date range. The app uses an IBM Carbon Design–inspired green-energy theme and displays results in a table plus charts (generation mix pie chart and actual vs forecast line plot).

---

## **<u>Table of Contents</u>**

- [For users](#for-users)
  - [How to open the app](#how-to-open-the-app)
  - [How to use the app](#how-to-use-the-app)
- [For developers](#for-developers)
  - [Overview](#overview)
  - [Installation](#installation)
  - [How to run the app](#how-to-run-the-app)
  - [API requirements](#api-requirements)
  - [Screenshots](#screenshots)

---

## **<u>For users</u>**

### **<u>How to open the app</u>**

If the app is already running (e.g. someone started it for you), open your browser and go to:

**<http://127.0.0.1:8000/>**

*The app runs on your machine; no account or API key is needed.*

---

### **<u>How to use the app</u>**

1. **Set the date range** in the "Query parameters" card: click each date field and choose a start and end date. *Start is 00:00 UTC, end is 23:00 UTC.*

2. **Click "Run query"** to fetch carbon intensity and generation mix for that range from the UK Carbon Intensity API.

3. **Review the table** under "Carbon intensity and mix by source": each row is a time period with:
   - **forecast** and **actual** carbon intensity (gCO₂/kWh),
   - **index** (e.g. low/moderate/high),
   - **Generation mix** columns: percentage by fuel (e.g. gas, wind, nuclear, solar).

4. **Check the visual summary** at the bottom:
   - **Pie chart:** average generation mix across all periods in your query (green/teal theme).
   - **Line plot:** actual vs forecast carbon intensity over time; use the legend to tell the lines apart.

5. **Change the date range** and click "Run query" again to explore different periods.

*If the API is unavailable or the request fails, an error message appears in the results area.*

---

## **<u>For developers</u>**

### **<u>Overview</u>**

The app lets users pick a date range, call the [UK Carbon Intensity API](https://api.carbonintensity.org.uk/), and view a merged table of intensity + generation mix plus two charts. *Times are 00:00 UTC for start and 23:00 UTC for end.*

**Structure:**

- [app.py](app.py) — Entry point; wires UI and server, runs the app.
- [ui_components.py](ui_components.py) — UI layout (header, query card, results cards, outputs).
- [server.py](server.py) — Server logic: reactive query on button click, [render.DataGrid](https://shiny.rstudio.com/py/docs/render.mdc#render.DataGrid) for table, [render.plot](https://shiny.rstudio.com/py/docs/render.mdc#render.plot) for pie and line chart.
- [utils.py](utils.py) — API helpers: [fetch_intensity](utils.py), [fetch_generation](utils.py); parses JSON into pandas DataFrames.

---

### **<u>Installation</u>**

1. **Python:** Use Python 3.10+ with `pip` available.

2. **Navigate** to the app directory:
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

### **<u>How to run the app</u>**

From the `shiny_app` folder (with the virtual environment activated if you use one):

```bash
python app.py
```

*Alternatively:*

```bash
shiny run app.py
```

The app starts a local server and may open in your default browser. To open as a user, go to **<http://127.0.0.1:8000/>**. *If using Cursor’s Simple Browser, use an external browser and visit that URL.*

---

### **<u>API requirements</u>**

- **No API key is required.** The [UK Carbon Intensity API](https://api.carbonintensity.org.uk/) is public and does not use authentication.
- **Network access** is required for:
  - `https://api.carbonintensity.org.uk/intensity/{from}/{to}`
  - `https://api.carbonintensity.org.uk/generation/{from}/{to}`
- *No account or sign-up needed.*

---

### **<u>Screenshots</u>**

*Add your own screenshots to the [screenshots](screenshots) folder (e.g. `overview.png`, `charts.png`) and link them here.*

| View | Description |
|------|-------------|
| [screenshots/overview.png](screenshots/overview.png) | *Header, query card, and results table* |
| [screenshots/charts.png](screenshots/charts.png) | *Generation mix pie chart and actual vs forecast line plot* |
