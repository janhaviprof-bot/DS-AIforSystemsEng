# Dashboard functionality

## Overview

The app provides:

1. **Fetch** — Load all Star Wars people from SWAPI with one button click.
2. **Table** — Browse characters in a sortable, filterable DataTable (DT).
3. **Trait plot** — Choose a trait (gender, eye color, hair color, skin color, birth year) and see a Plotly bar chart of counts with hover labels (count and share %).

## Layout

- **bslib** page with Bootstrap **Cerulean** theme.
- **Responsive card layout** (works on mobile and desktop):
  - Card 1: Data controls (Fetch button, status, trait selector).
  - Card 2: Characters table (full-screen capable).
  - Card 3: Trait frequency plot (full-screen capable).

## Usage

1. Click **“Fetch characters from SWAPI”**. The app requests all paginated people from `https://swapi.dev/api/people/` and flattens results into a table.
2. Use the table filters and sorting (DT) to explore characters.
3. Select a **trait** in the dropdown; the bar plot updates to show frequency of each value, with sensible axis labels and hover text (value, count, percentage).

## Visual design

- **UI**: Cerulean theme (blues) via `bs_theme(bootswatch = "cerulean")`.
- **Plot**: Bar colors use a Cerulean-aligned palette (blues/teals) so charts match the dashboard.
