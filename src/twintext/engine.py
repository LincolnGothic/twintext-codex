"""Argos model management and CPU inference without inference-time downloads.

Argos supplies installed model metadata and tokenizers. CTranslate2 executes the
same model format directly, so sentence-splitter downloads and cloud-provider
settings in the user's Argos configuration cannot affect this local engine.
"""

import contextlib
import hashlib
import json
import os
import re
import tempfile
import threading
import zipfile
from collections import OrderedDict, deque
from pathlib import Path

from twintext.config import LANGUAGES, TwinTextError, data_dir, private_dir
from twintext.locking import file_lock

STARTER_PAIRS = tuple(
    (a, b) for code in LANGUAGES if code != "en" for a, b in (("en", code), (code, "en"))
)
MODEL_INDEX = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"


def configure_argos():
    # Isolate TwinText's models from any other Argos installation.
    root = private_dir(data_dir() / "argos")
    os.environ["ARGOS_PACKAGES_DIR"] = str(private_dir(root / "packages"))
    os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
    os.environ["ARGOS_MODEL_PROVIDER"] = "OPENNMT"


class ArgosEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.loaded = OrderedDict()

    def package_module(self):
        configure_argos()
        try:
            # Keep stdout reserved for MCP JSON-RPC, including third-party imports.
            import sys

            with contextlib.redirect_stdout(sys.stderr):
                from argostranslate import package, settings
            # settings is a process-global module; refresh paths on every entry.
            root = private_dir(data_dir() / "argos")
            settings.package_data_dir = private_dir(root / "packages")
            settings.package_dirs = [settings.package_data_dir]
            settings.downloads_dir = private_dir(root / "downloads")
            return package
        except ImportError as exc:
            raise TwinTextError(
                "Argos is not installed. Run the Linux install script first."
            ) from exc

    def packages(self):
        return [
            p
            for p in self.package_module().get_installed_packages()
            if p.type == "translate" and p.from_code in LANGUAGES and p.to_code in LANGUAGES
        ]

    def routes(self):
        return [
            {"source": p.from_code, "target": p.to_code, "version": p.package_version}
            for p in self.packages()
        ]

    def route(self, source: str, target: str):
        if source == target:
            return []
        graph = {}
        for package in self.packages():
            graph.setdefault(package.from_code, {})[package.to_code] = package
        queue = deque([(source, [])])
        visited = {source}
        while queue:
            language, path = queue.popleft()
            for next_language, package in graph.get(language, {}).items():
                if next_language == target:
                    return [*path, package]
                if next_language not in visited:
                    queue.append((next_language, [*path, package]))
                    visited.add(next_language)
        raise TwinTextError(
            f"No installed route from {LANGUAGES[source]} to {LANGUAGES[target]}. "
            "Run: twintext models install --starter"
        )

    def fingerprint(self, source: str, target: str):
        items = [
            (
                p.from_code,
                p.to_code,
                p.package_version,
                (p.package_path / "metadata.json").stat().st_mtime_ns,
            )
            for p in self.route(source, target)
        ]
        return hashlib.sha256(json.dumps(["float32-v1", items]).encode()).hexdigest()

    def _model(self, package):
        key = str(package.package_path)
        if key not in self.loaded:
            import ctranslate2

            # Two resident models suffice for an English pivot.
            while len(self.loaded) >= 2:
                self.loaded.popitem(last=False)
            self.loaded[key] = ctranslate2.Translator(
                str(package.package_path / "model"),
                device="cpu",
                # Float32 avoids repetitive decoding observed with the legacy
                # Spanish BPE model in int8 and automatic CPU computation.
                compute_type="float32",
                inter_threads=1,
                intra_threads=min(os.cpu_count() or 1, 4),
            )
        self.loaded.move_to_end(key)
        return self.loaded[key]

    def translate(self, text: str, source: str, target: str):
        with self.lock:
            route = self.route(source, target)
            for package in route:
                translator = self._model(package)
                # Small complete sentences avoid model input truncation.
                chunks = sentence_chunks(text)
                tokens = [package.tokenizer.encode(chunk) for chunk in chunks]
                prefix = getattr(package, "target_prefix", "")
                kwargs = {"target_prefix": [[prefix]] * len(tokens)} if prefix else {}
                limit = min(1024, max(128, 6 * max(len(row) for row in tokens)))
                results = translator.translate_batch(
                    tokens,
                    beam_size=4,
                    replace_unknowns=True,
                    length_penalty=0.2,
                    max_batch_size=32,
                    max_input_length=0,
                    max_decoding_length=limit,
                    **kwargs,
                )
                if any(len(result.hypotheses[0]) >= limit for result in results):
                    raise TwinTextError(
                        "The local model exceeded its decoding limit. "
                        "Try translating a shorter passage."
                    )
                decoded = [package.tokenizer.decode(result.hypotheses[0]) for result in results]
                if prefix:
                    decoded = [value.removeprefix(prefix) for value in decoded]
                text = " ".join(decoded)
            return text.strip()

    def install(self, source: str, target: str):
        if source == target or source not in LANGUAGES or target not in LANGUAGES:
            raise TwinTextError("Choose two different supported languages.")
        with self.lock, file_lock(private_dir(data_dir()) / "models.lock"):
            package_module = self.package_module()
            if any(p.from_code == source and p.to_code == target for p in self.packages()):
                return {"source": source, "target": target, "already_installed": True}
            # Only this explicitly requested operation accesses the network.
            import urllib.request

            from argostranslate import settings

            try:
                with urllib.request.urlopen(MODEL_INDEX, timeout=60) as response:
                    index = json.load(response)
                candidates = [
                    p
                    for p in index
                    if p.get("type", "translate") == "translate"
                    and p.get("from_code") == source
                    and p.get("to_code") == target
                ]
                if not candidates:
                    raise TwinTextError(f"The Argos index has no {source} → {target} model.")
                # Index order is not a version ordering.
                from packaging.version import Version

                metadata = max(candidates, key=lambda p: Version(p.get("package_version", "0")))
                available = package_module.AvailablePackage(metadata)
                path = available.download()
                validate_model_archive(path)
                # Stage before moving: readers never see half-extracted models.
                # Avoid Argos's install helper importing optional online SBD loaders.
                with tempfile.TemporaryDirectory(dir=settings.package_data_dir.parent) as staging:
                    with zipfile.ZipFile(path) as archive:
                        archive.extractall(staging)
                    roots = list(Path(staging).iterdir())
                    if len(roots) != 1 or not roots[0].is_dir():
                        raise TwinTextError("Model archive must contain one model directory.")
                    candidate = package_module.Package(roots[0])
                    if candidate.from_code != source or candidate.to_code != target:
                        raise TwinTextError(
                            "Model metadata does not match the requested languages."
                        )
                    os.replace(roots[0], settings.package_data_dir / roots[0].name)
                path.unlink(missing_ok=True)
                self.loaded.clear()
                return {"source": source, "target": target, "version": metadata["package_version"]}
            except (OSError, ValueError) as exc:
                raise TwinTextError(f"Could not install {source} → {target}: {exc}") from exc


def validate_model_archive(path: Path):
    """Argos extracts zip files; validate all archive member paths first."""
    import zipfile

    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            item = Path(member.filename)
            if item.is_absolute() or ".." in item.parts or "\\" in member.filename:
                raise TwinTextError("Model archive contains an unsafe path.")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise TwinTextError("Model archive contains a symbolic link.")


def sentence_chunks(text: str, maximum: int = 450):
    sentences = re.split(r"(?<=[.!?。！？])\s*|\n+", text)
    result = []
    for sentence in sentences:
        remaining = sentence.strip()
        while len(remaining) > maximum:
            cut = remaining.rfind(" ", 0, maximum + 1)
            if cut < maximum // 2:
                cut = maximum
            result.append(remaining[:cut])
            remaining = remaining[cut:].lstrip()
        if remaining:
            result.append(remaining)
    return result or [text]


def detect_language(text: str):
    # Japanese often contains Han characters, so check kana first.
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", text):
        return "zh"
    try:
        from langdetect import DetectorFactory, detect
        from langdetect.lang_detect_exception import LangDetectException

        DetectorFactory.seed = 0
        code = detect(text)
    except ImportError as exc:
        raise TwinTextError("Language detection is missing. Re-run the install script.") from exc
    except LangDetectException as exc:
        raise TwinTextError(
            "Cannot detect this text's language. Choose a source language."
        ) from exc
    code = {"zh-cn": "zh", "zh-tw": "zh"}.get(code, code)
    if code not in LANGUAGES:
        raise TwinTextError(
            "Language detection is uncertain or unsupported. Choose the source language explicitly."
        )
    return code
