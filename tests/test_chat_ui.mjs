import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

class Element {
  value = ""; checked = false; hidden = false; disabled = false;
  options = []; listeners = {}; textContent = "";
  classList = {toggle() {}};
  addEventListener(event, listener) { this.listeners[event] = listener; }
  replaceChildren(...items) { this.options = items; }
  add(option) { this.options.push(option); }
  append() {}
  setAttribute() {}
}
const script = readFileSync(new URL("../src/twintext/web/app.js", import.meta.url), "utf8");
const settle = async () => {for (let i = 0; i < 20; ++i) await Promise.resolve();};
const html = readFileSync(new URL("../src/twintext/web/index.html", import.meta.url), "utf8");
const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
for (const id of ["location", "response-scope", "translate-questions", "message-buttons"]) {
  assert.equal(ids.has(id), false, `Retired control ${id} must not be presented`);
}
for (const saved of [{}, {workflow:"desktop",chat_presentation:"inline",message_buttons:false},
  {workflow:"chat",chat_presentation:"floating",message_buttons:false,follow_codex:true}]) {
  const elements = new Map();
  const element = id => {
    assert.ok(ids.has(id), `The page must contain requested control ${id}`);
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const mode = new Element(); mode.value = "bilingual";
  const status = {provider:"offline", settings:{provider:"offline", source:"en", target:"zh",
    ui_language:"en", mode:"bilingual", enabled:true, cache:true, ...saved}, installed_models:[]};
  const calls = [];
  vm.runInNewContext(script, {
    window:{TWINTEXT_BOOT:{embedded:false, token:"fixture"}, addEventListener() {}},
    navigator:{language:"en"},
    document:{documentElement:{}, getElementById:element, createElement:() => new Element(),
      querySelectorAll:() => [], querySelector:selector => selector.includes("input") ? mode : new Element()},
    Option:class {constructor(text, value) {this.text = text; this.value = value;}},
    fetch:async (_url, request) => {
      const call = JSON.parse(request.body); calls.push(call);
      if (call.name === "twintext_set_settings") Object.assign(status.settings, call.arguments);
      return {ok:true, json:async () => status};
    },
    setTimeout, clearTimeout, AbortController,
  });
  await settle();
  assert.equal(element("target").value, "zh");
  assert.equal(element("follow-codex").checked, saved.follow_codex ?? false);
  element("session-cache").checked = true;
  element("follow-codex").checked = true;
  for (const language of ["en", "zh", "ja", "fr", "es"]) {
    element("ui-language").value = language;
    element("ui-language").listeners.change();
    assert.equal(element("target").value, "zh", "Localization must preserve translation target");
    assert.equal(element("provider").value, "offline");
  }
  await element("settings-form").listeners.submit({preventDefault() {}});
  const savedCall = calls.filter(call => call.name === "twintext_set_settings").at(-1);
  assert.deepEqual(JSON.parse(JSON.stringify(savedCall.arguments)), {
    provider:"offline",follow_codex:true,target:"zh",source:"en",mode:"bilingual",ui_language:"es",
    enabled:true,cache:true,cache_lifetime:"session"
  });
  assert.equal(calls.filter(call => call.name === "twintext_translate").length, 0);
  element("cache").checked = false;
  element("cache").listeners.change();
  assert.equal(element("session-cache").disabled, true);
}
console.log("Manual reader settings: no retired methods, preserved preferences, localization and no automatic translation passed.");
