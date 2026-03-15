# app.R
# Supabase-authenticated Shiny for R app
# Tim Fraser
#
# This app demonstrates Supabase email/password authentication to protect app content.
# Users must sign up or sign in with Supabase before accessing the restaurant tipping dashboard.

library(shiny)
library(httr2)
library(jsonlite)
library(readr)
library(dplyr)
library(DT)
library(bslib)

# Supabase configuration
# Get credentials from environment variables
SUPABASE_URL <- Sys.getenv("SUPABASE_URL", "")
SUPABASE_PUBLIC_KEY <- Sys.getenv("SUPABASE_PUBLIC_KEY", "")

# Load data
tips <- read_csv("data/tips.csv", show_col_types = FALSE)
bill_rng <- c(min(tips$total_bill), max(tips$total_bill))

# Supabase authentication functions
normalize_auth_payload = function(data) {
  # Normalize auth payload across REST and SDK-like response shapes.
  user = data$user
  if (is.null(user)) { user = list() }

  session = data$session
  # Raw GoTrue REST responses return tokens at top level.
  if (is.null(session) && !is.null(data$access_token)) {
    session = list(
      access_token = data$access_token,
      refresh_token = data$refresh_token,
      expires_in = data$expires_in
    )
  }

  list(user = user, session = session)
}

sign_up <- function(email, password) {
  # Create a new user account in Supabase
  tryCatch({
    response <- request(paste0(SUPABASE_URL, "/auth/v1/signup")) %>%
      req_headers(
        "apikey" = SUPABASE_PUBLIC_KEY,
        "Content-Type" = "application/json"
      ) %>%
      req_error(is_error = function(resp) FALSE) %>%
      req_body_json(list(email = email, password = password)) %>%
      req_perform()
    
    # Supabase signup can return 200 OK or 201 Created
    if (resp_status(response) %in% c(200, 201)) {
      tryCatch({
        data <- resp_body_json(response)
        normalized = normalize_auth_payload(data)
        list(success = TRUE, user = normalized$user, session = normalized$session)
      }, error = function(e) {
        list(success = FALSE, error = "Invalid response format from server")
      })
    } else {
      # Handle error response
      tryCatch({
        error_data <- resp_body_json(response)
        # Check multiple possible error field names
        error_msg <- if (!is.null(error_data$error_description)) {
          error_data$error_description
        } else if (!is.null(error_data$message)) {
          error_data$message
        } else if (!is.null(error_data$error)) {
          error_data$error
        } else {
          paste0("Signup failed (status ", resp_status(response), ")")
        }
        list(success = FALSE, error = error_msg)
      }, error = function(e) {
        # Non-JSON error response
        error_text <- tryCatch(resp_body_string(response), error = function(e) "Unknown error")
        error_msg <- paste0("Signup failed (status ", resp_status(response), "): ", substr(error_text, 1, 200))
        list(success = FALSE, error = error_msg)
      })
    }
  }, error = function(e) {
    list(success = FALSE, error = conditionMessage(e))
  })
}

sign_in <- function(email, password) {
  # Authenticate user with email/password via Supabase
  tryCatch({
    response <- request(paste0(SUPABASE_URL, "/auth/v1/token?grant_type=password")) %>%
      req_headers(
        "apikey" = SUPABASE_PUBLIC_KEY,
        "Content-Type" = "application/json"
      ) %>%
      req_error(is_error = function(resp) FALSE) %>%
      req_body_json(list(email = email, password = password)) %>%
      req_perform()
    
    if (resp_status(response) == 200) {
      tryCatch({
        data <- resp_body_json(response)
        normalized = normalize_auth_payload(data)
        list(success = TRUE, user = normalized$user, session = normalized$session)
      }, error = function(e) {
        list(success = FALSE, error = "Invalid response format from server")
      })
    } else {
      # Handle error response
      tryCatch({
        error_data <- resp_body_json(response)
        # Check multiple possible error field names
        error_msg <- if (!is.null(error_data$error_description)) {
          error_data$error_description
        } else if (!is.null(error_data$message)) {
          error_data$message
        } else if (!is.null(error_data$error)) {
          error_data$error
        } else {
          paste0("Login failed (status ", resp_status(response), ")")
        }
        list(success = FALSE, error = error_msg)
      }, error = function(e) {
        # Non-JSON error response
        error_text <- tryCatch(resp_body_string(response), error = function(e) "Unknown error")
        error_msg <- paste0("Login failed (status ", resp_status(response), "): ", substr(error_text, 1, 200))
        list(success = FALSE, error = error_msg)
      })
    }
  }, error = function(e) {
    list(success = FALSE, error = conditionMessage(e))
  })
}

refresh_session <- function(refresh_token_value) {
  # Refresh access token with a Supabase refresh token.
  tryCatch({
    response <- request(paste0(SUPABASE_URL, "/auth/v1/token?grant_type=refresh_token")) %>%
      req_headers(
        "apikey" = SUPABASE_PUBLIC_KEY,
        "Content-Type" = "application/json"
      ) %>%
      req_error(is_error = function(resp) FALSE) %>%
      req_body_json(list(refresh_token = refresh_token_value)) %>%
      req_perform()

    if (resp_status(response) == 200) {
      data = resp_body_json(response)
      normalized = normalize_auth_payload(data)
      list(success = TRUE, user = normalized$user, session = normalized$session)
    } else {
      tryCatch({
        error_data = resp_body_json(response)
        error_msg = if (!is.null(error_data$error_description)) {
          error_data$error_description
        } else if (!is.null(error_data$message)) {
          error_data$message
        } else if (!is.null(error_data$error)) {
          error_data$error
        } else {
          paste0("Token refresh failed (status ", resp_status(response), ")")
        }
        list(success = FALSE, error = error_msg)
      }, error = function(e) {
        error_text = tryCatch(resp_body_string(response), error = function(e) "Unknown error")
        error_msg = paste0("Token refresh failed (status ", resp_status(response), "): ", substr(error_text, 1, 200))
        list(success = FALSE, error = error_msg)
      })
    }
  }, error = function(e) {
    list(success = FALSE, error = conditionMessage(e))
  })
}

remote_sign_out <- function(access_token_value) {
  # Best-effort remote logout; local logout still proceeds on failure.
  if (is.null(access_token_value) || identical(access_token_value, "")) { return(invisible(NULL)) }
  tryCatch({
    request(paste0(SUPABASE_URL, "/auth/v1/logout")) %>%
      req_headers(
        "apikey" = SUPABASE_PUBLIC_KEY,
        "Authorization" = paste("Bearer", access_token_value)
      ) %>%
      req_error(is_error = function(resp) FALSE) %>%
      req_perform()
    invisible(NULL)
  }, error = function(e) {
    invisible(NULL)
  })
}

sign_out <- function() {
  # Sign out user (state is cleared in the server observer).
}

# UI
ui <- fluidPage(
  titlePanel("Restaurant tipping"),
  
  sidebarLayout(
    sidebarPanel(
      conditionalPanel(
        condition = "!output.auth_ok",
        h5("Sign In or Sign Up"),
        textInput("auth_email", "Email", ""),
        passwordInput("auth_password", "Password", ""),
        actionButton("sign_in_btn", "Sign In", class = "btn-primary"),
        actionButton("sign_up_btn", "Sign Up", class = "btn-secondary"),
        hr(),
        uiOutput("auth_message")
      ),
      conditionalPanel(
        condition = "output.auth_ok",
        h5("Logged in as:"),
        textOutput("user_email"),
        actionButton("sign_out_btn", "Sign Out", class = "btn-warning"),
        hr(),
        sliderInput(
          "total_bill",
          "Bill amount",
          min = bill_rng[1],
          max = bill_rng[2],
          value = bill_rng,
          pre = "$"
        ),
        checkboxGroupInput(
          "time",
          "Food service",
          choices = c("Lunch", "Dinner"),
          selected = c("Lunch", "Dinner"),
          inline = TRUE
        ),
        actionButton("reset", "Reset filter")
      )
    ),
    
    mainPanel(
      fluidRow(
        column(4,
          valueBoxOutput("total_tippers", width = NULL)
        ),
        column(4,
          valueBoxOutput("average_tip", width = NULL)
        ),
        column(4,
          valueBoxOutput("average_bill", width = NULL)
        )
      ),
      br(),
      card(
        card_header("Tips data"),
        DT::dataTableOutput("table")
      )
    )
  )
)

# Server
server <- function(input, output, session) {
  
  # Reactive authentication state
  auth_ok <- reactiveVal(FALSE)
  user_email <- reactiveVal("")
  session_token <- reactiveVal("")
  refresh_token <- reactiveVal("")
  token_expires_at <- reactiveVal(0)
  
  # Authentication status for conditionalPanel
  output$auth_ok <- reactive(auth_ok())
  outputOptions(output, "auth_ok", suspendWhenHidden = FALSE)
  
  # User email display
  output$user_email <- renderText({
    user_email()
  })
  
  # Auth message
  output$auth_message <- renderUI({
    if (SUPABASE_URL == "" || SUPABASE_PUBLIC_KEY == "") {
      tags$p(
        "⚠️ Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
        class = "text-warning"
      )
    } else {
      tags$p("")
    }
  })
  
  # Sign in handler
  observeEvent(input$sign_in_btn, {
    if (SUPABASE_URL == "" || SUPABASE_PUBLIC_KEY == "") {
      showNotification(
        "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
        type = "error",
        duration = 5
      )
      return()
    }
    
    email <- input$auth_email
    password <- input$auth_password
    
    if (email == "" || password == "") {
      showNotification("Please enter both email and password", type = "error", duration = 3)
      return()
    }
    
    result <- sign_in(email, password)
    
    if (result$success) {
      auth_ok(TRUE)
      user_email(if (!is.null(result$user$email)) result$user$email else email)
      if (!is.null(result$session)) {
        session_token(if (!is.null(result$session$access_token)) result$session$access_token else "")
        refresh_token(if (!is.null(result$session$refresh_token)) result$session$refresh_token else "")
        expires_in = if (!is.null(result$session$expires_in)) result$session$expires_in else 0
        token_expires_at(as.numeric(Sys.time()) + max(0, as.numeric(expires_in) - 30))
      }
      showNotification("Signed in successfully!", type = "message", duration = 3)
    } else {
      showNotification(paste("Sign in failed:", result$error), type = "error", duration = 5)
    }
  })
  
  # Sign up handler
  observeEvent(input$sign_up_btn, {
    if (SUPABASE_URL == "" || SUPABASE_PUBLIC_KEY == "") {
      showNotification(
        "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_PUBLIC_KEY environment variables.",
        type = "error",
        duration = 5
      )
      return()
    }
    
    email <- input$auth_email
    password <- input$auth_password
    
    if (email == "" || password == "") {
      showNotification("Please enter both email and password", type = "error", duration = 3)
      return()
    }
    
    result <- sign_up(email, password)
    
    if (result$success) {
      showNotification("Account created! Please sign in.", type = "message", duration = 3)
    } else {
      showNotification(paste("Sign up failed:", result$error), type = "error", duration = 5)
    }
  })
  
  # Sign out handler
  observeEvent(input$sign_out_btn, {
    remote_sign_out(session_token())
    sign_out()
    auth_ok(FALSE)
    user_email("")
    session_token("")
    refresh_token("")
    token_expires_at(0)
    showNotification("Signed out successfully", type = "message", duration = 2)
  })

  # Refresh token periodically for longer sessions.
  observe({
    invalidateLater(60000, session)
    if (!auth_ok()) { return() }

    expires_at = token_expires_at()
    if (is.null(expires_at) || expires_at <= 0 || (expires_at - as.numeric(Sys.time())) > 90) { return() }

    current_refresh_token = refresh_token()
    if (is.null(current_refresh_token) || identical(current_refresh_token, "")) { return() }

    result = refresh_session(current_refresh_token)
    if (isTRUE(result$success) && !is.null(result$session)) {
      session_token(if (!is.null(result$session$access_token)) result$session$access_token else "")
      refresh_token(if (!is.null(result$session$refresh_token)) result$session$refresh_token else current_refresh_token)
      expires_in = if (!is.null(result$session$expires_in)) result$session$expires_in else 0
      token_expires_at(as.numeric(Sys.time()) + max(0, as.numeric(expires_in) - 30))
    } else {
      auth_ok(FALSE)
      user_email("")
      session_token("")
      refresh_token("")
      token_expires_at(0)
      showNotification("Session expired. Please sign in again.", type = "warning", duration = 5)
    }
  })
  
  # Filtered tips data
  tips_data <- reactive({
    if (!auth_ok()) {
      return(data.frame())
    }
    bill <- input$total_bill
    tips %>%
      filter(total_bill >= bill[1] & total_bill <= bill[2]) %>%
      filter(time %in% input$time)
  })
  
  # Value boxes
  output$total_tippers <- renderValueBox({
    if (!auth_ok()) {
      valueBox("—", "Total tippers", icon = icon("user"))
    } else {
      valueBox(
        nrow(tips_data()),
        "Total tippers",
        icon = icon("user")
      )
    }
  })
  
  output$average_tip <- renderValueBox({
    if (!auth_ok()) {
      valueBox("—", "Average tip", icon = icon("wallet"))
    } else {
      dat <- tips_data()
      if (nrow(dat) > 0) {
        perc <- mean(dat$tip / dat$total_bill)
        valueBox(
          paste0(round(perc * 100, 1), "%"),
          "Average tip",
          icon = icon("wallet")
        )
      } else {
        valueBox("—", "Average tip", icon = icon("wallet"))
      }
    }
  })
  
  output$average_bill <- renderValueBox({
    if (!auth_ok()) {
      valueBox("—", "Average bill", icon = icon("dollar-sign"))
    } else {
      dat <- tips_data()
      if (nrow(dat) > 0) {
        bill <- mean(dat$total_bill)
        valueBox(
          paste0("$", round(bill, 2)),
          "Average bill",
          icon = icon("dollar-sign")
        )
      } else {
        valueBox("—", "Average bill", icon = icon("dollar-sign"))
      }
    }
  })
  
  # Data table
  output$table <- DT::renderDataTable({
    if (!auth_ok()) {
      return(data.frame())
    }
    tips_data()
  })
  
  # Reset handler
  observeEvent(input$reset, {
    updateSliderInput(session, "total_bill", value = bill_rng)
    updateCheckboxGroupInput(session, "time", selected = c("Lunch", "Dinner"))
  })
}

shinyApp(ui = ui, server = server)
