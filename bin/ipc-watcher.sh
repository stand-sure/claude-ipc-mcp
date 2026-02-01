#!/bin/bash
# IPC Message Watcher for Claude Code
#
# Purpose: Polls for IPC messages and notifies via audio/visual alerts
# Usage:   ./ipc-watcher.sh [instance-id] [interval-seconds]
# Example: ./ipc-watcher.sh claude-ipc-mcp 5
#
# Requirements:
# - Claude IPC MCP server running (automatically started by mcp-langchain-bridge)
# - macOS (for 'say' command)
# - Optional: home-notify MCP server for visual alerts
#
# Background usage: nohup ./ipc-watcher.sh claude-ipc-mcp 5 &

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

INSTANCE_ID="${1:-claude-ipc-mcp}"
CHECK_INTERVAL="${2:-5}"  # seconds between checks
LAST_CHECK_FILE="/tmp/ipc-watcher-${INSTANCE_ID}.lastcheck"
LOG_FILE="/tmp/ipc-watcher-${INSTANCE_ID}.log"

# Audio notification settings (macOS 'say' command)
AUDIO_ENABLED=true
AUDIO_VOICE="Samantha"  # or "Alex", "Victoria", etc.

# Visual notification settings (requires home-notify MCP)
VISUAL_ENABLED=false  # Set to true if you have home-notify configured

# ============================================================================
# Functions
# ============================================================================

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $*" | tee -a "$LOG_FILE"
}

notify_audio() {
    if [ "$AUDIO_ENABLED" = true ]; then
        # Run in background so it doesn't block message processing
        say -v "$AUDIO_VOICE" "$1" &
    fi
}

notify_visual() {
    if [ "$VISUAL_ENABLED" = true ]; then
        # This would call home-notify MCP tool
        # For now, just log (you can integrate MCP tool call here)
        log "VISUAL: $1 (severity: $2)"
        # TODO: Add MCP tool call when home-notify is configured
        # claude code mcp execute home-notify notify_human "$1" "$2"
    fi
}

check_messages() {
    # Use Claude Code CLI to check for messages
    # This assumes you have claude code CLI and MCP server configured

    # Method 1: Direct MCP tool execution (preferred)
    if command -v claude &> /dev/null; then
        local result=$(claude code -c "use mcp tool claude-ipc check instance_id=$INSTANCE_ID" 2>&1 || true)
    else
        # Method 2: Call Python MCP server directly (fallback)
        # This requires the server to be running as a standalone service
        log "ERROR: claude code CLI not found. Please install Claude Code."
        return 1
    fi

    echo "$result"
}

parse_messages() {
    local output="$1"

    # Check if there are new messages (simple grep check)
    if echo "$output" | grep -q "From:"; then
        return 0  # Has messages
    else
        return 1  # No messages
    fi
}

extract_message_summary() {
    local output="$1"

    # Extract first message summary for notification
    # Format: "From: sender\nTime: timestamp\nContent: message"
    local sender=$(echo "$output" | grep "From:" | head -1 | sed 's/From: //')
    local content=$(echo "$output" | grep "Content:" | head -1 | sed 's/Content: //' | cut -c1-50)

    echo "Message from ${sender}: ${content}..."
}

# ============================================================================
# Main Loop
# ============================================================================

log "Starting IPC watcher for instance: $INSTANCE_ID"
log "Check interval: ${CHECK_INTERVAL}s"
log "Log file: $LOG_FILE"
log "Last check file: $LAST_CHECK_FILE"

# Initialize last check timestamp
date +%s > "$LAST_CHECK_FILE"

trap 'log "IPC watcher stopped"; exit 0' SIGINT SIGTERM

while true; do
    log "Checking for messages..."

    result=$(check_messages)

    if parse_messages "$result"; then
        # New messages detected!
        log "NEW MESSAGES DETECTED"
        log "---"
        log "$result"
        log "---"

        # Extract summary for notification
        summary=$(extract_message_summary "$result")

        # Send notifications
        notify_audio "Attention meatbag! You've got IPC mail from the machines!"
        notify_visual "IPC Message: $summary" "success"

        # Update last check time
        date +%s > "$LAST_CHECK_FILE"

        # Display full messages to console
        echo ""
        echo "================================================================================"
        echo "NEW IPC MESSAGES"
        echo "================================================================================"
        echo "$result"
        echo "================================================================================"
        echo ""

    else
        log "No new messages (inbox clear)"
    fi

    # Wait before next check
    sleep "$CHECK_INTERVAL"
done
