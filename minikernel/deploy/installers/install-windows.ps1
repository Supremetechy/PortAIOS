# MiniKernel Windows Installation Script
# PowerShell script for Windows deployment

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "C:\Program Files\MiniKernel"
)

$ErrorActionPreference = "Stop"

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           MiniKernel Windows Installation                   ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Check pip
Write-Host "Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "✓ Found: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ pip not found" -ForegroundColor Red
    exit 1
}

# Create installation directory
Write-Host "Creating installation directory..." -ForegroundColor Yellow
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}
Write-Host "✓ Directory created: $InstallPath" -ForegroundColor Green

# Copy MiniKernel files
Write-Host "Installing MiniKernel files..." -ForegroundColor Yellow
if (Test-Path "minikernel") {
    Copy-Item -Path "minikernel" -Destination $InstallPath -Recurse -Force
    
    # Copy kernel audio files
    if (Test-Path "kernel\audio") {
        New-Item -ItemType Directory -Path "$InstallPath\kernel" -Force | Out-Null
        Copy-Item -Path "kernel\audio" -Destination "$InstallPath\kernel" -Recurse -Force
    }
    
    # Copy models
    if (Test-Path "models") {
        Copy-Item -Path "models" -Destination $InstallPath -Recurse -Force
    }
    
    Write-Host "✓ Files copied" -ForegroundColor Green
} else {
    Write-Host "✗ minikernel directory not found" -ForegroundColor Red
    Write-Host "Please run this script from the PortAIOS root directory" -ForegroundColor Yellow
    exit 1
}

# Create data directories
Write-Host "Creating data directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$InstallPath\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallPath\logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallPath\models" -Force | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Set-Location $InstallPath
pip install -r minikernel\requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create batch file wrapper
Write-Host "Creating command wrapper..." -ForegroundColor Yellow
$batchContent = @"
@echo off
cd /d "$InstallPath"
python minikernel\boot.py %*
"@
Set-Content -Path "C:\Windows\System32\minikernel.bat" -Value $batchContent
Write-Host "✓ Command wrapper created" -ForegroundColor Green

# Create Windows Service (optional)
Write-Host ""
Write-Host "Do you want to install MiniKernel as a Windows Service? (y/n)" -ForegroundColor Yellow
$response = Read-Host
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "Installing Windows Service..." -ForegroundColor Yellow
    
    # Create NSSM service wrapper (requires NSSM to be installed)
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        nssm install MiniKernel python "$InstallPath\minikernel\boot.py" --mode text
        nssm set MiniKernel AppDirectory $InstallPath
        nssm set MiniKernel DisplayName "MiniKernel - AI OS"
        nssm set MiniKernel Description "AI-First Voice-Controlled Operating System"
        nssm set MiniKernel Start SERVICE_AUTO_START
        
        Write-Host "✓ Service installed" -ForegroundColor Green
        Write-Host "  Start service: net start MiniKernel" -ForegroundColor Yellow
    } else {
        Write-Host "⚠ NSSM not found. Install from https://nssm.cc/ to create Windows Service" -ForegroundColor Yellow
    }
}

# Add to PATH
Write-Host ""
Write-Host "Adding to PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$InstallPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallPath", "Machine")
    Write-Host "✓ Added to PATH" -ForegroundColor Green
} else {
    Write-Host "✓ Already in PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ✓ MiniKernel Installation Complete!                 ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  Run MiniKernel:    " -NoNewline -ForegroundColor Yellow
Write-Host "minikernel --mode text" -ForegroundColor Green
Write-Host "  Installation path: " -NoNewline -ForegroundColor Yellow
Write-Host $InstallPath -ForegroundColor Green
Write-Host ""
Write-Host "Note: You may need to restart your terminal for PATH changes to take effect" -ForegroundColor Yellow
Write-Host ""
