# TRINITY_CORE.ps1
# Core Event Loop & Agency State Machine
# DARTRIX RUNTIME v1.1

param(
    [double]$TargetResonance = 25.748,
    [double]$ScalingFactor = 7.14,
    [int]$TickMs = 100
)

# --- CONFIGURATION ----------------------------------------------------------
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FusionPath = Join-Path $Root "src/dartrix-biology-v1/fusion.ts"

# --- THREAD-SAFE EVENT QUEUE ------------------------------------------------
$EventQueue = [System.Collections.Concurrent.ConcurrentQueue[PSObject]]::new()

function Publish-Event {
    param([string]$Type, [string]$Source, [hashtable]$Data)
    $evt = [PSCustomObject]@{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Type      = $Type
        Source    = $Source
        Data      = $Data
    }
    $EventQueue.Enqueue($evt)
}

# --- MODULE WATCHDOG --------------------------------------------------------
$Global:LastHeartbeat = Get-Date
function Check-Watchdog {
    if (Test-Path $FusionPath) {
        $Global:LastHeartbeat = Get-Date
        return $true
    }
    return $false
}

# --- STATE MACHINE (AGENCY) -------------------------------------------------
$Global:CurrentState = "ADAPT" # Default state

function Resolve-AgencyState {
    param([double]$FusionScore, [double]$Resonance)
    
    $prev = $Global:CurrentState
    if ($FusionScore -lt 0.3 -or $Resonance -lt ($TargetResonance * 0.5)) {
        $Global:CurrentState = "PROTECT"
    }
    elseif ($FusionScore -gt 0.8 -and $Resonance -gt ($TargetResonance * 0.9)) {
        $Global:CurrentState = "FLOW"
    }
    else {
        $Global:CurrentState = "ADAPT"
    }

    if ($prev -ne $Global:CurrentState) {
        Publish-Event -Type "INTERNAL_EVENT" -Source "AGENCY" -Data @{ Transition = "$prev -> $($Global:CurrentState)" }
    }
}

# --- MAIN LOOP --------------------------------------------------------------
Write-Host "DARTRIX TRINITY CORE :: STARTING" -ForegroundColor Cyan
Publish-Event -Type "SYSTEM_EVENT" -Source "CORE" -Data @{ Status = "BOOTING"; ScalingFactor = $ScalingFactor }

$Running = $true
$Iteration = 0

while ($Running) {
    try {
        $Iteration++
        
        # 1. Watchdog & Heartbeat
        if (-not (Check-Watchdog)) {
            Publish-Event -Type "INTERNAL_EVENT" -Source "WATCHDOG" -Data @{ Error = "fusion.ts missing" }
        }

        # 2. Simulate Telemetry Input (In real scenario, this reads from node/fusion output)
        $SimulatedFusionScore = 0.6 # Base value for headless execution
        
        # 3. Agency Routing
        Resolve-AgencyState -FusionScore $SimulatedFusionScore -Resonance $TargetResonance

        # 4. Cognition m-impuls Modifier
        $mImpulse = (1.0 - (1.0 / $ScalingFactor)) * $SimulatedFusionScore

        # 5. Process Event Queue
        while ($EventQueue.TryDequeue([ref]$currentEvt)) {
            $color = switch ($currentEvt.Type) {
                "SYSTEM_EVENT"   { "Green" }
                "INTERNAL_EVENT" { "Yellow" }
                "INPUT_EVENTS"   { "White" }
                "OUTPUT_EVENTS"  { "Magenta" }
                default          { "Gray" }
            }
            Write-Host "[$($currentEvt.Timestamp)][$($currentEvt.Type)] Source: $($currentEvt.Source) | Data: $($currentEvt.Data | ConvertTo-Json -Compress)" -ForegroundColor $color
        }

        # Status Update
        Write-Host "ITER: $Iteration | STATE: $Global:CurrentState | m: $($mImpulse.ToString('F3')) | F: $SimulatedFusionScore" -NoNewline
        Write-Host "`r" -NoNewline

        Start-Sleep -Milliseconds $TickMs
    }
    catch {
        Write-Host "`nCORE CRITICAL ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $Running = $false
    }
}

Write-Host "DARTRIX TRINITY CORE :: SHUTDOWN" -ForegroundColor Cyan
