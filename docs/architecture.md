# TwinText architecture

## One manual selection path

TwinText is a Python companion with a Qt reader, a local settings/preview UI and
stdio MCP configuration tools. It supports Offline, Azure and experimental Google
Free through the shared Markdown translation service. It makes no automatic LLM
translation requests or changes to Codex transcripts.

On Windows, codex_launcher.py starts the installed Codex/shared ChatGPT executable
with loopback debugging after the user exits it normally. It does not kill apps or
patch packaged resources. CMD launchers retain resolved runtime/settings paths.
message_adapter.py validates exactly one supported local main-window target and
installs the runtime message-buttons.js adapter through a bounded protocol session.
Only app://- default contexts can emit validated, nonce-bound button events. It
rejects remote/redirected endpoints and bypasses proxies for loopback discovery.

The renderer adapter walks committed message props and matches a completed visible
assistant body to its source Markdown and conversation/message IDs. It fails closed
on unknown layouts. Mutation/recycling causes rescanning; discovery does not translate.
An explicit Translate/Original click submits that exact source to the reader queue.
No latest-message or clipboard fallback is used. Actions stay English with localized
tooltips; Codex text and native copying stay untouched.

The reader archives clicked originals in Inbox, displays the exact selection, and
submits a translation only on the Translate action. Original cancels pending work;
revision IDs reject stale results. Source stays visible on error. Selecting saved
history shows source first. Manual Paste provides the other explicit input path,
including on Linux. Copy original copies exact source Markdown in every view.

## Settings and migration

config.py validates settings and atomically persists updates while retaining unknown
fields. Valid old workflow choices normalize to chat/floating/message-buttons true;
provider, source/target/UI languages, display, enabled state, cache, pin/follow and
credentials remain independent. Retired mode fields are compatibility data, absent
from the native/web controls and public settings/CLI schema.

Automatic inline and Desktop workflows have been removed. Context hooks provide
manual-only instructions. Stop is not registered; capture and forwarding compatibility
entry points are inert for old registrations. Reader settings never close the reader
through a workflow change. Opening a reader can reconnect its adapter if the existing
Codex process already has the expected debugging endpoint.

Inbox preserves original history and completed reader results. At initialization,
retained old Desktop reply rows are inserted idempotently into history with original
text and timestamps. Existing rows are never replaced. History sorts by created
then ID, descending, so imported older replies do not displace newer entries.

## Translation service and storage

Service parses Markdown and protects code, paths, link destinations, numbers and math.
It uses the selected provider only, preserving bilingual/translated/original views.
The settings UI uses the same explicit translation service for manual preview. Cloud
failures never select another provider. Azure credentials stay in local protected
storage, outside normal settings/tool output. Google uses the unofficial fixed
translate.googleapis.com endpoint, a shared serial lock, encoded-length-aware chunks,
15-second request timeouts and bounded cancellable retries; no key or free quota is
promised. Provider/source/target/text identify cached fragments.

Default disk caching retains the existing bounded fragment policy and persisted
reader results. Session lifetime stores both kinds in bounded process memory and
ignores old disk translations. Disabling cache stops both reads/writes. Clearing
translations preserves originals, settings and models; clearing received history
is separate. Window exit releases session caches and cancels pending translation.

## Packaging and validation

One source-installer ZIP per OS contains the same manual reader. Installation keeps
models and unrelated preferences while persisting profile migration. Message buttons
use the dedicated Windows or native Linux launcher and the same loopback adapter.
Linux discovers the desktop executable beside resources/app.asar, checks this user's
GUI process paths, and starts a detached app only after a normal exit. The installed
menu launcher pins the settings/data paths. Manual Paste remains available on both OSes.
Regular GitHub releases publish only after Windows/Linux regressions and fresh ZIP
installation, real Offline table translation, hooks, Qt and upgrade checks pass.
Unit tests use controlled adapter/DOM/protocol fixtures and never certify all private
Codex renderer versions or automate a user's live Codex UI.
