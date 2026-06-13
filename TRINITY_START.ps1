# TRINITY_START.ps1
# Bootstrap trzech rdzeni: BIOLOGY / COGNITION / AGENCY
# DARTRIX RUNTIME v1.0

param(
    [string]$EnvName = "DEV",
    [string]$LogDir = "./logs",
    [int]$TickMs = 200
)

# --- CONFIG / PATHS ---------------------------------------------------------

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src  = Join-Path $Root "src"
$Bio  = Join-Path $Src "dartrix-biology-v1"
$LogDir = Resolve-Path $LogDir -ErrorAction SilentlyContinue -ErrorVariable logErr

if (-not $LogDir) {
    $LogDir = New-Item -ItemType Directory -Path (Join-Path $Root "logs")
}

$LogFile = Join-Path $LogDir ("TRINITY" + (Get-Date -Format "yyyyMMddHHmmss") + ".log")

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $line = "[$ts][$Level] $Message"
    $line | Out-File -FilePath $LogFile -Encoding UTF8 -Append
    Write-Host $line
}

Write-Log "TRINITY_START.ps1 :: ENV=$EnvName TICK=${TickMs}ms"

# --- CHECK MODULES ---------------------------------------------------------

$runtimeAxis = Join-Path $Bio "runtimeAxisEarBreath.ts"
$phiDeltoid  = Join-Path $Bio "phiDeltoid.ts"
$fusionMod   = Join-Path $Bio "fusion.ts"

$required = @($runtimeAxis, $phiDeltoid, $fusionMod)

foreach ($f in $required) {
    if (-not (Test-Path $f)) {
        Write-Log "Missing module: $f" "ERROR"
        throw "Required module not found: $f"
    }
}

Write-Log "All core modules present."

# --- NODE / TS RUNTIME CHECK -----------------------------------------------

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Log "Node.js not found in PATH." "ERROR"
    throw "Node.js required for TRINITY runtime."
}

Write-Log "Node.js detected at: $($node.Source)"

# --- BIOLOGY ENGINE (FUSION) -----------------------------------------------

$BioScript = @"
import { computeFusion } from "./src/dartrix-biology-v1/fusion"
import { SpineAxis } from "./src/dartrix-biology-v1/runtimeAxisEarBreath"

const spine: SpineAxis = {
  thetaN: 5,
  thetaL: -3,
  thetaP: 2,
  tensionN: 0.4,
  tensionL: 0.5,
  tensionP: 0.6,
} as any

const depth = 0.7

const sensory = {
  dermatome: { C5: 0.3, C6: 0.1 },
  proprioception: 0.6,
  visionStability: 0.7,
}

const motor = {
  myotome: { C5: 0.4, C6: 0.2 },
  activation: 0.5,
}

const m = 0.8
const radius = 0.25

const state = computeFusion(spine, depth, sensory, motor, m, radius)

console.log(JSON.stringify({
  fusionScore: state.fusionScore,
  vestibularBalance: state.axis.ear.vestibularBalance,
  resonanceError: state.axis.resonanceError,
}, null, 2))
"@

$BioTmp = Join-Path $Root "trinity_bio.ts"
$BioScript | Out-File -FilePath $BioTmp -Encoding UTF8 -Force

# --- COGNITION ENGINE (m-impuls) -------------------------------------------

function Get-CognitionState {
    param(
        [double]$Load,
        [double]$ResonanceError
    )
    # prosty heurystyczny m ∈ [0,1]
    $m = [Math]::Max(0, [Math]::Min(1, 1.0 - ($ResonanceError + $Load) / 4.0))
    return $m
}

# --- AGENCY ENGINE (ROUTING) -----------------------------------------------

function Route-Agency {
    param(
        [double]$FusionScore,
        [double]$VestibularBalance
    )

    if ($FusionScore -lt 0.3) {
        return "STATE: PROTECT | ACTION: REDUCE_LOAD"
    }
    elseif ($FusionScore -lt 0.6) {
        return "STATE: ADAPT | ACTION: MICRO_ADJUST"
    }
    else {
        if ($VestibularBalance -lt 0.4) {
            return "STATE: STABLEAXIS / UNSTABLEBALANCE | ACTION: GAZE_FIX + BREATH"
        }
        return "STATE: FLOW | ACTION: EXECUTE_PLAN"
    }
}

# --- MAIN LOOP -------------------------------------------------------------

Write-Log "TRINITY :: BOOTSTRAP COMPLETE. ENTERING MAIN LOOP."

$running = $true

while ($running) {
    try {
        # BIOLOGY: odpalamy fusion przez node
        $bioJson = node --loader ts-node/esm $BioTmp 2>$null
        if (-not $bioJson) {
            Write-Log "BIOLOGY: no output from fusion." "WARN"
            Start-Sleep -Milliseconds $TickMs
            continue
        }

        $bioState = $null
        try {
            $bioState = $bioJson | ConvertFrom-Json
        } catch {
            Write-Log "BIOLOGY: invalid JSON from fusion." "ERROR"
            throw
        }

        $fusionScore      = [double]$bioState.fusionScore
        $vestibular       = [double]$bioState.vestibularBalance
        $resonanceError   = [double]$bioState.resonanceError

        # COGNITION: wyliczamy m na podstawie obciążenia
        $m = Get-CognitionState -Load (1 - $fusionScore) -ResonanceError $resonanceError

        # AGENCY: routing decyzji
        $route = Route-Agency -FusionScore $fusionScore -VestibularBalance $vestibular

        Write-Log ("FUSION={0:F3} | VEST={1:F3} | E={2:F3} | m={3:F3} | {4}" -f `
            $fusionScore, $vestibular, $resonanceError, $m, $route)

        Start-Sleep -Milliseconds $TickMs
    }
    catch {
        Write-Log "TRINITY LOOP ERROR: $($_.Exception.Message)" "ERROR"
        $running = $false
    }
}

Write-Log "TRINITY :: SHUTDOWN COMPLETE."
