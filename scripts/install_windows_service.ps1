# PropShop IF - Windows Service Installer
# This script installs the trading bot as a Windows service using NSSM

param(
    [string]$ConfigPath = "configs\example_if_100k_profitmax.yaml",
    [string]$ServiceName = "PropShopTradingBot"
)

Write-Host "=" * 60
Write-Host "PropShop IF - Windows Service Installer"
Write-Host "=" * 60
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "[*] Project root: $ProjectRoot" -ForegroundColor Cyan

# Check if NSSM is installed
$nssmPath = "C:\ProgramData\chocolatey\bin\nssm.exe"

if (-not (Test-Path $nssmPath)) {
    Write-Host "[*] NSSM not found. Installing via Chocolatey..." -ForegroundColor Yellow

    # Check if Chocolatey is installed
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "[*] Installing Chocolatey..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }

    choco install nssm -y

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install NSSM" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[OK] NSSM found at: $nssmPath" -ForegroundColor Green

# Find Python executable
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $pythonPath) {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ and add to PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Python found at: $pythonPath" -ForegroundColor Green

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($existingService) {
    Write-Host "[WARN] Service '$ServiceName' already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove and reinstall? (y/n)"

    if ($response -eq "y") {
        Write-Host "[*] Stopping service..." -ForegroundColor Cyan
        & $nssmPath stop $ServiceName
        Start-Sleep -Seconds 2

        Write-Host "[*] Removing service..." -ForegroundColor Cyan
        & $nssmPath remove $ServiceName confirm
    } else {
        Write-Host "[*] Installation cancelled" -ForegroundColor Yellow
        exit 0
    }
}

# Install service
Write-Host "[*] Installing service '$ServiceName'..." -ForegroundColor Cyan

$arguments = "-m src.ui.cli trade --config $ConfigPath"
$appDirectory = $ProjectRoot
$stdoutLog = Join-Path $ProjectRoot "runs\logs\service_stdout.log"
$stderrLog = Join-Path $ProjectRoot "runs\logs\service_stderr.log"

# Create logs directory if it doesn't exist
$logsDir = Join-Path $ProjectRoot "runs\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

# Install the service
& $nssmPath install $ServiceName $pythonPath $arguments

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install service" -ForegroundColor Red
    exit 1
}

# Configure service
& $nssmPath set $ServiceName AppDirectory $appDirectory
& $nssmPath set $ServiceName AppStdout $stdoutLog
& $nssmPath set $ServiceName AppStderr $stderrLog
& $nssmPath set $ServiceName AppRotateFiles 1
& $nssmPath set $ServiceName AppRotateOnline 1
& $nssmm set $ServiceName AppRotateSeconds 86400  # Rotate daily
& $nssmm set $ServiceName AppRotateBytes 10485760  # 10MB max

# Set service to start automatically
& $nssmPath set $ServiceName Start SERVICE_AUTO_START

Write-Host "[OK] Service installed successfully" -ForegroundColor Green

# Start the service
Write-Host "[*] Starting service..." -ForegroundColor Cyan
& $nssmm start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Service started successfully" -ForegroundColor Green
} else {
    Write-Host "[WARN] Failed to start service. Check logs:" -ForegroundColor Yellow
    Write-Host "  stdout: $stdoutLog" -ForegroundColor Cyan
    Write-Host "  stderr: $stderrLog" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=" * 60
Write-Host "Installation Complete!"
Write-Host "=" * 60
Write-Host ""
Write-Host "Service Name: $ServiceName" -ForegroundColor Cyan
Write-Host "Status: " -NoNewline
& $nssmm status $ServiceName
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  Start service:   nssm start $ServiceName" -ForegroundColor Cyan
Write-Host "  Stop service:    nssm stop $ServiceName" -ForegroundColor Cyan
Write-Host "  Restart service: nssm restart $ServiceName" -ForegroundColor Cyan
Write-Host "  View status:     nssm status $ServiceName" -ForegroundColor Cyan
Write-Host "  Remove service:  nssm remove $ServiceName confirm" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logs:" -ForegroundColor Yellow
Write-Host "  stdout: $stdoutLog" -ForegroundColor Cyan
Write-Host "  stderr: $stderrLog" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dashboard: http://localhost:8000" -ForegroundColor Green
Write-Host ""
