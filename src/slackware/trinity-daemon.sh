#!/bin/bash
# DARTRIX TRINITY DAEMON - Watchdog for Slackware
# Monitors TRINITY_CORE.ps1 or binary equivalents

LOGFILE="/var/log/trinity-daemon.log"
CORE_PATH="/opt/dartrix/TRINITY_CORE.ps1"

echo "[$(date)] Trinity Daemon Started" >> $LOGFILE

while true; do
    # Check if pwsh is running the core script
    if ! pgrep -f "TRINITY_CORE.ps1" > /dev/null; then
        echo "[$(date)] Trinity Core not found. Restarting..." >> $LOGFILE
        pwsh -File "$CORE_PATH" &
    fi
    sleep 30
done
