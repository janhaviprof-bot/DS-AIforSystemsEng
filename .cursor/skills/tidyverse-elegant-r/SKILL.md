---
name: tidyverse-elegant-r
description: >-
  Write elegant modern tidyverse R for this course repo—always = for assignment (never <-),
  dplyr 1.1+ (join_by, .by), native pipe, explicit library() per file, vectorized
  mutate/case_when, httr2 and purrr possibly/safely, rlang data-mask patterns.
  Use when editing 03_query_ai, 10_data_management, fixer, or refactoring API/data pipelines.
---

# Tidyverse-elegant R (SYSEN5381 / dsai)

Project rule: [.cursor/rules/tidyverse_elegant.mdc](../../rules/tidyverse_elegant.mdc). This skill adds links, package map, and patterns.

## Canonical links

- [Tidyverse style guide](https://style.tidyverse.org/) — [Syntax](https://style.tidyverse.org/syntax.html), [Pipes](https://style.tidyverse.org/pipes.html), [Functions](https://style.tidyverse.org/functions.html), [ggplot2](https://style.tidyverse.org/ggplot2.html)
- [Tidyverse packages](https://tidyverse.org/packages/)
- [Learning the tidyverse with AI](https://tidyverse.org/blog/2025/04/learn-tidyverse-ai/) — review pipelines step-by-step; remove unused packages and `print()` noise
- [Writing performant code with tidy tools](https://tidyverse.org/blog/2023/04/performant-packages/) — profile with **profvis**; compare with **bench::mark()**; dplyr-first until a hotspot is proven
- [Modern R Development Guide (gist)](https://gist.github.com/sj-io/3828d64d0969f2a0f05297e59e6c15ad) — join_by, .by, rlang, purrr 1.0+
- [httr2](https://httr2.r-lib.org/) — [req_error](https://httr2.r-lib.org/reference/req_error.html), [Wrapping APIs](https://httr2.r-lib.org/articles/wrapping-apis.html), [req_perform_iterative](https://httr2.r-lib.org/reference/req_perform_iterative.html)
- Formatting helpers: [styler](https://styler.r-lib.org/), [lintr](https://lintr.r-lib.org/)

## Package map (load only what you use)

| Package | Use for |
|---------|---------|
| dplyr | filter, mutate, summarise, joins, if_else, case_when, .by, join_by |
| tidyr | pivot_*, nest/unnest, separate_*, replace_na, complete |
| readr | read_csv, write_csv, read_lines, write_lines |
| tibble | tibble, as_tibble, tidy printing |
| purrr | map, walk, list_rbind, possibly, safely |
| stringr | str_*, vectorized strings in mutate |
| forcats | fct_* |
| lubridate | Dates and datetimes |
| ggplot2 | Graphics |
| httr2 | HTTP: request, req_*, resp_* |
| jsonlite | JSON with APIs |
| glue | Interpolation (when many pasted strings) |
| reprex | Minimal reproducible examples when debugging |

Avoid **`library(tidyverse)`** as a default; attach the rows you need.

## Modern dplyr patterns (gist-aligned)

```r
# Joins — join_by() and join quality
x |>
  dplyr::inner_join(y, dplyr::join_by(id == id), multiple = "error", unmatched = "error")

# Per-operation grouping — .by
x |>
  dplyr::summarise(m = mean(value), .by = c(grp, year))

# purrr 1.0+ — row-bind results
purrr::map(splits, fit_one) |> purrr::list_rbind()
```

## Vectorized vs scalar `if`

- **Column logic:** `dplyr::case_when()`, `if_else()`, `coalesce()`, `tidyr::replace_na()`, stringr inside `mutate()`.
- **Script flow:** `if (file.exists(".env")) readRenviron(".env")` is fine once at top.

## rlang snippets for function arguments

```r
my_mean = function(data, var) {
  data |> dplyr::summarise(m = mean({{ var }}, na.rm = TRUE))
}

my_mean_by_name = function(data, var) {
  data |> dplyr::summarise(m = mean(.data[[var]], na.rm = TRUE))
}
```

## httr2 + errors + mapped requests

- Single request: let **`req_perform()`** error, or tailor with **`req_error()`**.
- Many URLs: wrap a small function in **`purrr::possibly()`** / **`safely()`**, or use **`req_perform_iterative(..., on_error = "return")`** when appropriate.
- For typed handling of HTTP conditions, **`rlang::try_fetch`** on specific `httr2_http_*` classes can be clearer than a huge **`tryCatch`**.

## Performance workflow

1. Run **profvis** on realistic data.
2. Only optimize hot paths; use **bench::mark()** to compare; ensure equal outputs.
3. Prefer keeping **dplyr** in analysis scripts; consider **vctrs** / lower-level substitutes mainly for package internals or very tight loops ([performant-packages](https://tidyverse.org/blog/2023/04/performant-packages/)).

## Relation to tutorial `coding_style.mdc`

Tutorial rule prefers **`%>%`** and heavy commenting. Scoped elegant paths use **`|>`**, explicit **`library()`**, and vectorized table logic. Assignment is **always `=`** (never **`<-`**), same as [arrows.mdc](../../rules/arrows.mdc) and the tutorial rule.
