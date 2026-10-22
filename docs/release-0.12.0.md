# TwinText 0.12.0 — Faster long replies on Windows and Linux

- Group short, uncached Google Free fragments into bounded requests. Validate all
  generated boundaries before assigning translations; fall back to individual
  fragments when a boundary changes, disappears, repeats or moves out of order.
  Preserve protected Markdown, code, paths, numbers, links and existing caches.
- Reuse network connections through a bounded HTTPX client. Retain Windows/system
  and environment proxy settings, normal TLS verification, redirect rejection,
  response size limits, cancellable backoff and serialized Google requests.
  Do not retain Google cookies or switch providers.
- Display completed paragraphs progressively in the separate reader while pending
  paragraphs remain original. Show a progress percentage and retain reading position.
  Bound and throttle previews; save only complete results to reply translation history.
- Preserve Original cancellation, exact Copy original, late-result rejection and
  source restoration after an error. New replies and scrolling remain manual only.

The same implementation serves Windows and Linux. Offline and Azure also benefit
from progressive reader output, without changing provider or model preferences.

A synthetic 11,042-character formatted article needed 6 requests instead of 157
with mocked network responses. This is a request-count result, not a guaranteed
latency improvement. A small public-text check also confirmed real Google batch
boundaries. Google Free remains unofficial and can change, fail or rate-limit;
batching falls back safely when necessary.

Regression coverage includes batching and malformed boundaries, cancellation,
Unicode URL budgets, cache reuse, protected text, connection reuse, proxy/TLS
configuration, redirects, cookies, response caps, and native reader progress.
Windows/Linux release installation and upgrade gates run before publication.
