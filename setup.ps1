# ═══════════════════════════════════════════════════════════
#  Teacher Bot — Windows PowerShell Setup Script
#  Run this ONCE to set up your environment.
#  Right-click PowerShell → "Run as Administrator" if needed.
# ═══════════════════════════════════════════════════════════

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Teacher Assistant Bot — Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ─────────────────────────────────
Write-Host "Step 1: Checking Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Download Python from https://python.org (check 'Add to PATH')" -ForegroundColor Red
    exit 1
}
$ver = python --version
Write-Host "  Found: $ver" -ForegroundColor Green

# ── Step 2: Create virtual environment ───────────────────
Write-Host ""
Write-Host "Step 2: Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  venv already exists, skipping." -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "  Created: venv/" -ForegroundColor Green
}

# ── Step 3: Activate venv ────────────────────────────────
Write-Host ""
Write-Host "Step 3: Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "  Activated." -ForegroundColor Green

# ── Step 4: Install packages ─────────────────────────────
Write-Host ""
Write-Host "Step 4: Installing packages (may take 1-2 minutes)..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt
Write-Host "  Packages installed." -ForegroundColor Green

# ── Step 5: Create local_uploads folder ──────────────────
Write-Host ""
Write-Host "Step 5: Creating local_uploads folder..." -ForegroundColor Yellow
if (-not (Test-Path "local_uploads")) {
    New-Item -ItemType Directory -Path "local_uploads" | Out-Null
}
Write-Host "  Done." -ForegroundColor Green

# ── Done ─────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Open .env file and fill in:"
Write-Host "       BOT_TOKEN  = your Telegram bot token"
Write-Host "       ADMIN_ID   = your Telegram user ID"
Write-Host ""
Write-Host "  2. Run the bot:"
Write-Host "       .\venv\Scripts\Activate.ps1"
Write-Host "       python bot.py"
Write-Host ""
