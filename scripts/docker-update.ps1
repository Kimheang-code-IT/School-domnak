# Rebuild and restart the full Docker stack after code changes (frontend + backend).
# Same as deploy-docker.ps1; uses COMPOSE_PROJECT_NAME=schooldomnak for a stable project/volume name.
& "$PSScriptRoot\deploy-docker.ps1"
