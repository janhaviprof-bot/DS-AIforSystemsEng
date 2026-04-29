# 📌 ACTIVITY

## Serve Model as REST Endpoint

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Start a local endpoint that loads the framework-specific model (`data/modelr.json` for Plumber, `data/modelpy.json` for FastAPI) and predicts Brussels vehicle counts from `day_of_week` and `hour_of_day`.

### 🧱 Stage 1: Run the endpoint locally

Make sure `data/modelr.json` (R) or `data/modelpy.json` (Python) exists (run the matching training script first if needed).

**R (Plumber):**
```r
source("12_end/03_plumber.R")
pr = plumber::plumb("12_end/03_plumber.R")
pr$run(port = 8000)
```
The server starts on `http://localhost:8000`.

**Python (FastAPI):**
```bash
python 12_end/03_serve_model.py
```
The server starts on `http://localhost:8000`.

You can also run helper scripts:
- [`03_plumber/runme.R`](03_plumber/runme.R)
- [`03_fastapi/runme.sh`](03_fastapi/runme.sh)

- [ ] Start the server in one terminal window. Leave it running.
- [ ] In a second terminal or browser, test the endpoint:

```bash
curl "http://localhost:8000/predict?day_of_week=1&hour_of_day=8"
```

Expected response:
```json
{"predicted_vehicle_count": 1423.7}
```

### 🧱 Stage 2: Test with R or Python

You can call the endpoint programmatically, which is exactly what the agent will do in the next activity.

**R:**
```r
library(httr2)
resp <- request("http://localhost:8000/predict") %>%
  req_url_query(day_of_week = 1, hour_of_day = 8) %>%
  req_perform() %>%
  resp_body_json()
resp$predicted_vehicle_count
```

**Python:**
```python
import requests
resp = requests.get("http://localhost:8000/predict", params={"day_of_week": 1, "hour_of_day": 8})
resp.json()["predicted_vehicle_count"]
```

- [ ] Run one of the snippets above and confirm you get back a numeric prediction.
- [ ] Keep your endpoint URL — you will paste it into the next two activities.

---

# 📤 To Submit

- For credit: one screenshot showing a successful `/predict?day_of_week=1&hour_of_day=8` response.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
