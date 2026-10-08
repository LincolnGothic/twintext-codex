# TwinText 0.3.0 troubleshooting

Start with a local test: choose source **English**, target **Chinese**, display
**Bilingual**, paste an English sentence into TwinText and press **Translate**.
If that succeeds, the engine works and the remaining issue is likely integration
or window behavior. These steps apply to both Windows and Linux.

## Text stays in its original language

Check the target and source settings. The default target is English; an English
reply translated into English remains unchanged. **Original** mode also leaves
text unchanged. Short text can confuse automatic detection, so choose the source
explicitly for a test. Code, numbers, paths and protected blocks intentionally remain
unchanged; a fenced code block containing a table is treated as code.

Check installed models with `twintext status` or `twintext models list`. On Windows,
run these commands through `& "$env:LOCALAPPDATA\TwinText\TwinText.cmd"`.
Models are not downloaded automatically. Request the five-language pack from web
settings (`twintext ui --open`), or install the required pair:

```bash
twintext models install --source en --target zh
```

Non-English pairs need both legs of the route through English. Review the
[model notices](../THIRD_PARTY_NOTICES.md) before requesting downloads.

## Local translation works, but Codex replies do not arrive

Make sure the TwinText plugin is installed/enabled in the personal Codex marketplace,
then restart Codex and review/trust its hooks. Rerunning the runtime installer
registers the plugin but does not automatically install/enable it in Codex or grant
hook trust. Upgrades can add hooks that require another review.

Check **Translation location**. In **Chat** mode, Stop capture is inactive, so an
empty Desktop inbox is expected. In **Desktop** mode, enable **Receive Codex replies**.
Only newly completed replies are captured; previous messages and streaming fragments
are not imported. Paste/Translate works independently of automatic capture.

On an affected host, use the developer probe `python scripts/check-codex-plugin.py`
with the repository's Python environment to verify plugin/hook discovery. This
read-only probe does not grant trust or start a model turn. Discovery alone does
not prove delivery in an actual chat.

## Chat does not use the translator, or still follows the previous style

Set the translation location to **Chat**, enable translation and choose a target
that differs from the reply's source. Start a new Codex chat after switching from
Desktop so SessionStart/UserPromptSubmit supplies the selected workflow's instructions.
Automatic Chat translation depends on Codex following those instructions and
calling the available `twintext_translate` tool; it is not a native renderer overlay.

When switching back to Desktop, start a new chat too. Old Chat instructions can
remain in an existing conversation even when later Desktop hooks return no context.

## The floating window does not open or stay above Codex

Launch **TwinText Desktop** from your application menu/Start, or run
`twintext desktop`. If automatic opening is desired, enable **Open floating button
on new replies**. Repeated launches should activate the existing reader.

On Linux, launch within a graphical session and check Qt's system-library errors.
Ubuntu/Debian may require the packages documented in [installation](../README.md#linux).
Wayland/compositor policy can ignore placement or always-on-top hints. If XWayland
is available, try `QT_QPA_PLATFORM=xcb twintext desktop`. Actual movement uses Qt's
system-move request; behavior depends on the desktop/window manager.

## The compact button is hard to move

Use its visible six-dot grip, or deliberately drag the TwinText button itself.
Click without dragging to expand. The expanded reader's header is also draggable;
its bottom-right grip resizes it. The reader is movable but does not automatically
follow the Codex window.

## The interface language does not match Codex

Translation target and TwinText interface language are independent. Automatic
can use a supported Codex locale previously supplied by the embedded settings
panel. Hooks do not supply that locale; Desktop falls back to the system language,
and standalone web settings can follow browser language. Choose the interface
language manually when Automatic cannot determine the language you want.

## Does translation consume Codex tokens?

Offline Argos/CTranslate2 inference does not consume LLM tokens or require a
translation API payment. Automatic **Desktop** translation adds no model calls
or translated text to Codex context. **Chat** instructions, translation tool calls,
results and final bilingual output use normal Codex tokens; longer replies increase
the overhead. Asking Codex to configure/open TwinText or manually translate also
uses normal tokens. No negligible-cost guarantee is made.

## Where are saved records, and when are they deleted?

See the [local-record paths](../README.md#local-records) for each operating system.
There is no timed expiry. The translation cache holds up to 10,000 fragments; the
separate Desktop inbox holds the latest original reply from up to 24 chats.

Turning off **Remember translations locally** stops cache reads/writes but preserves
existing entries. It does not stop inbox storage in Desktop mode. **Clear cache**
deletes cached translations; **Clear received replies** clears the inbox. Each
control leaves the other store, preferences and models alone. Clearing normally
completes immediately, and SQLite files may remain after their records are cleared.

## Report a formatting or integration problem

Use the repository's [Issues page](https://github.com/LincolnGothic/twintext-codex/issues).
Include OS/architecture, Python/Codex/TwinText versions, Chat/Desktop style, language
pair, display mode, whether Paste/Translate works and a small sanitized Markdown
example. Describe expected and actual behavior. Avoid posting private replies,
credentials or your local databases. Formatting coverage is documented
[here](output-formats.md); model quality is separate from formatting correctness.
