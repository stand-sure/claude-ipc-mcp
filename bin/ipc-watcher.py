#!/usr/bin/env python3
"""
IPC Message Watcher for Claude Code

Purpose: Polls for IPC messages and notifies via audio/visual alerts
Usage:   ./ipc-watcher.py --instance-id claude-ipc-mcp --interval 5
Example: python3 ipc-watcher.py --instance-id saskia --interval 10

This directly calls the IPC MCP server via socket connection.
More reliable than calling through Claude Code CLI.

Requirements:
- Claude IPC MCP server running (port 9876)
- macOS (for 'say' command)
- Python 3.8+
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional


class IPCWatcher:
    """Watches for IPC messages and sends notifications"""

    def __init__(self, instance_id: str, check_interval: int = 5, host: str = "127.0.0.1", port: int = 9876):
        self.instance_id = instance_id
        self.check_interval = check_interval
        self.host = host
        self.port = port
        self.session_token: Optional[str] = None
        self.audio_enabled = True
        self.visual_enabled = False  # Set to True if home-notify configured

    def log(self, message: str):
        """Log with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)

    def send_broker_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to IPC broker"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5.0)
            client_socket.connect((self.host, self.port))

            # Send request
            client_socket.send(json.dumps(request).encode('utf-8'))

            # Receive response
            response_data = client_socket.recv(65536).decode('utf-8')
            response = json.loads(response_data)

            client_socket.close()
            return response

        except ConnectionRefusedError:
            self.log("ERROR: Cannot connect to IPC broker. Is the MCP server running?")
            self.log(f"       Trying to connect to {self.host}:{self.port}")
            return {"status": "error", "message": "Connection refused"}
        except Exception as e:
            self.log(f"ERROR: Broker connection failed: {e}")
            return {"status": "error", "message": str(e)}

    def register(self) -> bool:
        """Register with IPC broker and get session token"""
        self.log(f"Registering as {self.instance_id}...")

        # Check for shared secret (optional)
        shared_secret = os.environ.get("IPC_SHARED_SECRET", "")
        auth_token = ""
        if shared_secret:
            import hashlib
            auth_token = hashlib.sha256(f"{self.instance_id}:{shared_secret}".encode()).hexdigest()

        response = self.send_broker_request({
            "action": "register",
            "instance_id": self.instance_id,
            "auth_token": auth_token
        })

        if response.get("status") == "ok":
            self.session_token = response.get("session_token")
            self.log(f"✓ Registered successfully")
            if "queued" in response.get("message", ""):
                self.log(f"  {response['message']}")
            return True
        else:
            self.log(f"✗ Registration failed: {response.get('message')}")
            return False

    def check_messages(self) -> Dict[str, Any]:
        """Check for new messages"""
        if not self.session_token:
            self.log("ERROR: Not registered. Call register() first.")
            return {"status": "error", "messages": []}

        response = self.send_broker_request({
            "action": "check",
            "instance_id": self.instance_id,
            "session_token": self.session_token
        })

        return response

    def notify_audio(self, message: str):
        """Send audio notification via macOS 'say' command"""
        if not self.audio_enabled:
            return

        try:
            # Run in background so it doesn't block
            subprocess.Popen(
                ["say", message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            self.log("WARN: 'say' command not found (macOS only)")
            self.audio_enabled = False  # Disable future attempts
        except Exception as e:
            self.log(f"WARN: Audio notification failed: {e}")

    def notify_visual(self, message: str, severity: str = "success"):
        """Send visual notification (requires home-notify MCP)"""
        if not self.visual_enabled:
            return

        # TODO: Integrate with home-notify MCP tool
        self.log(f"VISUAL: {message} (severity: {severity})")

    def format_messages(self, messages: list) -> str:
        """Format messages for display"""
        if not messages:
            return "No messages"

        output = []
        for i, msg in enumerate(messages, 1):
            output.append(f"\n{'='*80}")
            output.append(f"Message {i}/{len(messages)}")
            output.append(f"{'='*80}")
            output.append(f"From:    {msg.get('from', 'unknown')}")
            output.append(f"Time:    {msg.get('timestamp', 'unknown')}")
            output.append(f"Content: {msg.get('message', {}).get('content', 'no content')}")

            # Show data if present
            data = msg.get('message', {}).get('data')
            if data:
                output.append(f"Data:    {json.dumps(data, indent=2)}")

            output.append(f"{'='*80}\n")

        return "\n".join(output)

    def run(self):
        """Main watcher loop"""
        self.log(f"IPC Watcher starting...")
        self.log(f"Instance ID: {self.instance_id}")
        self.log(f"Check interval: {self.check_interval}s")
        self.log(f"Broker: {self.host}:{self.port}")

        # Register first
        if not self.register():
            self.log("FATAL: Registration failed. Exiting.")
            return 1

        self.log("Watching for messages... (Ctrl+C to stop)")
        self.log("")

        try:
            while True:
                response = self.check_messages()

                if response.get("status") == "ok":
                    messages = response.get("messages", [])

                    if messages:
                        # New messages!
                        self.log(f"🔔 {len(messages)} new message(s) received!")

                        # Format and display
                        formatted = self.format_messages(messages)
                        print(formatted)

                        # Extract summary for notification
                        first_msg = messages[0]
                        sender = first_msg.get('from', 'unknown')
                        content = first_msg.get('message', {}).get('content', '')[:50]
                        summary = f"Message from {sender}: {content}..."

                        # Send notifications
                        self.notify_audio(f"Attention meatbag! IPC message from {sender}!")
                        self.notify_visual(summary, "success")

                    else:
                        # No messages - quiet log
                        self.log("📭 Inbox clear")

                elif response.get("status") == "error":
                    error_code = response.get("error_code", "unknown")
                    error_msg = response.get("message", "unknown error")
                    is_recoverable = response.get("recoverable", False)

                    # Handle recoverable errors (expired tokens, missing tokens)
                    if error_code == "token_expired":
                        self.log(f"⚠️  Session expired (tokens expire after 24h). Re-registering...")
                        if not self.register():
                            self.log("FATAL: Re-registration failed. Exiting.")
                            return 1
                        self.log("✓ Re-registered successfully. Mailbox preserved!")
                    elif error_code == "missing_token":
                        self.log("⚠️  Session token missing. Re-registering...")
                        if not self.register():
                            self.log("FATAL: Registration failed. Exiting.")
                            return 1
                    elif is_recoverable:
                        self.log(f"⚠️  Recoverable error ({error_code}): {error_msg}")
                        self.log("Attempting to re-register...")
                        if not self.register():
                            self.log("FATAL: Re-registration failed. Exiting.")
                            return 1
                    else:
                        # Non-recoverable error
                        self.log(f"ERROR ({error_code}): {error_msg}")
                        if error_code == "invalid_token":
                            self.log("HINT: Your session token is invalid. Try re-registering manually.")
                        elif error_code == "database_error":
                            self.log("HINT: Database connection issue. Check ~/.claude-ipc-data/")

                # Wait before next check
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.log("\nIPC Watcher stopped by user")
            return 0

        except Exception as e:
            self.log(f"FATAL: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="IPC Message Watcher - Poll for inter-Claude messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch with default settings (5s interval)
  %(prog)s --instance-id claude-ipc-mcp

  # Watch with custom interval
  %(prog)s --instance-id saskia --interval 10

  # Run in background
  nohup %(prog)s --instance-id claude-ipc-mcp &

  # Connect to remote broker
  %(prog)s --instance-id worker1 --host 192.168.1.100 --port 9876
        """
    )

    parser.add_argument(
        '--instance-id',
        required=True,
        help='Your Claude instance ID'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Seconds between checks (default: 5)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='IPC broker host (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9876,
        help='IPC broker port (default: 9876)'
    )
    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Disable audio notifications'
    )

    args = parser.parse_args()

    # Create watcher
    watcher = IPCWatcher(
        instance_id=args.instance_id,
        check_interval=args.interval,
        host=args.host,
        port=args.port
    )

    if args.no_audio:
        watcher.audio_enabled = False

    # Run it
    sys.exit(watcher.run())


if __name__ == "__main__":
    main()
