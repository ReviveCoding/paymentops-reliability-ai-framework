$ErrorActionPreference = "Stop"

Write-Host "Running full PaymentOps pipeline..."
python -m src.scripts.run_all

Write-Host "Running lightweight project tests..."
python -m src.scripts.run_tests

Write-Host "Running pytest..."
python -m pytest -q

Write-Host "All checks completed."
