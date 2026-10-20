# TwinText 0.7.0 — experimental Google Free and a calmer palette

Adds the optional **Google Free (experimental)** provider (`google-free`), with no
API key. Offline remains the default; Azure, inline Chat, floating Chat, bilingual
display, settings, models, caches and reader history are retained.

This uses an unofficial keyless interface, not a Google Cloud-supported API. It may
be rate limited, fail or change; availability, translation quality and free quota
are not guaranteed. Text is sent to Google. The same warning is shown in all five
interface languages. No automatic fallback or new third-party service is introduced.

Google supports automatic detection, explicit Simplified Chinese (`zh` → `zh-CN`),
and Google-only Traditional Chinese (`zh-TW`). Requests use the Python backend,
encoded URL chunks, the existing cross-process lock and local fragment cache.
One request runs at a time, with a 15-second timeout, up to two exponential-backoff
retries and valid Retry-After support. Cancellation stops pending chunks/retries;
in-flight blocking I/O may take up to its timeout. The standalone preview aborts
work when leaving the page. MCP processes cancellation notifications while its
single translation worker runs; the embedded panel sends them on close/timeout,
requiring the host to forward them. Chunk boundary whitespace is preserved even
if Google trims it from translated fragments.

Both native and web interfaces use a coordinated blue-gray/indigo palette; the web
dark theme is retained. Layout and controls are preserved. Failed preview requests
show the current original instead of an earlier translation, with a clear error
and restored loading controls.

140 regression tests pass on the development Windows environment (one Unix-only
skip), including mocked Google requests, parsing, encoding, long text/paragraphs,
language mapping, cache, cancellation, retries, settings and UI failure behavior.
A public “Hello world.” connectivity check returned “你好世界。”; this verifies one
request only and does not guarantee future service availability.
