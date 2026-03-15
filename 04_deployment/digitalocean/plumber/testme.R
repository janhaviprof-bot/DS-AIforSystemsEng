setwd("C:/Users/tmf77/courses/SYSEN5381/dsai/04_deployment/digitalocean/plumber")
library(plumber)
plumb("plumber.R") %>% pr_run(port = 5762)