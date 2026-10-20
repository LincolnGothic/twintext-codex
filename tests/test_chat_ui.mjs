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
for (const saved of [{}, {response_scope:"all", translate_questions:false,chat_presentation:"floating",follow_codex:true},
  {workflow:"desktop",chat_presentation:"floating"}]) {
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
    setTimeout, clearTimeout, AbortController,
  });
  await settle();
  assert.equal(element("response-scope").value, saved.response_scope || "final");
  assert.equal(element("location").value, saved.workflow === "desktop" ? "desktop" : saved.chat_presentation === "floating" ? "chat-floating" : "chat-inline");
  assert.equal(element("translate-questions").checked, saved.translate_questions ?? true);
  assert.equal(element("follow-codex").checked, saved.follow_codex ?? false);
  assert.equal(element("follow-codex").disabled, !saved.chat_presentation);
  assert.equal(element("response-scope").disabled, saved.workflow === "desktop");
  element("location").value = "desktop";
  element("location").listeners.change();
  assert.equal(element("response-scope").disabled, true);
  assert.equal(element("translate-questions").disabled, true);
  await element("settings-form").listeners.submit({preventDefault() {}});
  assert.equal(status.settings.workflow, "desktop");
  assert.equal(status.settings.chat_presentation, saved.chat_presentation || "inline");
  element("location").value = "chat-floating";
  element("location").listeners.change();
  assert.equal(element("response-scope").disabled, false);
  element("response-scope").value = "all";
  element("translate-questions").checked = false;
  element("follow-codex").checked = true;
  for (const language of ["en", "zh", "ja", "fr", "es"]) {
    element("ui-language").value = language;
    element("ui-language").listeners.change();
    assert.equal(element("response-scope").value, "all", "Localization must preserve selection");
    assert.equal(element("response-scope").options.length, 2);
    assert.equal(element("location").value, "chat-floating");
    assert.equal(element("location").options.length, 3);
    assert.ok(element("location").options.every(option => option.text && option.text !== option.value));
    assert.ok(element("response-scope").options.every(option => option.text && option.text !== option.value));
  }
  await element("settings-form").listeners.submit({preventDefault() {}});
  const settingsCall = calls.filter(call => call.name === "twintext_set_settings").at(-1);
  assert.equal(settingsCall.arguments.workflow, "chat");
  assert.equal(settingsCall.arguments.response_scope, "all");
  assert.equal(settingsCall.arguments.chat_presentation, "floating");
  assert.equal(settingsCall.arguments.translate_questions, false);
  assert.equal(settingsCall.arguments.follow_codex, true);
}
console.log("Chat settings defaults, saved values, localization and workflow controls passed.");
