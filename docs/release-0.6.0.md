# TwinText 0.6.0 — floating Chat reader

Chat now has an optional **Floating button and reader** presentation. Codex keeps
the original answer, so its Copy button does not include a translation. Click the
small draggable **T** button to show the reader; click again to hide it and return
to the original conversation. The reader opens beside the button and offers
**Copy original**. Its **×** closes both windows. This is a separate reader, not
an overlay that edits Codex messages or follows the Codex window automatically.

Select **Translation location → Codex chat**, **Chat presentation → Floating
button and reader**, and **Display mode → Bilingual**. Enable **Open floating
button on new replies**, or open the reader manually. Existing installations
default to **In conversation**, preserving the previous display.

Final answers use the trusted Stop hook. All-responses progress updates and enabled
questions use the new local `twintext_send_to_reader` tool; their original text stays
in Codex. These deliveries still use normal Codex tool tokens, but no reader
translation is returned to model context. Question IDs and choice values remain intact.

The floating presentation retains each newly received reply and completed
translation in local history. Older replies remain selectable after a restart and
after clearing the ordinary translation cache. History has no automatic expiry;
use **Clear received replies** to remove it. Existing conversation text is not
rewritten or imported. The original Desktop inbox still retains one latest reply
per chat, up to 24 chats.

The release adds setting, hook, delivery, history, original-copy and native toggle
regressions, while retaining inline Chat, Desktop, offline/Azure and dropdown behavior.
No new dependency or translation provider is added.
