"""Linux CLI and entry points for the Codex plugin."""

import argparse
import json
import sys
from pathlib import Path

from twintext import __version__
from twintext.cache import Cache
from twintext.config import LANGUAGES, MODES, TwinTextError, load_settings, update_settings
from twintext.engine import STARTER_PAIRS, ArgosEngine
from twintext.service import Service, context


def parser():
    result = argparse.ArgumentParser(prog="twintext", description="Offline translation for Codex")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    translate = commands.add_parser("translate", help="Translate a UTF-8 file or stdin")
    translate.add_argument("file", nargs="?", help="Input file; omit or use - for stdin")
    translate.add_argument("--source", choices=["auto", *LANGUAGES])
    translate.add_argument("--target", choices=list(LANGUAGES))
    translate.add_argument("--mode", choices=MODES)
    translate.add_argument("--json", action="store_true")
    settings = commands.add_parser("settings", help="Read or save settings")
    settings.add_argument("--source", choices=["auto", *LANGUAGES])
    settings.add_argument("--target", choices=list(LANGUAGES))
    settings.add_argument("--mode", choices=MODES)
    settings.add_argument("--ui-language", choices=["auto", *LANGUAGES])
    settings.add_argument("--enabled", choices=["true", "false"])
    settings.add_argument("--cache", choices=["true", "false"])
    commands.add_parser("status", help="Inspect settings and installed models")
    models = commands.add_parser("models", help="Manage offline language models")
    operations = models.add_subparsers(dest="operation", required=True)
    operations.add_parser("list", help="List installed models (offline)")
    install = operations.add_parser("install", help="Download official Argos models")
    install.add_argument("--starter", action="store_true", help="Install all five languages")
    install.add_argument("--source", choices=list(LANGUAGES))
    install.add_argument("--target", choices=list(LANGUAGES))
    commands.add_parser("clear-cache", help="Remove cached translations")
    commands.add_parser("mcp", help="Serve local MCP over stdio")
    commands.add_parser("context", help="Print Codex hook context")
    ui = commands.add_parser("ui", help="Open the settings page on localhost")
    ui.add_argument("--port", type=int, default=0)
    ui.add_argument("--open", action="store_true", dest="open_browser")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "mcp":
            from twintext.mcp import serve

            serve()
        elif args.command == "ui":
            from twintext.ui import serve

            serve(args.port, args.open_browser)
        elif args.command == "translate":
            text = (
                Path(args.file).read_text(encoding="utf-8")
                if args.file and args.file != "-"
                else sys.stdin.read()
            )
            result = Service().translate(
                text, source=args.source, target=args.target, mode=args.mode
            )
            print(json.dumps(result, ensure_ascii=False) if args.json else result["display"])
        elif args.command == "settings":
            changes = {
                key: getattr(args, key)
                for key in ("source", "target", "mode", "ui_language", "enabled", "cache")
                if getattr(args, key) is not None
            }
            for key in ("enabled", "cache"):
                if key in changes:
                    changes[key] = changes[key] == "true"
            value = update_settings(**changes) if changes else load_settings()
            print(json.dumps(value.as_dict(), ensure_ascii=False, indent=2))
        elif args.command == "status":
            print(json.dumps(Service().status(), ensure_ascii=False, indent=2))
        elif args.command == "clear-cache":
            Cache().clear()
            print("Translation cache cleared.")
        elif args.command == "context":
            print(context())
        elif args.command == "models":
            engine = ArgosEngine()
            if args.operation == "list":
                print(json.dumps(engine.routes(), ensure_ascii=False, indent=2))
            else:
                if args.starter and (args.source or args.target):
                    raise TwinTextError("Use --starter or a source/target pair, not both.")
                if not args.starter and not (args.source and args.target):
                    raise TwinTextError("Use --starter or both --source and --target.")
                pairs = STARTER_PAIRS if args.starter else [(args.source, args.target)]
                for source, target in pairs:
                    print(f"Installing {source} → {target}…", file=sys.stderr, flush=True)
                    print(json.dumps(engine.install(source, target)), flush=True)
        return 0
    except (TwinTextError, OSError, ValueError, RuntimeError) as exc:
        print(f"TwinText: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
