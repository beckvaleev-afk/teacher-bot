# ═══════════════════════════════════════════════════════════
#  Teacher Bot — Run Script
#  Use this every time you want to start the bot.
# ═══════════════════════════════════════════════════════════

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Teacher Assistant Bot..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "ERROR: venv not found. Run setup.ps1 first!" -ForegroundColor Red
    exit 1
}

& ".\venv\Scripts\Activate.ps1"

# Check .env
$envContent = Get-Content ".env" -Raw
if ($envContent -match "PUT_YOUR_BOT_TOKEN_HERE") {
    Write-Host ""
    Write-Host "WARNING: BOT_TOKEN is not set in .env!" -ForegroundColor Red
    Write-Host "Open .env and replace PUT_YOUR_BOT_TOKEN_HERE with your token." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Get a token from @BotFather on Telegram:" -ForegroundColor Cyan
    Write-Host "  1. Open Telegram → search @BotFather"
    Write-Host "  2. Send /newbot"
    Write-Host "  3. Follow instructions → copy the token"
    Write-Host "  4. Paste it in .env as BOT_TOKEN=your_token_here"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting bot... (Press Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""
python bot.py
