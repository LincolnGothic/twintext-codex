import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

// Minimal DOM fixture executes the real script/handlers; no browser or network.
class Element {
  value = ""; checked = true; hidden = false; disabled = false;
  options = []; listeners = {}; textContent = "";
  classList = {toggle() {}};
  addEventListener(event, listener) { this.listeners[event] = listener; }
  replaceChildren(...items) { this.options = items; }
  add(option) { this.options.push(option); }
  append() {}
  setAttribute() {}
}
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
const mode = new Element(); mode.value = "translated";
const status = {provider:"azure", settings:{provider:"azure",source:"en",target:"fr",
  ui_language:"en",workflow:"chat",mode:"translated",enabled:true,cache:true},
  azure_configured:true, cloud_usage_label:"This month: 1 requests · 5 characters"};
let resolveTranslation;
const response = value => ({ok:true, json:async () => value});
const context = {
  window:{TWINTEXT_BOOT:{embedded:false,token:"fixture"},addEventListener() {}},
  navigator:{language:"en"},
  document:{documentElement:{},getElementById:element,createElement:() => new Element(),
    querySelectorAll:() => [],querySelector:selector => selector.includes("input") ? mode : element(selector)},
  Option:class {constructor(text,value) {this.text=text; this.value=value;}},
  fetch:async (_url, request) => {
    const call = JSON.parse(request.body);
    if (call.name === "twintext_translate")
      return new Promise(resolve => {resolveTranslation = resolve;});
    return response(status);
  },
  setTimeout,clearTimeout,
};
vm.runInNewContext(readFileSync(new URL("../src/twintext/web/app.js", import.meta.url), "utf8"), context);
const settle = async () => {for (let i=0;i<20;++i) await Promise.resolve();};
await settle();
element("input").value = "Hello";
assert.equal(element("translate").disabled, false);
const pending = element("translate").listeners.click();
await settle();
assert.equal(element("translate").disabled, true);
element("provider").value = "offline";
element("provider").listeners.change();
assert.equal(element("translate").disabled, true);
resolveTranslation(response({blocks:[],route:["en","fr"]}));
await pending;
assert.equal(element("translate").disabled, true, "Unsaved provider must stay blocked after an in-flight request");
element("provider").value = "azure";
element("provider").listeners.change();
assert.equal(element("translate").disabled, false);
const another = element("translate").listeners.click();
await settle();
element("provider").listeners.change();
assert.equal(element("translate").disabled, true, "Provider controls must not re-enable a busy translation");
resolveTranslation(response({blocks:[],route:["en","fr"]}));
await another;
assert.equal(element("translate").disabled, false);
console.log("Provider UI asynchronous privacy guards passed.");
