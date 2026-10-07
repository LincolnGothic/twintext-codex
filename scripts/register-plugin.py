"""Merge one entry into the personal marketplace without changing existing entries."""

import json
import os
import sys
import tempfile
from pathlib import Path

plugin = Path(sys.argv[1]).resolve()
home = Path.home()
try:
    relative = plugin.relative_to(home)
except ValueError:
    sys.exit("The plugin must be inside your home directory for this personal marketplace.")
marketplace = home / ".agents/plugins/marketplace.json"
marketplace.parent.mkdir(parents=True, exist_ok=True)
if marketplace.exists():
    value = json.loads(marketplace.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("plugins"), list):
        sys.exit("Existing marketplace has an unexpected format; it was not changed.")
else:
    value = {
        "name": "twintext-linux",
        "interface": {"displayName": "TwinText Linux"},
        "plugins": [],
    }
entry = {
    "name": "twintext",
    "source": {"source": "local", "path": "./" + str(relative)},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}
existing = next((item for item in value["plugins"] if item.get("name") == "twintext"), None)
if existing and existing.get("source") != entry["source"]:
    sys.exit("A different TwinText entry already exists; the marketplace was not changed.")
if not existing:
    value["plugins"].append(entry)
fd, temporary = tempfile.mkstemp(prefix="marketplace-", suffix=".json", dir=marketplace.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(temporary, marketplace)
finally:
    Path(temporary).unlink(missing_ok=True)
print(f"Plugin registered in {marketplace} (marketplace: {value['name']}).")
