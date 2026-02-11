# SWAPI Star Wars Dashboard — Documentation

Shiny app that queries the [SWAPI (Star Wars API)](https://swapi.dev) for characters and presents results in a table and trait-frequency plot, with a bslib/Cerulean UI.

## Quick start

From the project root in R or RStudio:

```r
source("run.R")
```

Or from the shell: `Rscript run.R`

## Doc index

| Document | Description |
|----------|-------------|
| [FUNCTIONALITY.md](FUNCTIONALITY.md) | Dashboard features, layout, and usage |
| [SCHEMA.md](SCHEMA.md) | Table schema and column definitions |
| [API.md](API.md) | SWAPI endpoint details and usage |
| [DEPENDENCIES.md](DEPENDENCIES.md) | R package dependencies and install |
| [WORKFLOW.md](WORKFLOW.md) | Data and app workflows (Mermaid diagrams) |

## Project layout

```
.
├── run.R          # One-line launcher (loads Shiny, runs app)
├── app.R          # Shiny app (UI, server, SWAPI fetch, table, plot)
└── docs/
    ├── README.md
    ├── FUNCTIONALITY.md
    ├── SCHEMA.md
    ├── API.md
    ├── DEPENDENCIES.md
    └── WORKFLOW.md
```
