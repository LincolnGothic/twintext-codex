/* Optional runtime adapter. It never replaces message text or uses the clipboard.
 * Codex's private renderer shape can change; unrecognized messages fail closed. */
(() => {
  "use strict";
  window.__twintextMessages?.stop();
  const config = window.TWINTEXT_MESSAGE_CONFIG;
  if (!config || typeof window[config.binding] !== "function") return;
  const words = {
    en:["Translate", "Original", "Translate this reply in TwinText", "Show original in TwinText", "Translation failed; click to retry"],
    zh:["Translate", "Original", "在 TwinText 中翻译这条回复", "在 TwinText 中显示原文", "翻译失败，点击重试"],
    ja:["Translate", "Original", "この返信を TwinText で翻訳", "TwinText で原文を表示", "翻訳に失敗しました。クリックして再試行"],
    fr:["Translate", "Original", "Traduire cette réponse dans TwinText", "Afficher l’original dans TwinText", "Échec de traduction ; cliquez pour réessayer"],
    es:["Translate", "Original", "Traducir esta respuesta en TwinText", "Mostrar el original en TwinText", "Error al traducir; pulsa para reintentar"]
  }[config.language] || ["Translate", "Original", "Translate this reply in TwinText", "Show original in TwinText", "Translation failed; click to retry"];
  const records = new Map();
  const requests = new Map();
  let serial = 0, timer, stopped = false;
  const validId = value => typeof value === "string" && value.trim() && value.length <= 256;

  function messages(onlyBody) {
    const bodies = new Set(onlyBody ? [onlyBody] : document.querySelectorAll("[data-selected-text-overlay-target]"));
    const roots = new Set(), found = new Map();
    for (const body of bodies) {
      if (!body.isConnected) continue;
      const key = Object.keys(body).find(name => name.startsWith("__reactFiber$"));
      let top = key && body[key];
      for (let depth = 0; top?.return && depth < 300; depth++) top = top.return;
      if (top && !top.return && top.stateNode?.current) roots.add(top.stateNode.current);
    }
    for (const tree of roots) {
      // Walk the committed child graph. Bailouts can share children whose return
      // pointers still reach the previous root; those pointers cannot select props.
      const stack = [{fiber:tree, owner:null, root:null}], seen = new Set();
      while (stack.length && seen.size < 100000) {
        let {fiber, owner, root} = stack.pop();
        if (!fiber || seen.has(fiber)) continue;
        seen.add(fiber);
        if (fiber.sibling) stack.push({fiber:fiber.sibling, owner, root});
        if (fiber.memoizedProps?.item?.type) { owner = fiber.memoizedProps; root = null; }
        const node = fiber.stateNode;
        if (owner && !root && node instanceof Element) root = node;
        if (bodies.has(node)) {
          const item = owner?.item, id = item?.searchItemId || item?.responseAnnotationTargetId;
          if (item?.type === "assistant-message" && item.completed === true &&
              [undefined, null, "final_answer", "commentary"].includes(item.phase) &&
              validId(id) && validId(owner.conversationId) && root && root !== node &&
              root.contains(node) && typeof item.content === "string" &&
              item.content.trim() && item.content.length <= 100000) {
            found.set(node, {root, session:owner.conversationId, message:id, text:item.content});
          }
        }
        if (fiber.child) stack.push({fiber:fiber.child, owner, root});
      }
    }
    return found;
  }

  function paint(record, error = false) {
    record.button.textContent = words[record.active ? 1 : 0];
    record.button.setAttribute("aria-pressed", String(record.active));
    record.button.title = words[error ? 4 : record.active ? 3 : 2];
  }

  function install(body, current) {
    if (records.has(current.root)) return;
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("data-twintext-translate", "");
    button.setAttribute("data-markdown-copy", "exclude");
    button.style.cssText = "align-self:flex-start;margin:5px 0;padding:3px 9px;border:1px solid #94a3b866;border-radius:8px;background:transparent;color:inherit;font:inherit;font-size:12px;cursor:pointer;user-select:none";
    const record = {body, button, active:false, key:null, request:null};
    paint(record);
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      const selected = messages(body).get(body);
      if (!selected || selected.root !== current.root) return;
      const identity = JSON.stringify([selected.session, selected.message, selected.text]);
      if (identity !== record.key) record.active = false;
      record.key = identity;
      record.active = !record.active;
      if (record.request !== null) requests.delete(record.request);
      record.request = ++serial;
      requests.set(serial, record);
      paint(record);
      try {
        window[config.binding](JSON.stringify({document:config.document, request:serial,
          action:record.active ? "translate" : "original", session:selected.session,
          message:selected.message, text:selected.text}));
      } catch {
        record.active = false;
        paint(record, true);
      }
    });
    records.set(current.root, record);
    current.root.append(button);
  }

  function scan() {
    timer = undefined;
    if (stopped) return;
    for (const [root, record] of records) {
      if (!root.isConnected || !root.contains(record.body) || !root.contains(record.button)) {
        record.button.remove();
        requests.delete(record.request);
        records.delete(root);
      }
    }
    for (const [body, current] of messages()) install(body, current);
  }
  const observer = new MutationObserver(() => {
    if (timer === undefined) timer = setTimeout(scan, 20);
  });
  function start() {
    if (stopped) return;
    observer.observe(document.documentElement, {childList:true, subtree:true, characterData:true});
    scan();
  }
  window.__twintextMessages = {
    feedback(value) {
      if (value.document !== config.document) return;
      const record = requests.get(value.request);
      if (!record || record.request !== value.request) return;
      if (value.state === "error" || value.state === "original") record.active = false;
      paint(record, value.state === "error");
    },
    stop() {
      stopped = true;
      clearTimeout(timer);
      document.removeEventListener("DOMContentLoaded", start);
      observer.disconnect();
      for (const record of records.values()) record.button.remove();
      records.clear();
      requests.clear();
    }
  };
  if (document.documentElement) start();
  else document.addEventListener("DOMContentLoaded", start, {once:true});
})();
