# Third-party software and language models

TwinText's own source is MIT licensed; retain its copyright and license notice.
The release archives contain TwinText source, installers and documentation only.
They do **not** redistribute Python, Qt/PySide, PyTorch, translation weights or
other dependency binaries. Installers obtain dependencies from their upstream
package repositories. No paid Qt license or hosted translation API is required
for this source/installer distribution.

## Runtime dependencies

These dependencies retain their own licenses. The installed distributions'
license files are authoritative; the list is not a license grant for their code.

| Component | Upstream license / reference |
| --- | --- |
| Argos Translate | [MIT or CC0](https://github.com/argosopentech/argos-translate/blob/master/LICENSE) |
| CTranslate2 | [MIT](https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE) |
| PyTorch | [BSD-style license and third-party notices](https://github.com/pytorch/pytorch/blob/main/LICENSE) |
| Stanza | [Apache 2.0](https://github.com/stanfordnlp/stanza/blob/main/LICENSE) |
| SentencePiece | [Apache 2.0](https://github.com/google/sentencepiece/blob/master/LICENSE) |
| langdetect | [Apache 2.0](https://github.com/Mimino666/langdetect/blob/master/LICENSE) |
| markdown-it-py | [MIT](https://github.com/executablebooks/markdown-it-py/blob/master/LICENSE) |
| PySide6/Qt | [LGPLv3/GPLv3 or commercial](https://doc.qt.io/qtforpython-6/licenses.html) |

If you redistribute a bundled executable or dependency binaries, perform a new
audit of the exact dependency versions and modules. Source availability, license
notices and relinking/replacement requirements may apply to Qt. Making an app
free of charge does not remove those obligations. This release intentionally
does not provide frozen/bundled executables.

## Language packages

Models are downloaded **only on request**, directly from the official
[Argos package index](https://github.com/argosopentech/argospm-index).
Installed model directories contain their upstream `README.md` and metadata.
Do not assume the engine's MIT license licenses model weights or training data.

The eight packages tested during TwinText development have the following
README statements. Different upstream versions require another review.

| Direction | Package | README license statement |
| --- | --- | --- |
| English → Chinese | translate-en_zh-1_9 | Derived OPUS model: CC-BY 4.0 |
| Chinese → English | translate-zh_en-1_9 | Derived OPUS model: CC-BY 4.0 |
| English → French | translate-en_fr-1_9 | Derived OPUS model: CC-BY 4.0 |
| French → English | translate-fr_en-1_9 | Derived OPUS model: CC-BY 4.0 |
| Spanish → English | translate-es_en-1_9 | Derived OPUS model: CC-BY 4.0 |
| English → Spanish | en_es | Model-weight license not stated; corpus/Stanza credits only |
| English → Japanese | en_ja | Model-weight license not stated; corpus/Stanza credits only |
| Japanese → English | ja_en | Model-weight license not stated; corpus/Stanza credits only |

The OPUS-MT packages credit Jörg Tiedemann and Santhosh Thottingal, *OPUS-MT —
Building open translation services for the World*, EAMT 2020. Preserve their
model READMEs and attribution. The legacy Spanish/Japanese packages reference
OPUS corpora, Stanza and (Japanese) Wiktionary/Wiktextract, CCAligned and WikiMatrix.
These credits alone do not establish a model redistribution license.

The missing model-weight statements remain unresolved upstream; see
[Argos issue 507](https://github.com/argosopentech/argos-translate/issues/507).
This release makes no claim that those packages are cleared for redistribution
or commercial use. Before including weights in your own distribution, obtain
clarification or substitute models with explicit compatible licenses. Neither
free pricing nor separate downloads resolve unclear upstream licenses.
