# SWAPI Star Wars Characters Dashboard
# Queries swapi.dev, displays table and trait frequency plot (Plotly).
# UI: bslib + Bootstrap Darkly; responsive card layout.

library(shiny)
library(bslib)
library(httr)
library(jsonlite)
library(DT)
library(plotly)
library(dplyr)

# ---- API ----
SWAPI_BASE <- "https://swapi.dev/api"
# Dark theme compatible palette - bright colors for dark backgrounds
DARK_PALETTE <- c("#0D6EFD", "#20C997", "#FFC107", "#DC3545", "#6F42C1", "#17A2B8", "#FD7E14", "#E83E8C", "#6C757D")

fetch_people_page <- function(url) {
  r <- GET(url)
  if (http_error(r)) stop("SWAPI request failed.")
  content(r, as = "text", encoding = "UTF-8") |> fromJSON()
}

fetch_all_people <- function() {
  out <- list()
  url <- paste0(SWAPI_BASE, "/people/?format=json")
  while (!is.null(url)) {
    page <- fetch_people_page(url)
    out <- c(out, list(page$results))
    url <- page[["next"]]
  }
  bind_rows(out)
}

# Flatten to table: keep scalar fields; homeworld as URL for brevity
people_to_table <- function(people) {
  people %>%
    select(
      name, height, mass, hair_color, skin_color, eye_color,
      birth_year, gender, homeworld, url
    ) %>%
    mutate(
      height = as.numeric(height),
      mass = as.numeric(mass),
      across(c(hair_color, skin_color, eye_color, gender),
              ~ if_else(is.na(.) | . == "n/a", "unknown", as.character(.)))
    )
}

# ---- UI ----
ui <- page_fillable(
  theme = bs_theme(bootswatch = "darkly"),
  title = "Star Wars Characters — SWAPI Dashboard",
  padding = 20,
  h1("Star Wars Characters Dashboard", class = "text-center mb-4"),
  p("Explore Star Wars character data from the SWAPI (Star Wars API). Data loads automatically on startup.", 
    class = "text-center text-muted mb-4"),
  layout_columns(
    col_widths = c(12, 12),
    row_heights = "auto",
    # Card 1: Controls
    card(
      card_header("Data Controls"),
      p("Use the button below to refresh character data from SWAPI. Select a trait from the dropdown to visualize its frequency distribution across all characters."),
      fill = TRUE,
      layout_columns(
        col_widths = c(12, 12, 12),
        actionButton("fetch", "Refresh data from SWAPI", class = "btn-primary"),
        uiOutput("status"),
        uiOutput("trait_ui")
      )
    ),
    # Card 2: Table
    card(
      card_header("Characters Table"),
      p("Browse all Star Wars characters with their physical attributes, birth information, and homeworld. Use the filters at the top of each column to search and sort the data."),
      full_screen = TRUE,
      DT::dataTableOutput("table")
    ),
    # Card 3: Plot
    card(
      card_header("Trait Frequency Visualization"),
      p("This interactive bar chart shows the frequency distribution of the selected trait across all characters. Hover over bars to see detailed counts and percentages."),
      full_screen = TRUE,
      plotlyOutput("barplot", height = "400px")
    )
  )
)

# ---- Server ----
server <- function(input, output, session) {
  people_df <- reactiveVal(NULL)
  
  # Fetch function
  fetch_data <- function() {
    withProgress(message = "Fetching from SWAPI…", value = 0, {
      tryCatch({
        people <- fetch_all_people()
        tbl <- people_to_table(people)
        people_df(tbl)
        output$status <- renderUI({
          div(class = "text-success", strong(nrow(tbl)), " characters loaded.")
        })
      }, error = function(e) {
        people_df(NULL)
        output$status <- renderUI({
          div(class = "text-danger", "Error: ", conditionMessage(e))
        })
      })
    })
  }
  
  # Auto-fetch on startup
  observe({
    if (is.null(people_df())) {
      fetch_data()
    }
  })
  
  # Manual refresh button
  observeEvent(input$fetch, {
    fetch_data()
  })

  output$trait_ui <- renderUI({
    if (is.null(people_df())) {
      # Show default trait selector even before data loads
      trait_opts <- c(
        "gender" = "Gender",
        "eye_color" = "Eye color",
        "hair_color" = "Hair color",
        "skin_color" = "Skin color",
        "birth_year" = "Birth year (BBY/ABY)"
      )
      return(selectInput(
        "trait",
        "Trait for frequency plot",
        choices = trait_opts,
        selected = "gender"
      ))
    }
    trait_opts <- c(
      "gender" = "Gender",
      "eye_color" = "Eye color",
      "hair_color" = "Hair color",
      "skin_color" = "Skin color",
      "birth_year" = "Birth year (BBY/ABY)"
    )
    selectInput(
      "trait",
      "Trait for frequency plot",
      choices = trait_opts,
      selected = "gender"
    )
  })

  output$table <- DT::renderDataTable({
    df <- people_df()
    if (is.null(df) || nrow(df) == 0) return(NULL)
    df %>%
      rename(
        Name = name, Height_cm = height, Mass_kg = mass,
        `Hair color` = hair_color, `Skin color` = skin_color,
        `Eye color` = eye_color, `Birth year` = birth_year,
        Gender = gender, Homeworld = homeworld, URL = url
      ) %>%
      DT::datatable(
        filter = "top",
        options = list(
          pageLength = 10,
          scrollX = TRUE,
          autoWidth = TRUE,
          dom = "Blfrtip",
          columnDefs = list(list(width = "150px", targets = c(0, 1, 2)))
        ),
        width = "100%",
        rownames = FALSE
      )
  })

  output$barplot <- renderPlotly({
    df <- people_df()
    # Default to "gender" if trait not yet selected
    trait <- if (is.null(input$trait)) "gender" else input$trait
    
    if (is.null(df) || nrow(df) == 0) {
      return(plot_ly() %>%
        add_annotations(
          text = "No data available. Please wait for data to load.",
          x = 0.5, y = 0.5,
          xref = "paper", yref = "paper",
          showarrow = FALSE,
          font = list(size = 16)
        ) %>%
        layout(
          paper_bgcolor = "rgba(0,0,0,0)",
          plot_bgcolor = "rgba(0,0,0,0)",
          xaxis = list(showgrid = FALSE, showticklabels = FALSE),
          yaxis = list(showgrid = FALSE, showticklabels = FALSE)
        ))
    }

    # Ensure trait is valid
    if (!trait %in% c("gender", "eye_color", "hair_color", "skin_color", "birth_year")) {
      trait <- "gender"
    }

    counts <- df %>%
      mutate(value = coalesce(as.character(!!sym(trait)), "unknown")) %>%
      count(value, name = "count", sort = TRUE) %>%
      mutate(pct = round(100 * count / sum(count), 1))

    if (nrow(counts) == 0) {
      return(plot_ly() %>%
        add_annotations(
          text = "No data available for this trait.",
          x = 0.5, y = 0.5,
          xref = "paper", yref = "paper",
          showarrow = FALSE,
          font = list(size = 16)
        ) %>%
        layout(
          paper_bgcolor = "rgba(0,0,0,0)",
          plot_bgcolor = "rgba(0,0,0,0)",
          xaxis = list(showgrid = FALSE, showticklabels = FALSE),
          yaxis = list(showgrid = FALSE, showticklabels = FALSE)
        ))
    }

    trait_title <- switch(trait,
      gender = "Gender",
      eye_color = "Eye color",
      hair_color = "Hair color",
      skin_color = "Skin color",
      birth_year = "Birth year",
      trait
    )

    # Use dark theme compatible colors
    pal <- rep(DARK_PALETTE, length.out = nrow(counts))

    p <- plot_ly(
      counts,
      x = ~value,
      y = ~count,
      type = "bar",
      marker = list(
        color = pal,
        line = list(color = "rgba(255,255,255,0.1)", width = 1)
      ),
      text = ~paste0(value, "<br>Count: ", count, "<br>Share: ", pct, "%"),
      hoverinfo = "text",
      hovertemplate = "%{text}<extra></extra>"
    ) %>%
      layout(
        xaxis = list(
          title = list(text = trait_title, font = list(color = "#fff")),
          categoryorder = "total descending",
          tickangle = -45,
          tickfont = list(color = "#fff"),
          gridcolor = "rgba(255,255,255,0.1)"
        ),
        yaxis = list(
          title = list(text = "Number of characters", font = list(color = "#fff")),
          tickfont = list(color = "#fff"),
          gridcolor = "rgba(255,255,255,0.1)"
        ),
        title = list(
          text = paste0("Frequency by ", trait_title),
          font = list(size = 16, color = "#fff")
        ),
        margin = list(b = 100, t = 60),
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor = "rgba(0,0,0,0)",
        font = list(color = "#fff")
      ) %>%
      config(displayModeBar = TRUE, displaylogo = FALSE)

    p
  })
}

shinyApp(ui, server)
