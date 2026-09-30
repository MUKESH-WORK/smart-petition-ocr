# ==============================================================================
# GDP Assistant - Fresh Server Host and Ollama Bootstrap Script (Windows)
# ==============================================================================
# Automates host pre-flight verification, Ollama installation, daemon startup,
# AI model downloading (qwen2.5:3b-instruct), Redis installation,
# Sentence Transformer model caching, environment setup, and Docker Compose deployment.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup_host.ps1
# ==============================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

function Log-Info {
    param([string]$Msg)
    Write-Host "[INFO] $Msg" -ForegroundColor Cyan
}

function Log-Ok {
    param([string]$Msg)
    Write-Host "[OK] $Msg" -ForegroundColor Green
}

function Log-Warn {
    param([string]$Msg)
    Write-Host "[WARNING] $Msg" -ForegroundColor Yellow
}

function Log-Err {
    param([string]$Msg)
    Write-Host "[ERROR] $Msg" -ForegroundColor Red
}

function Update-SessionPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"

    $localOllama = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
    if ((Test-Path $localOllama) -and ($env:Path -notlike "*$localOllama*")) {
        $env:Path = "$localOllama;$env:Path"
    }
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor White
Write-Host "   GDP Assistant - Fresh Server Deployment and Host Bootstrap Engine" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor White
Write-Host ""

# ------------------------------------------------------------------------------
# STEP 1: Verify Docker and Docker Compose
# ------------------------------------------------------------------------------
Log-Info "Step 1/10: Verifying Docker and Docker Compose availability..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Log-Err "Docker is not installed or not available in PATH."
    Log-Err "Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop"
    Log-Err "Ensure WSL 2 based engine is enabled in Docker Desktop settings, then rerun this script."
    exit 1
}

try {
    $dockerVer = docker --version
    Log-Ok "Docker CLI found: $dockerVer"
} catch {
    Log-Err "Failed to execute docker --version. Ensure Docker CLI is accessible."
    exit 1
}

# Verify Docker daemon is responsive
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker daemon returned exit code $LASTEXITCODE"
    }
    Log-Ok "Docker Engine daemon is active and responsive."
} catch {
    Log-Err "Docker Engine is not running."
    Log-Err "Please start Docker Desktop on this PC and wait until the engine is fully running, then rerun this script."
    exit 1
}

# Check docker compose plugin
try {
    $composeVer = docker compose version
    Log-Ok "Docker Compose found: $composeVer"
} catch {
    Log-Err "Docker Compose v2 plugin is missing. Please update Docker Desktop."
    exit 1
}

# ------------------------------------------------------------------------------
# STEP 2: Check / Install Ollama on Host
# ------------------------------------------------------------------------------
Log-Info "Step 2/10: Checking host Ollama installation..."
Update-SessionPath

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue

if ($ollamaCmd) {
    $ollamaVer = ollama --version
    Log-Ok "Ollama is already installed on host: $ollamaVer"
} else {
    Log-Info "Ollama CLI was not found. Attempting automated installation via winget..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Log-Err "Windows Package Manager (winget) is not available on this system."
        Log-Err "Please download and install Ollama manually from: https://ollama.com/download/windows"
        Log-Err "After installation completes, rerun this script."
        exit 1
    }

    try {
        Log-Info "Running: winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements --silent"
        $installProc = Start-Process winget -ArgumentList "install Ollama.Ollama --accept-source-agreements --accept-package-agreements --silent" -NoNewWindow -PassThru -Wait
        
        Update-SessionPath
        Start-Sleep -Seconds 3

        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaCmd) {
            $localOllamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
            if (Test-Path $localOllamaExe) {
                $ollamaDir = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
                $env:Path = "$ollamaDir;$env:Path"
            }
        }

        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaCmd) {
            throw "Ollama executable not found in PATH after winget installation."
        }

        $ollamaVer = ollama --version
        Log-Ok "Ollama successfully installed: $ollamaVer"
    } catch {
        Log-Err "Automated Ollama installation failed: $_"
        Log-Err "Please manually download and install Ollama from: https://ollama.com/download/windows"
        exit 1
    }
}

# ------------------------------------------------------------------------------
# STEP 3: Check / Start Ollama Server Daemon
# ------------------------------------------------------------------------------
Log-Info "Step 3/10: Verifying host Ollama server daemon (http://127.0.0.1:11434)..."

function Test-OllamaHealth {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

$isOllamaRunning = Test-OllamaHealth

if ($isOllamaRunning) {
    Log-Ok "Host Ollama server daemon is active and responding."
} else {
    Log-Info "Host Ollama server is not running. Launching 'ollama serve' in background..."
    try {
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    } catch {
        Log-Err "Failed to launch 'ollama serve' process: $_"
        exit 1
    }

    Log-Info "Waiting for Ollama daemon to become ready on http://127.0.0.1:11434 (timeout 60s)..."
    $maxOllamaWaitSec = 60
    $waitedSec = 0
    $ready = $false

    while ($waitedSec -lt $maxOllamaWaitSec) {
        Start-Sleep -Seconds 2
        $waitedSec += 2
        if (Test-OllamaHealth) {
            $ready = $true
            break
        }
        Write-Host -NoNewline "."
    }
    Write-Host ""

    if (-not $ready) {
        Log-Err "Host Ollama server did not respond on http://127.0.0.1:11434 within $maxOllamaWaitSec seconds."
        Log-Err "Please start the Ollama application from the Start Menu, then rerun this script."
        exit 1
    }

    Log-Ok "Host Ollama server started and verified."
}

# ------------------------------------------------------------------------------
# STEP 4: Check / Pull Required Ollama Model (qwen2.5:3b-instruct)
# ------------------------------------------------------------------------------
Log-Info "Step 4/10: Checking required LLM model (qwen2.5:3b-instruct)..."
$targetModel = "qwen2.5:3b-instruct"

$hasModel = $false
try {
    $tagsResp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 5
    if ($tagsResp -and $tagsResp.models) {
        foreach ($m in $tagsResp.models) {
            if ($m.name -like "*qwen2.5:3b-instruct*" -or $m.model -like "*qwen2.5:3b-instruct*") {
                $hasModel = $true
                break
            }
        }
    }
} catch {
    Log-Warn "REST tag inspection failed; checking via ollama list CLI..."
    try {
        $listOutput = (ollama list 2>&1 | Out-String)
        if ($listOutput -match "qwen2.5:3b-instruct") {
            $hasModel = $true
        }
    } catch {}
}

if ($hasModel) {
    Log-Ok "Required Ollama model '$targetModel' is already installed."
} else {
    Log-Info "Model '$targetModel' is missing. Downloading via 'ollama pull $targetModel' (~1.9 GB)..."
    try {
        $pullProcess = Start-Process ollama -ArgumentList "pull $targetModel" -NoNewWindow -PassThru -Wait
        if ($pullProcess.ExitCode -ne 0) {
            throw "Ollama pull command exited with code $($pullProcess.ExitCode)"
        }
        Log-Ok "Model '$targetModel' successfully downloaded and verified."
    } catch {
        Log-Err "Failed to pull Ollama model '$targetModel': $_"
        Log-Err "Please run 'ollama pull qwen2.5:3b-instruct' manually, then rerun this script."
        exit 1
    }
}

# ------------------------------------------------------------------------------
# STEP 5: Check / Install Redis on Host
# ------------------------------------------------------------------------------
Log-Info "Step 5/10: Checking Redis availability on host..."

$redisCmd = Get-Command redis-server -ErrorAction SilentlyContinue
$redisCliCmd = Get-Command redis-cli -ErrorAction SilentlyContinue

if ($redisCmd) {
    try {
        $redisVer = (redis-server --version 2>&1 | Out-String).Trim()
        Log-Ok "Redis is already installed on host: $redisVer"
    } catch {
        Log-Ok "Redis server binary found at: $($redisCmd.Source)"
    }
} else {
    Log-Info "Redis is not installed on the host. Attempting installation via winget..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Log-Warn "winget is not available. Trying Chocolatey..."

        if (Get-Command choco -ErrorAction SilentlyContinue) {
            try {
                Log-Info "Running: choco install redis-64 -y"
                $chocoProc = Start-Process choco -ArgumentList "install redis-64 -y" -NoNewWindow -PassThru -Wait
                Update-SessionPath
                $redisCmd = Get-Command redis-server -ErrorAction SilentlyContinue
                if ($redisCmd) {
                    Log-Ok "Redis installed successfully via Chocolatey."
                } else {
                    throw "Redis not found after Chocolatey install."
                }
            } catch {
                Log-Warn "Chocolatey Redis installation failed: $_"
            }
        }
    } else {
        try {
            Log-Info "Running: winget install Redis.Redis --accept-source-agreements --accept-package-agreements --silent"
            $redisInstall = Start-Process winget -ArgumentList "install Redis.Redis --accept-source-agreements --accept-package-agreements --silent" -NoNewWindow -PassThru -Wait

            Update-SessionPath
            Start-Sleep -Seconds 3

            $redisCmd = Get-Command redis-server -ErrorAction SilentlyContinue
            if ($redisCmd) {
                Log-Ok "Redis installed successfully via winget."
            } else {
                # Check common install paths
                $commonRedisPaths = @(
                    "C:\Program Files\Redis",
                    "$env:LOCALAPPDATA\Redis",
                    "$env:ProgramFiles\Redis"
                )
                foreach ($rp in $commonRedisPaths) {
                    if (Test-Path (Join-Path $rp "redis-server.exe")) {
                        $env:Path = "$rp;$env:Path"
                        Log-Info "Added Redis to PATH from: $rp"
                        break
                    }
                }
                $redisCmd = Get-Command redis-server -ErrorAction SilentlyContinue
            }
        } catch {
            Log-Warn "winget Redis installation encountered an issue: $_"
        }
    }

    # Final fallback: Docker-based Redis is bundled inside the all-in-one container
    if (-not $redisCmd) {
        Log-Warn "Could not install Redis as a standalone host service."
        Log-Info "Redis is already bundled INSIDE the GDP Assistant Docker container (via supervisord)."
        Log-Info "Host Redis is only needed for local development without Docker."
        Log-Ok "Proceeding with container-bundled Redis (no host install required for Docker deployment)."
    }
}

# Verify Redis connectivity if installed on host
if ($redisCmd) {
    $redisCliCmd = Get-Command redis-cli -ErrorAction SilentlyContinue
    if ($redisCliCmd) {
        try {
            $redisPing = (redis-cli ping 2>&1 | Out-String).Trim()
            if ($redisPing -eq "PONG") {
                Log-Ok "Host Redis server is running and responding to PING."
            } else {
                Log-Info "Host Redis server is installed but not currently running (will be started inside Docker container)."
            }
        } catch {
            Log-Info "Host Redis server is installed but not currently running."
        }
    }
}

# ------------------------------------------------------------------------------
# STEP 6: Pre-download Sentence Transformer Model for Docker Image
# ------------------------------------------------------------------------------
Log-Info "Step 6/10: Pre-downloading Sentence Transformer model for offline Docker builds..."

$rootDir = $PSScriptRoot
$modelDir = Join-Path $rootDir "models"
$stModelDir = Join-Path $modelDir "all-MiniLM-L6-v2"
$stModelConfig = Join-Path $stModelDir "config.json"

if (Test-Path $stModelConfig) {
    Log-Ok "Sentence Transformer model 'all-MiniLM-L6-v2' is already saved in '$modelDir'."
} else {
    Log-Info "Saving Sentence Transformer model 'all-MiniLM-L6-v2' to '$modelDir' for Docker image baking..."

    # Create model directory
    if (-not (Test-Path $modelDir)) {
        New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
    }

    # Locate a usable Python interpreter with sentence-transformers
    $pythonExe = $null

    # Check 1: Project venv
    $venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $pythonExe = $venvPython
    }

    # Check 2: System Python
    if (-not $pythonExe) {
        $sysPython = Get-Command python -ErrorAction SilentlyContinue
        if ($sysPython) {
            $pythonExe = $sysPython.Source
        }
    }

    if (-not $pythonExe) {
        Log-Err "No Python interpreter found. Cannot pre-download Sentence Transformer model."
        Log-Err "Install Python 3.11+ and sentence-transformers, then rerun this script."
        exit 1
    }

    Log-Info "Using Python interpreter: $pythonExe"

    # Ensure sentence-transformers is installed
    $stCheck = & $pythonExe -c "import sentence_transformers; print('ok')" 2>&1 | Out-String
    if ($stCheck -notmatch "ok") {
        Log-Info "Installing sentence-transformers package..."
        & $pythonExe -m pip install --quiet sentence-transformers 2>&1 | Out-Null
    }

    # Download and save the model locally
    $saveScript = @"
import os, sys
os.environ['HF_HOME'] = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
save_path = sys.argv[1]
model.save(save_path)
print(f'Model saved to {save_path}')
"@

    $tempScript = Join-Path $env:TEMP "save_st_model.py"
    Set-Content -Path $tempScript -Value $saveScript -Encoding UTF8

    try {
        $saveProc = Start-Process $pythonExe -ArgumentList "`"$tempScript`" `"$stModelDir`"" -NoNewWindow -PassThru -Wait
        if ($saveProc.ExitCode -ne 0) {
            throw "Model save script exited with code $($saveProc.ExitCode)"
        }

        if (Test-Path $stModelConfig) {
            Log-Ok "Sentence Transformer model saved successfully to '$stModelDir'."
            Log-Info "This model will be COPY'd into the Docker image at build time (no runtime download needed)."
        } else {
            throw "Model config.json not found after save operation."
        }
    } catch {
        Log-Err "Failed to save Sentence Transformer model: $_"
        Log-Warn "The Docker image will download the model at first container startup instead."
        Log-Warn "To fix: pip install sentence-transformers, then rerun this script."
    } finally {
        Remove-Item $tempScript -ErrorAction SilentlyContinue
    }
}

# Ensure models directory is in .dockerignore exclusion list (NOT ignored)
$dockerignoreFile = Join-Path $rootDir ".dockerignore"
if (Test-Path $dockerignoreFile) {
    $diContent = Get-Content $dockerignoreFile -Raw
    if ($diContent -match "models/") {
        Log-Warn "'.dockerignore' may be excluding the 'models/' directory. Verify it is NOT ignored."
    }
}

# ------------------------------------------------------------------------------
# STEP 7: Environment File Configuration (.env)
# ------------------------------------------------------------------------------
Log-Info "Step 7/10: Validating environment configuration (.env)..."
$envFile = Join-Path $rootDir ".env"
$envExampleFile = Join-Path $rootDir ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExampleFile) {
        Log-Info "Creating '.env' from template '.env.example'..."
        Copy-Item $envExampleFile $envFile
        Log-Ok "Created default '.env' configuration."
    } else {
        Log-Err "Missing '.env.example' template file."
        exit 1
    }
} else {
    Log-Ok "Found existing '.env' file; preserving current configuration."
}

# ------------------------------------------------------------------------------
# STEP 8: Validate Docker Compose Configuration
# ------------------------------------------------------------------------------
Log-Info "Step 8/10: Validating Docker Compose configuration..."

try {
    $null = docker compose config 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker compose config validation failed"
    }
    Log-Ok "Docker Compose configuration is valid."
} catch {
    Log-Err "Docker Compose configuration error: $_"
    exit 1
}

# ------------------------------------------------------------------------------
# STEP 9: Build and Start GDP Assistant Containers
# ------------------------------------------------------------------------------
Log-Info "Step 9/10: Building and starting GDP Assistant Docker services..."
Log-Info "Executing: docker compose up -d --build..."

try {
    $composeProc = Start-Process docker -ArgumentList "compose up -d --build" -NoNewWindow -PassThru -Wait
    if ($composeProc.ExitCode -ne 0) {
        throw "Docker compose up command returned exit code $($composeProc.ExitCode)"
    }
    Log-Ok "Docker Compose services launched."
} catch {
    Log-Err "Docker Compose build/start failed: $_"
    exit 1
}

# ------------------------------------------------------------------------------
# STEP 10: Verify Application Health and Connectivity
# ------------------------------------------------------------------------------
Log-Info "Step 10/10: Verifying application readiness and container health..."
$healthUrl = "http://localhost/health"
$maxHealthWaitSec = 120
$healthWaited = 0
$isHealthy = $false

Log-Info "Polling $healthUrl for application readiness (timeout 120s)..."
while ($healthWaited -lt $maxHealthWaitSec) {
    Start-Sleep -Seconds 3
    $healthWaited += 3
    try {
        $hResp = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 3 -ErrorAction Stop
        if ($hResp -and ($hResp.status -eq "healthy" -or $hResp.status -eq "degraded" -or $hResp.status -eq "ok")) {
            $isHealthy = $true
            break
        }
    } catch {
        Write-Host -NoNewline "."
    }
}
Write-Host ""

if (-not $isHealthy) {
    Log-Warn "Application health endpoint did not respond with 200 OK within $maxHealthWaitSec seconds."
    Log-Info "Recent container logs:"
    docker logs --tail 30 gdp_assistant
    docker logs --tail 30 gdp_postgres
    exit 1
}

Log-Ok "GDP Assistant application is HEALTHY and responding at $healthUrl."

# Inspect internal supervisor status
Log-Info "Inspecting internal supervisor process tree..."
try {
    $supStatus = (docker exec gdp_assistant supervisorctl status 2>&1 | Out-String)
    Write-Host $supStatus -ForegroundColor Gray

    if ($supStatus -match "FATAL" -or $supStatus -match "BACKOFF") {
        Log-Warn "One or more supervisor sub-processes are not running cleanly. Check container logs."
    } else {
        Log-Ok "All internal services (Nginx, FastAPI, Redis, Worker) are RUNNING."
    }
} catch {
    Log-Warn "Could not query supervisorctl status: $_"
}

# Test Container -> Host Ollama bridge
Log-Info "Testing container-to-host Ollama connectivity (http://host.docker.internal:11434)..."
try {
    $bridgeTest = (docker exec gdp_assistant curl -s -f http://host.docker.internal:11434/api/tags 2>&1)
    if ($bridgeTest -and $bridgeTest -match "models") {
        Log-Ok "Container successfully connected to host Ollama engine."
    } else {
        Log-Warn "Container reached host endpoint but returned: $bridgeTest"
    }
} catch {
    Log-Warn "Container cannot connect to host Ollama via host.docker.internal: $_"
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "   DEPLOYMENT COMPLETE: GDP Assistant is Ready!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "   Web Application UI : http://localhost" -ForegroundColor White
Write-Host "   REST API and Docs  : http://localhost/api/v1/docs" -ForegroundColor White
Write-Host "   System Health Check: http://localhost/health" -ForegroundColor White
Write-Host ""
Write-Host "   Useful Commands:" -ForegroundColor Yellow
Write-Host "     - View App Logs    : docker logs -f gdp_assistant"
Write-Host "     - View DB Logs     : docker logs -f gdp_postgres"
Write-Host "     - Stop Platform    : docker compose down"
Write-Host "     - Restart Platform : docker compose up -d"
Write-Host ""
