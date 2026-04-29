# 📌 ACTIVITY

## Query Model Endpoint with AI Agent

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Connect your deployed endpoint to a tool-calling script so the agent can request a prediction for a specific day and hour.

### 🧱 Stage 1: Configure endpoint

- [ ] Open [`04_agent_query.R`](04_agent_query.R) or [`04_agent_query.py`](04_agent_query.py).
- [ ] Find the `ENDPOINT_URL` variable near the top and paste in your live URL from the previous activity.

```r
# R
ENDPOINT_URL <- "https://your-live-url"
```

```python
# Python
ENDPOINT_URL = "https://your-live-url"
```

If you are still testing locally, leave it as `http://localhost:8000` and keep your server running.

### 🧱 Stage 2: Run and modify prompts

- [ ] Change the prompt to something like:

> "Predict Brussels vehicle count for Monday at 8 AM."

- [ ] Run the script and confirm the tool call uses `day_of_week` and `hour_of_day`.
- [ ] Try one more day/hour prompt and confirm the tool call still maps correctly.

---

# 📤 To Submit

- For credit: one screenshot showing both values printed by the script (`Agent result` and `Direct API call`).

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
