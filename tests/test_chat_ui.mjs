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
for (const saved of [{}, {response_scope:"all", translate_questions:false}]) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const mode = new Element(); mode.value = "bilingual";
  const status = {provider:"offline", settings:{provider:"offline", source:"en", target:"zh",
    ui_language:"en", workflow:"chat", mode:"bilingual", enabled:true, cache:true, ...saved},
    installed_models:[], cloud_usage_label:""};
  const calls = [];
  vm.runInNewContext(script, {
    window:{TWINTEXT_BOOT:{embedded:false, token:"fixture"}, addEventListener() {}},
    navigator:{language:"en"},
    document:{documentElement:{}, getElementById:element, createElement:() => new Element(),
      querySelectorAll:() => [], querySelector:selector => selector.includes("input") ? mode : element(selector)},
    Option:class {constructor(text, value) {this.text = text; this.value = value;}},
    fetch:async (_url, request) => {
      const call = JSON.parse(request.body); calls.push(call);
      if (call.name === "twintext_set_settings") Object.assign(status.settings, call.arguments);
      return {ok:true, json:async () => status};
    },
    setTimeout, clearTimeout,
  });
  await settle();
  assert.equal(element("response-scope").value, saved.response_scope || "final");
  assert.equal(element("translate-questions").checked, saved.translate_questions ?? true);
  assert.equal(element("response-scope").disabled, false);
  element("workflow").value = "desktop";
  element("workflow").listeners.change();
  assert.equal(element("response-scope").disabled, true);
  assert.equal(element("translate-questions").disabled, true);
  element("workflow").value = "chat";
  element("workflow").listeners.change();
  assert.equal(element("response-scope").disabled, false);
  element("response-scope").value = "all";
  element("translate-questions").checked = false;
  for (const language of ["en", "zh", "ja", "fr", "es"]) {
    element("ui-language").value = language;
    element("ui-language").listeners.change();
    assert.equal(element("response-scope").value, "all", "Localization must preserve selection");
    assert.equal(element("response-scope").options.length, 2);
    assert.ok(element("response-scope").options.every(option => option.text && option.text !== option.value));
  }
  await element("settings-form").listeners.submit({preventDefault() {}});
  const settingsCall = calls.find(call => call.name === "twintext_set_settings");
  assert.equal(settingsCall.arguments.response_scope, "all");
  assert.equal(settingsCall.arguments.translate_questions, false);
}
console.log("Chat settings defaults, saved values, localization and workflow controls passed.");
