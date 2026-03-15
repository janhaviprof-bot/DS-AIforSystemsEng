#!/bin/bash
cd 04_deployment/positconnect/shinyr
Rscript -e "shiny::runApp('app.R', host='0.0.0.0', port=3838)"
