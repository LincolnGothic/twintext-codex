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
  append(...items) { this.options.push(...items); }
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
let fetchSignal;
const windowListeners = {};
const response = value => ({ok:true, json:async () => value});
const context = {
  window:{TWINTEXT_BOOT:{embedded:false,token:"fixture"},addEventListener(name, listener) {windowListeners[name] = listener;}},
  navigator:{language:"en"},
  document:{documentElement:{},getElementById:element,createElement:() => new Element(),
    querySelectorAll:() => [],querySelector:selector => selector.includes("input") ? mode : element(selector)},
  Option:class {constructor(text,value) {this.text=text; this.value=value;}},
  fetch:async (_url, request) => {
    fetchSignal = request.signal;
    const call = JSON.parse(request.body);
    if (call.name === "twintext_translate")
      return new Promise(resolve => {resolveTranslation = resolve;});
    return response(status);
  },
  setTimeout,clearTimeout,AbortController,
};
vm.runInNewContext(readFileSync(new URL("../src/twintext/web/app.js", import.meta.url), "utf8"), context);
const settle = async () => {for (let i=0;i<20;++i) await Promise.resolve();};
await settle();
element("input").value = "Hello";
assert.equal(element("translate").disabled, false);
element("provider").value = "google-free";
element("provider").listeners.change();
assert.equal(element("offline-controls").hidden, true);
assert.equal(element("azure-controls").hidden, true);
assert.equal(element("google-controls").hidden, false);
assert.equal(element("translate").disabled, true);
status.provider = status.settings.provider = "google-free";
await element("settings-form").listeners.submit({preventDefault() {}});
assert.equal(element("provider").value, "google-free");
element("input").value = "New original answer";
const failed = element("translate").listeners.click();
await settle();
resolveTranslation({ok:false,json:async () => ({error:"Google unavailable"})});
await failed;
assert.equal(element("result").options[0].textContent, "New original answer");
assert.equal(element("input").value, "New original answer");
assert.equal(element("translate").disabled, false);
assert.match(element("notice").textContent, /Google unavailable/);
status.provider = status.settings.provider = "azure";
element("provider").value = "azure";
element("provider").listeners.change();
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
windowListeners.pagehide();
assert.equal(fetchSignal.aborted, true, "Leaving the preview must abort its pending HTTP work");
console.log("Provider UI asynchronous privacy guards passed.");

// Exercise the real embedded bridge: closing a pending tool cancels its request ID.
const embeddedElements = new Map(), messages = [], embeddedListeners = {};
const embeddedElement = id => {
  if (!embeddedElements.has(id)) embeddedElements.set(id, new Element());
  return embeddedElements.get(id);
};
const embeddedWindow = {TWINTEXT_BOOT:{embedded:true,token:"fixture"},
  parent:{postMessage(message) {messages.push(message);}},
  addEventListener(name, listener) {embeddedListeners[name] = listener;}};
vm.runInNewContext(readFileSync(new URL("../src/twintext/web/app.js", import.meta.url), "utf8"), {
  ...context, window:embeddedWindow,
  document:{...context.document,getElementById:embeddedElement,
    querySelector:selector => selector.includes("input") ? mode : embeddedElement(selector)},
});
const respond = (id, result) => embeddedListeners.message({source:embeddedWindow.parent,
  data:{jsonrpc:"2.0",id,result}});
respond(messages.find(m => m.method === "ui/initialize").id, {hostContext:{locale:"en"}});
await settle();
status.settings.host_locale = "en";
respond(messages.find(m => m.method === "tools/call").id, {structuredContent:status});
await settle();
embeddedElement("input").value = "Hello";
const embeddedPending = embeddedElement("translate").listeners.click();
await settle();
const translationCall = messages.find(m => m.params?.name === "twintext_translate");
assert.ok(translationCall);
embeddedListeners.pagehide();
await embeddedPending;
assert.ok(messages.some(m => m.method === "notifications/cancelled" &&
  m.params.requestId === translationCall.id));
console.log("Embedded preview sends request cancellation on close.");
