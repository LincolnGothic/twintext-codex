"""Check real Codex hook discovery without a model turn or a trust change."""

import argparse
import json
import queue
import subprocess
import threading
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".agents/plugins/marketplace.json",
    )
    args = parser.parse_args()
    process = subprocess.Popen(
        [args.codex, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    messages = queue.Queue()

    def read():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue
        messages.put(None)

    threading.Thread(target=read, daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "twintext_package_check", "version": "0.2.1"},
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if message is None:
                raise RuntimeError("Codex app-server exited before checking the package.")
            if message.get("id") not in (1, 2):
                continue
            if "error" in message:
                raise RuntimeError(str(message["error"]))
            if message["id"] == 1:
                send({"method": "initialized"})
                send(
                    {
                        "id": 2,
                        "method": "plugin/read",
                        "params": {
                            "pluginName": "twintext",
                            "marketplacePath": str(args.marketplace.resolve()),
                        },
                    }
                )
            else:
                plugin = message["result"]["plugin"]
                hooks = plugin["hooks"]
                if len(hooks) != 1 or hooks[0].get("eventName", "").lower() != "stop":
                    raise RuntimeError(f"Expected one Stop hook, found: {hooks}")
                if "twintext" not in plugin["mcpServers"]:
                    raise RuntimeError("Codex did not discover the TwinText MCP server.")
                print(json.dumps({"hook": hooks[0], "mcpServers": plugin["mcpServers"]}))
                return
        raise RuntimeError("Timed out checking Codex plugin discovery.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process.stdin.close()


if __name__ == "__main__":
    main()
