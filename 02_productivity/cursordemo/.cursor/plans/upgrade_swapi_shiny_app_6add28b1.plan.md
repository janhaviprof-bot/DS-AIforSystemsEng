---
name: Upgrade SWAPI Shiny App
overview: Fix Plotly rendering, auto-fetch on startup, improve table display, add card descriptions, add prominent title, and switch to dark theme with compatible colors.
todos:
  - id: fix-plotly
    content: Fix Plotly reactivity - ensure plot reacts to both people_df() and input$trait, add default fallback for trait, verify data structure
    status: completed
  - id: auto-fetch
    content: Add automatic API fetch on app startup using observe() or session$onFlushed()
    status: completed
  - id: fix-table
    content: Fix table cutoff by adding autoWidth, proper scrollX, and width settings to DT options
    status: completed
  - id: card-text
    content: Add descriptive text to each card explaining what it shows
    status: completed
  - id: add-title
    content: Add prominent h1 title at top of UI
    status: completed
  - id: dark-theme
    content: Switch to dark theme (darkly/cyborg), update color palette for dark backgrounds, adjust plotly colors
    status: completed
  - id: todo-1770215284987-5k43ztqc9
    content: ""
    status: pending
isProject: false
---

# Upgrade SWAPI Shiny App

## Issues Identified

1. **Plotly not showing data**: The plotly output may not be properly reactive to `input$trait` changes, and the initial render when `input$trait` is NULL returns an empty plot.
2. **Manual API fetch**: Data only loads when button is clicked; should auto-fetch on startup.
3. **Table cutoff**: DT table needs better width/scroll handling.
4. **Missing card descriptions**: Each card needs explanatory text.
5. **No prominent title**: Only page title exists; needs a visible header.
6. **Light theme**: Currently using Cerulean; switch to dark theme (Darkly/Cyborg) with compatible colors.

## Implementation Plan

### File: `app1/app.R`

**1. Fix Plotly Reactivity (lines 140-188)**

- Wrap plot logic in a reactive expression that depends on both `people_df()` and `input$trait`
- Ensure `input$trait` has a default value even before trait_ui renders
- Fix data passing: verify `counts` dataframe structure is correct for plotly
- Add `event_data()` handling if needed
- Ensure plotly receives valid data even when trait_ui hasn't rendered yet

**2. Auto-fetch on Startup (lines 84-104)**

- Add `session$onFlushed()` or trigger fetch in `observe()` that runs once on startup
- Remove/hide the fetch button or make it optional (keep for refresh)
- Show loading state during initial fetch

**3. Fix Table Display (lines 123-138)**

- Add `autoWidth = TRUE` to DT options
- Adjust `scrollX` settings
- Consider `width = "100%"` in datatable options
- Ensure proper column width allocation

**4. Add Card Descriptions**

- **Card 1 (Data)**: Add text explaining the fetch button and trait selector
- **Card 2 (Table)**: Add text explaining the character data table
- **Card 3 (Plot)**: Add text explaining the frequency visualization

**5. Add Prominent Title**

- Add a `h1()` or `card_header()` at the top with app title
- Style it prominently above the cards

**6. Switch to Dark Theme**

- Change `bs_theme(bootswatch = "cerulean")` to `bs_theme(bootswatch = "darkly")` or `"cyborg"`
- Update `CERULEAN_PALETTE` to a dark-theme compatible palette (bright colors that work on dark backgrounds)
- Update plotly colors to use bright/neon colors suitable for dark backgrounds
- Ensure plotly `paper_bgcolor` and `plot_bgcolor` are transparent or match dark theme

### Color Palette for Dark Theme

- Use bright, saturated colors: blues, cyans, greens, purples, oranges
- Example palette: `c("#0D6EFD", "#20C997", "#FFC107", "#DC3545", "#6F42C1", "#17A2B8", "#FD7E14")`
- Or use plotly's built-in color scales like `"Set3"` or `"Pastel1"` that work on dark backgrounds

### Specific Code Changes

**Auto-fetch:**

```r
# In server function, add after people_df initialization:
observe({
  if (is.null(people_df())) {
    # Trigger fetch automatically
    withProgress(...)
  }
})
```

**Plotly fix:**

```r
# Make plot reactive to both data and trait selection
output$barplot <- renderPlotly({
  df <- people_df()
  trait <- input$trait %||% "gender"  # Default fallback
  # ... rest of plot code
})
```

**Table fix:**

```r
DT::datatable(
  ...,
  options = list(
    pageLength = 10,
    scrollX = TRUE,
    autoWidth = TRUE,
    dom = "Blfrtip"
  ),
  width = "100%"
)
```

**Dark theme:**

```r
theme = bs_theme(bootswatch = "darkly")
```

**Card descriptions:**
Add `p()` or `markdown()` blocks in each card explaining its purpose.

**Title:**
Add before `layout_columns`:

```r
h1("Star Wars Characters Dashboard", class = "text-center mb-4")
```

## Testing Checklist

- Plotly shows data when trait is selected
- Data loads automatically on app startup
- Table displays fully without cutoff
- All cards have descriptive text
- Prominent title is visible
- Dark theme is applied throughout
- Colors are visible and readable on dark background

