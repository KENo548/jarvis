<#
Windows setup script: installs Python deps and Node deps for MCP servers.
Run from repo root in PowerShell as an admin or developer shell.
#>

Write-Host "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Installing Node dependencies (package.json)..."
if (Test-Path -Path "package.json") {
    if (Test-Path -Path "node_modules") { Write-Host "node_modules exists — skipping npm ci" }
    else { npm ci }
}
else { Write-Host "No package.json found; skipping npm install" }

Write-Host "Installing Playwright browsers..."
python -m playwright install

Write-Host "Setup complete. Next: create secret files in ./secrets and start docker compose as needed."
