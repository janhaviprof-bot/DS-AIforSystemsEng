# Package dependencies

## Required R packages

| Package | Purpose |
|---------|---------|
| **shiny** | App framework and server. |
| **bslib** | Bootstrap/bslib theming (Cerulean). |
| **httr** | HTTP GET for SWAPI. |
| **jsonlite** | Parse JSON responses. |
| **DT** | Interactive DataTables in the UI. |
| **plotly** | Interactive bar plot. |
| **dplyr** | Data manipulation (e.g. `bind_rows`, `count`, `mutate`). |

## Installation

From R:

```r
pkgs <- c("shiny", "bslib", "httr", "jsonlite", "DT", "plotly", "dplyr")
install.packages(pkgs, repos = "https://cloud.r-project.org")
```

Or install individually; `run.R` only ensures `shiny` is present. Install the rest before first run if needed.

## Versions

The app is written for current CRAN versions of these packages. No minimum version is enforced in code; typical recent R (e.g. ≥ 4.0) is assumed.
