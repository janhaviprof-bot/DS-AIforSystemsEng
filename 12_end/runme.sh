#!/bin/bash
# runme.sh

# A single file in which to run all the activities in this module.
# Run from the root of the repository (dsai).
# Intended for instructor use or for students to do review.
# For best learning outcomes, be sure to review each folder individually and inspect the code.

# Run the data ingestion jobs
python 12_end/01_ingest_traffic.py
Rscript 12_end/01_ingest_traffic.R

# Run the model training jobs
python 12_end/02_train_model.py
Rscript 12_end/02_train_model.R

# Run the plumber api
Rscript 12_end/03_plumber/runme.R
Rscript 12_end/03_plumber/testme.R
Rscript 12_end/03_plumber/manifestme.R
Rscript 12_end/03_plumber/deployme.R

# Run the fastapi api
bash 12_end/03_fastapi/runme.sh
python 12_end/03_fastapi/testme.py
bash 12_end/03_fastapi/manifestme.sh
bash 12_end/03_fastapi/deployme.sh

# Run the agent query
Rscript 12_end/04_agent_query.R
python 12_end/04_agent_query.py


