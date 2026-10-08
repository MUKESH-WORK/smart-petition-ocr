# ==============================================================================
# GDP Assistant - Fresh Server Host and Ollama Bootstrap Script (Windows)
# ==============================================================================
# Automates host pre-flight verification, Ollama installation, daemon startup,
# AI model downloading (qwen2.5:7b-instruct-q4_K_M / configurable), Redis installation,
# Sentence Transformer model caching, environment setup, and Docker Compose deployment.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup_host.ps1
# ==============================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
$rootDir = $PSScriptRoot

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

    $py311Local = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311"
    if ((Test-Path $py311Local) -and ($env:Path -notlike "*$py311Local*")) {
        $env:Path = "$py311Local;$py311Local\Scripts;$env:Path"
    }

    $py311Prog = "C:\Program Files\Python311"
    if ((Test-Path $py311Prog) -and ($env:Path -notlike "*$py311Prog*")) {
        $env:Path = "$py311Prog;$py311Prog\Scripts;$env:Path"
    }
}

function Find-Python311 {
    # 1. Check py launcher for 3.11
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $ver = (py -3.11 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1 | Out-String).Trim()
            if ($ver -eq "3.11") {
                $exe = (py -3.11 -c "import sys; print(sys.executable)" 2>&1 | Out-String).Trim()
                if (Test-Path $exe) { return $exe }
            }
        } catch {}
    }

    # 2. Check standard installation directories
    $commonPaths = @(
        "C:\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "${env:ProgramFiles(x86)}\Python311\python.exe"
    )
    foreach ($cp in $commonPaths) {
        if (Test-Path $cp) {
            try {
                $ver = (& $cp -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1 | Out-String).Trim()
                if ($ver -eq "3.11") { return $cp }
            } catch {}
        }
    }

    # 3. Check system python in PATH if version is 3.11
    $sysPy = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPy) {
        try {
            $ver = (& $sysPy.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1 | Out-String).Trim()
            if ($ver -eq "3.11") { return $sysPy.Source }
        } catch {}
    }

    return $null
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
# STEP 4: Check / Pull Required Ollama Model
# ------------------------------------------------------------------------------
$envFilePath = Join-Path $rootDir ".env"
if (-not (Test-Path $envFilePath)) {
    $envFilePath = Join-Path $rootDir ".env.example"
}
$targetModel = "qwen2.5:7b-instruct-q4_K_M"
if (Test-Path $envFilePath) {
    try {
        $modelMatch = Select-String -Path $envFilePath -Pattern "^\s*LLM_MODEL_NAME\s*=\s*['`"]?([^'`"#\s]+)" | Select-Object -First 1
        if ($modelMatch -and $modelMatch.Matches[0].Groups[1].Value) {
            $targetModel = $modelMatch.Matches[0].Groups[1].Value.Trim()
        }
    } catch {}
}

Log-Info "Step 4/10: Checking required LLM model ($targetModel)..."

$hasModel = $false
try {
    $tagsResp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 5
    if ($tagsResp -and $tagsResp.models) {
        foreach ($m in $tagsResp.models) {
            if ($m.name -like "*$targetModel*" -or $m.model -like "*$targetModel*") {
                $hasModel = $true
                break
            }
        }
    }
} catch {
    Log-Warn "REST tag inspection failed; checking via ollama list CLI..."
    try {
        $listOutput = (ollama list 2>&1 | Out-String)
        if ($listOutput -match [regex]::Escape($targetModel)) {
            $hasModel = $true
        }
    } catch {}
}

if ($hasModel) {
    Log-Ok "Required Ollama model '$targetModel' is already installed."
} else {
    Log-Info "Model '$targetModel' is missing. Downloading via 'ollama pull $targetModel'..."
    try {
        $pullProcess = Start-Process ollama -ArgumentList "pull $targetModel" -NoNewWindow -PassThru -Wait
        if ($pullProcess.ExitCode -ne 0) {
            throw "Ollama pull command exited with code $($pullProcess.ExitCode)"
        }
        Log-Ok "Model '$targetModel' successfully downloaded and verified."
    } catch {
        Log-Err "Failed to pull Ollama model '$targetModel': $_"
        Log-Err "Please run 'ollama pull $targetModel' manually, then rerun this script."
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
Log-Info "Step 6/10: Preparing Sentence Transformer model for offline Docker builds..."

$rootDir = $PSScriptRoot
$modelDir = Join-Path $rootDir "models"
$stModelDir = Join-Path $modelDir "paraphrase-multilingual-MiniLM-L12-v2"
$stModelConfig = Join-Path $stModelDir "config.json"
$venvDir = Join-Path $rootDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (Test-Path $stModelConfig) {
    Log-Ok "Sentence Transformer model 'paraphrase-multilingual-MiniLM-L12-v2' is already saved in '$modelDir'."
} else {
    # 1. Locate or install Python 3.11
    Log-Info "Checking for Python 3.11..."
    $py311Exe = Find-Python311

    if (-not $py311Exe) {
        Log-Warn "Python 3.11 is not installed."
        Log-Info "Attempting automated installation using winget..."

        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Log-Err "Python 3.11 could not be installed automatically."
            Log-Err "winget is unavailable or installation failed."
            Log-Err "Please install Python 3.11 and rerun setup_host.ps1."
            exit 1
        }

        try {
            Log-Info "Running: winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent"
            $pyInstall = Start-Process winget -ArgumentList "install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent" -NoNewWindow -PassThru -Wait
            
            Update-SessionPath
            Start-Sleep -Seconds 3

            $py311Exe = Find-Python311
            if (-not $py311Exe) {
                throw "Python 3.11 executable not found after winget installation."
            }
            Log-Ok "Python 3.11 installed successfully."
        } catch {
            Log-Err "Python 3.11 could not be installed automatically."
            Log-Err "winget is unavailable or installation failed: $_"
            Log-Err "Please install Python 3.11 and rerun setup_host.ps1."
            exit 1
        }
    } else {
        Log-Ok "Python 3.11 found: $py311Exe"
    }

    # 2. Setup Dedicated Virtual Environment (.venv)
    $venvDir = Join-Path $rootDir ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    $isVenvValid = $false
    if (Test-Path $venvPython) {
        try {
            $vVer = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1 | Out-String).Trim()
            if ($vVer -eq "3.11") {
                $isVenvValid = $true
            }
        } catch {}
    }

    if (-not $isVenvValid) {
        if (Test-Path $venvDir) {
            Log-Warn "Existing virtual environment at '$venvDir' is not Python 3.11. Recreating..."
            Remove-Item -Recurse -Force $venvDir -ErrorAction SilentlyContinue
        }

        Log-Info "Creating dedicated Python virtual environment..."
        try {
            $venvCreate = Start-Process $py311Exe -ArgumentList "-m venv `"$venvDir`"" -NoNewWindow -PassThru -Wait
            if ($venvCreate.ExitCode -ne 0 -or -not (Test-Path $venvPython)) {
                throw "Virtual environment creation failed with exit code $($venvCreate.ExitCode)"
            }
            # Ensure pip is present
            & $venvPython -m ensurepip --default-pip 2>&1 | Out-Null
            Log-Ok "Python virtual environment ready: $venvPython"
        } catch {
            Log-Err "Failed to create Python virtual environment: $_"
            exit 1
        }
    } else {
        Log-Ok "Python virtual environment ready: $venvPython"
    }

    # 3. Install host-side dependencies (sentence-transformers, torch)
    $stCheck = $null
    try {
        $stCheck = & $venvPython -c "import sentence_transformers, torch; print('ok')" 2>&1 | Out-String
    } catch {}

    if ($stCheck -notmatch "ok") {
        Log-Info "Installing host-side sentence-transformers and torch..."
        try {
            # Check and bootstrap pip if missing in existing venv
            $venvPip = Join-Path (Split-Path $venvPython) "pip.exe"
            if (-not (Test-Path $venvPip)) {
                Log-Info "Bootstrapping pip in virtual environment..."
                & $venvPython -m ensurepip --default-pip
            }

            $pipProc = Start-Process $venvPython -ArgumentList "-m pip install sentence-transformers torch" -NoNewWindow -PassThru -Wait
            if ($pipProc.ExitCode -ne 0) {
                throw "pip install exited with code $($pipProc.ExitCode)"
            }

            # Verify import after installation
            $stVerify = & $venvPython -c "import sentence_transformers, torch; print('ok')" 2>&1 | Out-String
            if ($stVerify -notmatch "ok") {
                throw "Import verification failed after pip installation: $stVerify"
            }
            Log-Ok "Host-side Python dependencies verified."
        } catch {
            Log-Err "Failed to install host-side Python dependencies (sentence-transformers, torch): $_"
            exit 1
        }
    } else {
        Log-Ok "Host-side Python dependencies verified."
    }

    # 4. Download and save Sentence Transformer model
    Log-Info "Downloading paraphrase-multilingual-MiniLM-L12-v2..."
    if (-not (Test-Path $modelDir)) {
        New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
    }

    $saveScript = @"
import os, sys, re
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HOME'] = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))

# Read HF_TOKEN from environment or .env file if available
hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
if not hf_token and os.path.exists('.env'):
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\s*HF_TOKEN\s*=\s*["\']?([^"\'#\s]+)', line)
                if match:
                    hf_token = match.group(1).strip()
                    break
    except Exception:
        pass

if hf_token:
    os.environ['HF_TOKEN'] = hf_token
    os.environ['HUGGING_FACE_HUB_TOKEN'] = hf_token
    print('Using authenticated Hugging Face API token.')

from sentence_transformers import SentenceTransformer
kwargs = {'token': hf_token} if hf_token else {}
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', **kwargs)
save_path = sys.argv[1]
model.save(save_path)
print(f'Model saved successfully to {save_path}')
"@

    $tempScript = Join-Path $env:TEMP "save_st_model.py"
    Set-Content -Path $tempScript -Value $saveScript -Encoding UTF8

    try {
        $saveProc = Start-Process $venvPython -ArgumentList "`"$tempScript`" `"$stModelDir`"" -NoNewWindow -PassThru -Wait
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
        exit 1
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
Log-Info "Synchronizing host LAN IP for mobile QR access..."
try {
    $syncScript = Join-Path $rootDir "scripts\sync_host_lan_ip.py"
    if (Test-Path $syncScript) {
        $pyRunner = if ($venvPython -and (Test-Path $venvPython)) { $venvPython } elseif ($py311Exe -and (Test-Path $py311Exe)) { $py311Exe } else { "python" }
        $null = & $pyRunner "$syncScript" --once 2>&1
        Log-Ok "Host LAN network configuration initialized."
    }
} catch {
    Log-Warn "Host network sync notice: $_"
}

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
$healthUrl = "http://localhost:8080/health"
$fallbackHealthUrl = "http://localhost/health"
$maxHealthWaitSec = 300
$healthWaited = 0
$isHealthy = $false
$activeUrl = $healthUrl

Log-Info "Polling $healthUrl for application readiness (timeout 300s)..."
while ($healthWaited -lt $maxHealthWaitSec) {
    Start-Sleep -Seconds 3
    $healthWaited += 3
    try {
        $hResp = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 3 -ErrorAction Stop
        if ($hResp -and ($hResp.status -eq "healthy" -or $hResp.status -eq "degraded" -or $hResp.status -eq "ok")) {
            $isHealthy = $true
            $activeUrl = $healthUrl
            break
        }
    } catch {
        try {
            $hRespFallback = Invoke-RestMethod -Uri $fallbackHealthUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
            if ($hRespFallback -and ($hRespFallback.status -eq "healthy" -or $hRespFallback.status -eq "degraded" -or $hRespFallback.status -eq "ok")) {
                $isHealthy = $true
                $activeUrl = $fallbackHealthUrl
                break
            }
        } catch {
            Write-Host -NoNewline "."
        }
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

Log-Ok "GDP Assistant application is HEALTHY and responding at $activeUrl."

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
Write-Host "   Web Application UI : http://localhost:8080" -ForegroundColor White
Write-Host "   REST API and Docs  : http://localhost:8080/api/v1/docs" -ForegroundColor White
Write-Host "   System Health Check: http://localhost:8080/health" -ForegroundColor White
Write-Host ""
Write-Host "   Useful Commands:" -ForegroundColor Yellow
Write-Host "     - View App Logs    : docker logs -f gdp_assistant"
Write-Host "     - View DB Logs     : docker logs -f gdp_postgres"
Write-Host "     - Stop Platform    : docker compose down"
Write-Host "     - Restart Platform : docker compose up -d"
Write-Host ""