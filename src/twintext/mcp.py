"""Local newline-delimited JSON-RPC MCP server (stdio transport)."""

import json
import sys

from twintext import __version__
from twintext.cache import Cache
from twintext.config import LANGUAGES, MODES, WORKFLOWS, TwinTextError, update_settings
from twintext.engine import STARTER_PAIRS
from twintext.service import Service

UI_URI = "ui://twintext/settings.html"
LANGUAGE_SCHEMA = {"type": "string", "enum": list(LANGUAGES)}


def tools():
    def tool(name, description, properties, required=(), read_only=True, ui=False):
        result = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": list(required),
                "additionalProperties": False,
            },
            "annotations": {
                "readOnlyHint": read_only,
                "destructiveHint": False,
                "openWorldHint": name == "twintext_install_models",
            },
        }
        if ui:
            result["_meta"] = {"ui": {"resourceUri": UI_URI}}
        return result

    return [
        tool(
            "twintext_translate",
            "Translate Markdown offline with local Argos models. "
            "Return bilingual, translated-only, or original display without changing code.",
            {
                "text": {"type": "string", "maxLength": 100000},
                "source": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "target": LANGUAGE_SCHEMA,
                "mode": {"type": "string", "enum": list(MODES)},
            },
            required=("text",),
        ),
        tool("twintext_status", "Read TwinText settings and installed offline models.", {}),
        tool(
            "twintext_set_settings",
            "Save TwinText translation and display preferences.",
            {
                "source": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "workflow": {"type": "string", "enum": list(WORKFLOWS)},
                "target": LANGUAGE_SCHEMA,
                "mode": {"type": "string", "enum": list(MODES)},
                "ui_language": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "enabled": {"type": "boolean"},
                "cache": {"type": "boolean"},
                "host_locale": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "desktop_auto_start": {"type": "boolean"},
                "always_on_top": {"type": "boolean"},
            },
            read_only=False,
        ),
        tool(
            "twintext_settings_ui",
            "Open TwinText's multilingual settings and translation "
            "preview. UI language follows the host locale unless overridden.",
            {},
            ui=True,
        ),
        tool("twintext_clear_cache", "Clear the local translation cache.", {}, read_only=False),
        tool(
            "twintext_open_desktop",
            "Open the local floating TwinText reader. Completed Codex replies are translated "
            "in this window by the Stop hook, without returning translations to the model.",
            {},
            read_only=False,
        ),
        tool(
            "twintext_install_models",
            "Download the eight official Argos models for the "
            "English, Chinese, Japanese, French, and Spanish starter pack. "
            "Use only when the user requests model installation; this requires internet.",
            {},
            read_only=False,
        ),
    ]


def call_tool(name, arguments, service):
    definition = next((tool for tool in tools() if tool["name"] == name), None)
    if definition is None:
        raise TwinTextError(f"Unknown tool: {name}")
    if not isinstance(arguments, dict):
        raise TwinTextError("Tool arguments must be an object.")
    schema = definition["inputSchema"]
    if arguments.keys() - schema["properties"].keys():
        raise TwinTextError("Unexpected tool arguments.")
    if not set(schema["required"]).issubset(arguments):
        raise TwinTextError("Missing required tool arguments.")
    for key, value in arguments.items():
        field = schema["properties"][key]
        if field["type"] == "string" and not isinstance(value, str):
            raise TwinTextError(f"{key} must be a string.")
        if field["type"] == "boolean" and type(value) is not bool:
            raise TwinTextError(f"{key} must be true or false.")
        if "enum" in field and value not in field["enum"]:
            raise TwinTextError(f"Invalid {key}.")
    if name == "twintext_translate":
        return service.translate(**arguments)
    if name == "twintext_open_desktop":
        from twintext.bridge import launch_desktop

        return launch_desktop()
    if name == "twintext_set_settings":
        update_settings(**arguments)
        return service.status()
    if name == "twintext_clear_cache":
        Cache().clear()
        return {"cleared": True}
    if name == "twintext_install_models":
        return {"installed": [service.engine.install(a, b) for a, b in STARTER_PAIRS]}
    return service.status()


def handle(request, service):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
        }
    if "id" not in request:
        return None
    response = {"jsonrpc": "2.0", "id": request["id"]}
    method = request.get("method")
    params = request.get("params", {})
    if not isinstance(params, dict):
        response["error"] = {"code": -32602, "message": "Params must be an object"}
        return response
    try:
        if method == "initialize":
            version = params.get("protocolVersion")
            supported = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
            result = {
                "protocolVersion": version if version in supported else supported[-1],
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "twintext", "version": __version__},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tools()}
        elif method == "resources/list":
            result = {
                "resources": [
                    {
                        "uri": UI_URI,
                        "name": "TwinText Settings",
                        "mimeType": "text/html;profile=mcp-app",
                    }
                ]
            }
        elif method == "resources/templates/list":
            result = {"resourceTemplates": []}
        elif method == "resources/read":
            if params.get("uri") != UI_URI:
                raise TwinTextError("Unknown resource URI.")
            from twintext.ui import html

            result = {
                "contents": [
                    {
                        "uri": UI_URI,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": html(embedded=True),
                        "_meta": {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}}},
                    }
                ]
            }
        elif method == "tools/call":
            try:
                value = call_tool(params.get("name"), params.get("arguments", {}), service)
                text = value.get("display", json.dumps(value, ensure_ascii=False))
                result = {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": value,
                    "isError": False,
                }
            except (TwinTextError, OSError, ValueError, TypeError, RuntimeError) as exc:
                result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}
            return response
        response["result"] = result
    except (TwinTextError, OSError, ValueError, TypeError) as exc:
        response["error"] = {"code": -32602, "message": str(exc)}
    return response


def serve():
    service = Service()
    while True:
        line = sys.stdin.buffer.readline(1_100_000)
        if not line:
            break
        try:
            if len(line) > 1_000_000:
                # Drain the remainder of this oversized frame, then continue.
                while not line.endswith(b"\n"):
                    line = sys.stdin.buffer.readline(1_100_000)
                    if not line:
                        break
                raise ValueError("Frame exceeds 1 MB")
            request = json.loads(line)
            response = handle(request, service)
        except (ValueError, UnicodeError):
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Invalid JSON"},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
