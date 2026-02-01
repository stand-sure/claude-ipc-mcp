# IPC Watcher Scripts

Tools for monitoring IPC messages with audio/visual notifications.

## Quick Start

```bash
# Python version (recommended - more reliable)
./ipc-watcher.py --instance-id claude-ipc-mcp --interval 5

# Bash version (requires Claude Code CLI)
./ipc-watcher.sh claude-ipc-mcp 5
```

## Python Watcher (ipc-watcher.py)

**Recommended**: Direct socket connection to IPC broker.

### Features
- ✅ Direct TCP socket connection (no CLI dependency)
- ✅ Automatic session management and re-registration
- ✅ Audio notifications via macOS `say`
- ✅ Clear message formatting
- ✅ Error handling and recovery
- ✅ Background-friendly

### Usage

```bash
# Basic usage
./ipc-watcher.py --instance-id your-instance-name

# Custom check interval (10 seconds)
./ipc-watcher.py --instance-id saskia --interval 10

# Disable audio notifications
./ipc-watcher.py --instance-id claude-ipc-mcp --no-audio

# Run in background (nohup)
nohup ./ipc-watcher.py --instance-id claude-ipc-mcp &

# Run in background (screen/tmux)
screen -S ipc-watcher
./ipc-watcher.py --instance-id claude-ipc-mcp
# Press Ctrl+A then D to detach
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--instance-id` | (required) | Your Claude instance ID |
| `--interval` | 5 | Seconds between message checks |
| `--host` | 127.0.0.1 | IPC broker host |
| `--port` | 9876 | IPC broker port |
| `--no-audio` | false | Disable audio notifications |

### Example Output

```
[2026-01-30 15:45:00] IPC Watcher starting...
[2026-01-30 15:45:00] Instance ID: claude-ipc-mcp
[2026-01-30 15:45:00] Check interval: 5s
[2026-01-30 15:45:00] Broker: 127.0.0.1:9876
[2026-01-30 15:45:00] Registering as claude-ipc-mcp...
[2026-01-30 15:45:00] ✓ Registered successfully
[2026-01-30 15:45:00] Watching for messages... (Ctrl+C to stop)

[2026-01-30 15:45:05] 📭 Inbox clear
[2026-01-30 15:45:10] 🔔 1 new message(s) received!

================================================================================
Message 1/1
================================================================================
From:    saskia
Time:    2026-01-30T15:40:19.885143
Content: Hey! Testing IPC between Claude instances. Can you see this?
================================================================================
```

## Bash Watcher (ipc-watcher.sh)

**Alternative**: Uses Claude Code CLI (less reliable, more dependencies).

### Usage

```bash
# Basic usage
./ipc-watcher.sh claude-ipc-mcp 5

# Arguments: instance-id check-interval
./ipc-watcher.sh saskia 10

# Background usage
nohup ./ipc-watcher.sh claude-ipc-mcp 5 &
```

### Requirements
- Claude Code CLI installed
- MCP server configured in `~/.claude/mcp_config.json`

## Integration with Home Notify

To enable visual notifications via Hue lights:

1. Ensure `home-notify` MCP server is configured
2. Edit the watcher script and set `visual_enabled = True`
3. Uncomment the MCP tool call section

## Troubleshooting

### "Connection refused"
- Check if IPC MCP server is running
- Verify port 9876 is accessible: `lsof -i :9876`
- Ensure mcp-langchain-bridge has claude-ipc configured

### "Session token invalid"
- Session tokens expire after 24 hours
- Watcher automatically re-registers on expiry
- Check `~/.claude-ipc-data/messages.db` permissions

### No audio notifications
- macOS only: Requires `say` command
- Check audio is not muted
- Test manually: `say "test message"`

### Messages not appearing
- Verify sender used correct instance ID
- Check messages weren't already consumed by another check
- Look in `~/.claude-ipc-data/messages.db` for stored messages

## Advanced: Systemd Service (Linux)

Create `/etc/systemd/system/ipc-watcher.service`:

```ini
[Unit]
Description=Claude IPC Message Watcher
After=network.target

[Service]
Type=simple
User=your-username
ExecStart=/path/to/claude-ipc-mcp/bin/ipc-watcher.py --instance-id claude-ipc-mcp
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ipc-watcher
sudo systemctl start ipc-watcher
sudo systemctl status ipc-watcher
```

## Advanced: LaunchAgent (macOS)

Create `~/Library/LaunchAgents/com.user.ipc-watcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.ipc-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/claude-ipc-mcp/bin/ipc-watcher.py</string>
        <string>--instance-id</string>
        <string>claude-ipc-mcp</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ipc-watcher.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ipc-watcher.err</string>
</dict>
</plist>
```

Load and start:
```bash
launchctl load ~/Library/LaunchAgents/com.user.ipc-watcher.plist
launchctl start com.user.ipc-watcher
```

## For Other AIs

If you're an AI reading this to help a user set up IPC watching:

1. **Recommended approach**: Use `ipc-watcher.py` (Python version)
2. **Required info from user**: Their instance ID (e.g., "saskia", "claude-ipc-mcp")
3. **Basic command**:
   ```bash
   cd /path/to/claude-ipc-mcp/bin
   ./ipc-watcher.py --instance-id USER_INSTANCE_ID
   ```
4. **Background command**:
   ```bash
   nohup ./ipc-watcher.py --instance-id USER_INSTANCE_ID &
   ```
5. **Stop background process**:
   ```bash
   pkill -f "ipc-watcher.py.*USER_INSTANCE_ID"
   ```

The Python script is self-contained and handles all edge cases. Just ensure the IPC MCP server is running (it auto-starts with mcp-langchain-bridge).
