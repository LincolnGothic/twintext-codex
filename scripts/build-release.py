"""Build small Windows/Linux source-installer archives, without model/runtime binaries."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("src", "plugins", "scripts", "docs", "tests", ".agents", ".github")
FILES = ("pyproject.toml", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", ".gitignore")


def build(platform, output):
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)[1]
    output.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    paths = sorted(
        path
        for path in paths
        if not any(part == "__pycache__" or part.endswith(".egg-info") for part in path.parts)
        and path.suffix not in (".pyc", ".argosmodel", ".sqlite3")
    )
    archives = []
    for workflow in ("chat", "desktop"):
        name = f"TwinText-{version}-{platform}-{workflow}"
        destination = output / f"{name}.zip"
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, f"{name}/{path.relative_to(ROOT).as_posix()}")
            archive.writestr(
                f"{name}/release.json",
                json.dumps(
                    {
                        "version": version,
                        "platform": platform,
                        "workflow": workflow,
                        "package": "source-installer",
                        "models_bundled": False,
                        "runtime_bundled": False,
                    },
                    indent=2,
                )
                + "\n",
            )
        archives.append(destination)
    checksum = output / f"SHA256SUMS-{platform}.txt"
    checksum.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in archives
        ),
        encoding="utf-8",
    )
    return [*archives, checksum]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=("linux", "windows"))
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    for artifact in build(args.platform, args.output):
        print(artifact)
