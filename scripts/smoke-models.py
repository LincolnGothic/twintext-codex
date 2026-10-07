"""Exercise every supported pair using real models with Python networking disabled."""

import json
import socket
import sys

from twintext.config import LANGUAGES, update_settings
from twintext.service import Service

SAMPLES = {
    "en": "The program works now. Please save the file.",
    "zh": "程序现在可以正常运行。请保存文件。",
    "ja": "プログラムは正常に動作しています。ファイルを保存してください。",
    "fr": "Le programme fonctionne maintenant. Veuillez enregistrer le fichier.",
    "es": "El programa funciona ahora. Por favor, guarda el archivo.",
}


def denied(*args, **kwargs):
    raise AssertionError("Inference attempted network access")


socket.socket.connect = denied
socket.create_connection = denied
socket.getaddrinfo = denied
update_settings(enabled=True, cache=False)
service = Service()
results = []
for source, sample in SAMPLES.items():
    for target in LANGUAGES:
        if source == target:
            continue
        text = sample + "\n\n`npm test`\n\n```python\nprint('unchanged')\n```\n"
        result = service.translate(text, source=source, target=target, mode="bilingual")
        if result["translation"] == text or not result["translation"].strip():
            sys.exit(f"No translation produced for {source} → {target}")
        if (
            result["display"].count("print('unchanged')") != 1
            or "`npm test`" not in result["display"]
        ):
            sys.exit(f"Protected text changed for {source} → {target}")
        results.append(
            {
                "source": source,
                "target": target,
                "route": result["route"],
                "translation": result["translation"].split("\n")[0],
            }
        )
        print(f"PASS {source} → {target}", file=sys.stderr, flush=True)
print(
    json.dumps(
        {"pairs_checked": len(results), "offline": True, "results": results},
        ensure_ascii=False,
        indent=2,
    )
)
