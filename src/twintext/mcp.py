"""Local newline-delimited JSON-RPC MCP server (stdio transport)."""

import json
import queue
import sys
import threading

from twintext import __version__
from twintext.config import (
    CACHE_LIFETIMES,
    CHAT_PRESENTATIONS,
    LANGUAGES,
    MODES,
    PROVIDERS,
    RESPONSE_SCOPES,
    TRANSLATION_LANGUAGES,
    WORKFLOWS,
    TwinTextError,
    update_settings,
)
from twintext.engine import STARTER_PAIRS
from twintext.service import Service

UI_URI = "ui://twintext/settings.html"
LANGUAGE_SCHEMA = {"type": "string", "enum": list(TRANSLATION_LANGUAGES)}


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
                "openWorldHint": name in (
                    "twintext_install_models", "twintext_translate", "twintext_send_to_reader",
                ),
            },
        }
        if ui:
            result["_meta"] = {"ui": {"resourceUri": UI_URI}}
        return result

    return [
        tool(
            "twintext_translate",
            "Translate Markdown using the selected provider (Offline, Azure or Google Free). "
            "Azure sends source text to Microsoft using locally configured credentials. "
            "Google Free sends source text to Google using an experimental keyless interface. "
            "Return bilingual, translated-only, or original display without changing code.",
            {
                "text": {"type": "string", "maxLength": 100000},
                "source": {"type": "string", "enum": ["auto", *TRANSLATION_LANGUAGES]},
                "target": LANGUAGE_SCHEMA,
                "mode": {"type": "string", "enum": list(MODES)},
            },
            required=("text",),
        ),
        tool("twintext_status", "Read TwinText settings and installed offline models.", {}),
        tool(
            "twintext_send_to_reader",
            "Deliver original Markdown to the local floating Chat reader. "
            "The selected provider translates in the reader; no translation is returned to "
            "model context. Honors response scope, question and auto-start settings.",
            {"text": {"type": "string", "maxLength": 100000},
             "kind": {"type": "string", "enum": ["final", "progress", "question"]},
             "session_id": {"type": "string", "maxLength": 256},
             "turn_id": {"type": "string", "maxLength": 256}},
            required=("text",), read_only=False,
        ),
        tool(
            "twintext_set_settings",
            "Save TwinText translation and display preferences.",
            {
                "provider": {"type": "string", "enum": list(PROVIDERS)},
                "source": {"type": "string", "enum": ["auto", *TRANSLATION_LANGUAGES]},
                "workflow": {"type": "string", "enum": list(WORKFLOWS)},
                "response_scope": {"type": "string", "enum": list(RESPONSE_SCOPES)},
                "chat_presentation": {"type": "string", "enum": list(CHAT_PRESENTATIONS)},
                "translate_questions": {"type": "boolean"},
                "target": LANGUAGE_SCHEMA,
                "mode": {"type": "string", "enum": list(MODES)},
                "ui_language": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "enabled": {"type": "boolean"},
                "cache": {"type": "boolean"},
                "cache_lifetime": {"type": "string", "enum": list(CACHE_LIFETIMES)},
                "message_buttons": {"type": "boolean"},
                "host_locale": {"type": "string", "enum": ["auto", *LANGUAGES]},
                "desktop_auto_start": {"type": "boolean"},
                "always_on_top": {"type": "boolean"},
                "follow_codex": {"type": "boolean"},
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


def call_tool(name, arguments, service, cancel=None):
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
        if "maxLength" in field and len(value) > field["maxLength"]:
            raise TwinTextError(f"{key} exceeds {field['maxLength']} characters.")
    if name == "twintext_translate":
        return (service.translate(**arguments, cancel=cancel) if cancel is not None
                else service.translate(**arguments))
    if name == "twintext_send_to_reader":
        from twintext.bridge import send_to_reader

        return send_to_reader(**arguments)
    if name == "twintext_open_desktop":
        from twintext.bridge import launch_desktop

        return launch_desktop()
    if name == "twintext_set_settings":
        update_settings(**arguments)
        return service.status()
    if name == "twintext_clear_cache":
        from twintext.bridge import Inbox

        Inbox().clear_translations()
        return {"cleared": True}
    if name == "twintext_install_models":
        if service.status()["provider"] != "offline":
            raise TwinTextError("Select Offline before installing Argos models.")
        return {"installed": [service.engine.install(a, b) for a, b in STARTER_PAIRS]}
    return service.status()


def handle(request, service, cancel=None):
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
                value = call_tool(params.get("name"), params.get("arguments", {}), service,
                                  cancel=cancel)
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
    incoming = queue.Queue()
    cancelled = {}
    registry_lock = threading.Lock()
    invalid = object()

    def read():
        # Keep stdin responsive to cancellations while the main worker translates.
        try:
            while line := sys.stdin.buffer.readline(1_100_000):
                event = None
                try:
                    if len(line) > 1_000_000:
                        while line and not line.endswith(b"\n"):
                            line = sys.stdin.buffer.readline(1_100_000)
                        raise ValueError("Frame exceeds 1 MB")
                    request = json.loads(line)
                    if isinstance(request, dict):
                        params = request.get("params", {})
                        if (request.get("jsonrpc") == "2.0" and "id" not in request
                                and request.get("method") == "notifications/cancelled"
                                and isinstance(params, dict)):
                            key = params.get("requestId")
                            if type(key) in (str, int):
                                with registry_lock:
                                    if key in cancelled:
                                        cancelled[key].set()
                            continue
                        if (request.get("method") == "tools/call"
                                and isinstance(params, dict)
                                and params.get("name") == "twintext_translate"
                                and type(request.get("id")) in (str, int)):
                            event = threading.Event()
                            with registry_lock:
                                cancelled[request["id"]] = event
                except (ValueError, UnicodeError):
                    request = invalid
                incoming.put((request, event))
        finally:
            incoming.put(None)

    threading.Thread(target=read, daemon=True).start()
    try:
        for request, event in iter(incoming.get, None):
            if request is invalid:
                response = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32700, "message": "Invalid JSON"}}
            else:
                response = handle(request, service, cancel=event)
                if event is not None:
                    with registry_lock:
                        if cancelled.get(request["id"]) is event:
                            cancelled.pop(request["id"])
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
    finally:
        with registry_lock:
            for event in cancelled.values():
                event.set()
