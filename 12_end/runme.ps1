$ErrorActionPreference = "Stop"

# runme.ps1
#
# A single file in which to run all the activities in this module.
# Run from the root of the repository (dsai).
# Intended for instructor use or for students to do review.
# For best learning outcomes, be sure to review each folder individually and inspect the code.

function Run-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

# Run the data ingestion jobs
Run-Step -Command "python" -Arguments @("12_end/01_ingest_traffic.py")
Run-Step -Command "Rscript" -Arguments @("12_end/01_ingest_traffic.R")

# Run the model training jobs
Run-Step -Command "python" -Arguments @("12_end/02_train_model.py")
Run-Step -Command "Rscript" -Arguments @("12_end/02_train_model.R")

# Run the plumber api
Run-Step -Command "Rscript" -Arguments @("12_end/03_plumber/runme.R")
Run-Step -Command "Rscript" -Arguments @("12_end/03_plumber/testme.R")
Run-Step -Command "Rscript" -Arguments @("12_end/03_plumber/manifestme.R")
Run-Step -Command "Rscript" -Arguments @("12_end/03_plumber/deployme.R")

# Run the fastapi api
Run-Step -Command "bash" -Arguments @("12_end/03_fastapi/runme.sh")
Run-Step -Command "python" -Arguments @("12_end/03_fastapi/testme.py")
Run-Step -Command "bash" -Arguments @("12_end/03_fastapi/manifestme.sh")
Run-Step -Command "bash" -Arguments @("12_end/03_fastapi/deployme.sh")

# Run the agent query
Run-Step -Command "Rscript" -Arguments @("12_end/04_agent_query.R")
Run-Step -Command "python" -Arguments @("12_end/04_agent_query.py")
