(() => {
  "use strict";
  const boot = window.TWINTEXT_BOOT;
  const $ = id => document.getElementById(id);
  const translations = {
    en: {tagline:"Offline translation for Codex",local:"On your computer",eyebrow:"TWO LANGUAGES. ONE CONVERSATION.",headline:"Read it your way.",intro:"Keep the original beside its translation, or focus on just the translation.",preferences:"Preferences",target:"Translate into",source:"Source language",display:"Display mode",bilingual:"Bilingual",both:"Original + translation",translated:"Translation only",translationOnly:"A focused reading view",original:"Original",originalOnly:"Pause translation",uiLanguage:"Plugin display language",followHint:"Automatic follows Codex's language in an embedded panel, or your browser's language here.",enabled:"Enable Translate buttons",cache:"Remember translations locally",save:"Save preferences",nextReply:"Preferences apply to new replies in chats with TwinText enabled.",preview:"Try a translation",private:"Private by default",inputLabel:"Text to translate",placeholder:"Paste a paragraph or a Markdown reply…",preserve:"Code, paths, and links stay intact.",translate:"Translate",empty:"Your translation appears here.",copy:"Copy displayed text",models:"Language pack",noFees:"No API fees",modelInfo:"English, Chinese, Japanese, French, and Spanish. Download once, then translate offline.",install:"Download the five-language pack",clearCache:"Clear remembered translations",footer:"Built for quieter, clearer reading.",auto:"Detect automatically",follow:"Automatic · follow host language",en:"English",zh:"Chinese",ja:"Japanese",fr:"French",es:"Spanish",saved:"Preferences saved.",working:"Translating…",downloading:"Downloading models…",installed:"Language pack ready.",modelCount:"{count} of 8 starter models installed",missing:"Download the language pack to get started.",copied:"Copied.",cleared:"Remembered translations cleared.",pasteFirst:"Add some text first.",route:"Translation route",ready:"All five languages are ready.",copyFailed:"Select the displayed text and copy it manually."},
    zh: {tagline:"Codex 离线翻译",local:"在本机运行",eyebrow:"两种语言，同一段对话。",headline:"用你喜欢的方式阅读。",intro:"对照原文与译文，或专注于译文。",preferences:"偏好设置",target:"翻译为",source:"原文语言",display:"显示模式",bilingual:"双语对照",both:"原文 + 译文",translated:"仅译文",translationOnly:"专注阅读译文",original:"原文",originalOnly:"暂停翻译",uiLanguage:"插件界面语言",followHint:"自动模式在内嵌面板中跟随 Codex 的语言；在此页面跟随浏览器的语言。",enabled:"启用 Translate 按钮",cache:"在本机保存翻译缓存",save:"保存设置",nextReply:"设置适用于已启用 TwinText 的聊天中的新回复。",preview:"试一试翻译",private:"默认保护隐私",inputLabel:"待翻译文本",placeholder:"粘贴段落或 Markdown 回复…",preserve:"保留代码、路径和链接。",translate:"翻译",empty:"译文将在这里显示。",copy:"复制显示的文本",models:"语言包",noFees:"无需 API 费用",modelInfo:"英语、中文、日语、法语和西班牙语。下载一次，即可离线翻译。",install:"下载五种语言的语言包",clearCache:"清除翻译缓存",footer:"让阅读更轻松、更清晰。",auto:"自动检测",follow:"自动 · 跟随主程序语言",en:"英语",zh:"中文",ja:"日语",fr:"法语",es:"西班牙语",saved:"设置已保存。",working:"正在翻译…",downloading:"正在下载模型…",installed:"语言包已就绪。",modelCount:"已安装 {count}/8 个初始模型",missing:"请先下载语言包。",copied:"已复制。",cleared:"翻译缓存已清除。",pasteFirst:"请先添加文本。",route:"翻译路径",ready:"五种语言均已就绪。",copyFailed:"请选中显示的文本并手动复制。"},
    ja: {tagline:"Codex のオフライン翻訳",local:"このコンピューターで実行",eyebrow:"二つの言語、一つの会話。",headline:"自分に合った読み方で。",intro:"原文と訳文を見比べることも、訳文だけに集中することもできます。",preferences:"設定",target:"翻訳先の言語",source:"原文の言語",display:"表示モード",bilingual:"二言語表示",both:"原文 + 訳文",translated:"訳文のみ",translationOnly:"訳文に集中",original:"原文",originalOnly:"翻訳を一時停止",uiLanguage:"プラグインの表示言語",followHint:"自動設定では、埋め込みパネルは Codex の言語、このページはブラウザーの言語に従います。",enabled:"Translate ボタンを有効化",cache:"翻訳をローカルに保存",save:"設定を保存",nextReply:"設定は TwinText を有効にしたチャットの新しい返信に適用されます。",preview:"翻訳を試す",private:"プライバシーを優先",inputLabel:"翻訳するテキスト",placeholder:"文章や Markdown の返信を貼り付け…",preserve:"コード、パス、リンクを保持します。",translate:"翻訳",empty:"ここに翻訳が表示されます。",copy:"表示テキストをコピー",models:"言語パック",noFees:"API 料金なし",modelInfo:"英語、中国語、日本語、フランス語、スペイン語。一度ダウンロードすれば、オフラインで翻訳できます。",install:"5 言語のパックをダウンロード",clearCache:"保存した翻訳を消去",footer:"読みやすく、わかりやすく。",auto:"自動検出",follow:"自動 · ホストの言語に従う",en:"英語",zh:"中国語",ja:"日本語",fr:"フランス語",es:"スペイン語",saved:"設定を保存しました。",working:"翻訳中…",downloading:"モデルをダウンロード中…",installed:"言語パックの準備ができました。",modelCount:"初期モデル {count}/8 個をインストール済み",missing:"まず言語パックをダウンロードしてください。",copied:"コピーしました。",cleared:"保存した翻訳を消去しました。",pasteFirst:"テキストを入力してください。",route:"翻訳経路",ready:"5 言語すべて利用できます。",copyFailed:"表示テキストを選択して手動でコピーしてください。"},
    fr: {tagline:"Traduction hors ligne pour Codex",local:"Sur votre ordinateur",eyebrow:"DEUX LANGUES. UNE CONVERSATION.",headline:"Lisez à votre façon.",intro:"Comparez l’original et sa traduction, ou concentrez-vous sur la traduction.",preferences:"Préférences",target:"Traduire en",source:"Langue source",display:"Mode d’affichage",bilingual:"Bilingue",both:"Original + traduction",translated:"Traduction seule",translationOnly:"Une lecture ciblée",original:"Original",originalOnly:"Suspendre la traduction",uiLanguage:"Langue du plugin",followHint:"Le mode automatique suit la langue de Codex dans le panneau intégré, ou celle de votre navigateur ici.",enabled:"Activer les boutons Translate",cache:"Mémoriser les traductions localement",save:"Enregistrer",nextReply:"Ces préférences s’appliquent aux nouvelles réponses des conversations où TwinText est activé.",preview:"Essayer une traduction",private:"Confidentiel par défaut",inputLabel:"Texte à traduire",placeholder:"Collez un paragraphe ou une réponse Markdown…",preserve:"Le code, les chemins et les liens sont préservés.",translate:"Traduire",empty:"Votre traduction apparaîtra ici.",copy:"Copier le texte affiché",models:"Pack de langues",noFees:"Aucun frais d’API",modelInfo:"Anglais, chinois, japonais, français et espagnol. Téléchargez une fois, puis traduisez hors ligne.",install:"Télécharger le pack de cinq langues",clearCache:"Effacer les traductions mémorisées",footer:"Pour une lecture plus sereine et plus claire.",auto:"Détection automatique",follow:"Automatique · suivre la langue de l’hôte",en:"Anglais",zh:"Chinois",ja:"Japonais",fr:"Français",es:"Espagnol",saved:"Préférences enregistrées.",working:"Traduction…",downloading:"Téléchargement des modèles…",installed:"Pack de langues prêt.",modelCount:"{count} modèles sur 8 installés",missing:"Téléchargez le pack de langues pour commencer.",copied:"Copié.",cleared:"Traductions mémorisées effacées.",pasteFirst:"Ajoutez d’abord du texte.",route:"Parcours de traduction",ready:"Les cinq langues sont prêtes.",copyFailed:"Sélectionnez le texte affiché et copiez-le manuellement."},
    es: {tagline:"Traducción sin conexión para Codex",local:"En tu ordenador",eyebrow:"DOS IDIOMAS. UNA CONVERSACIÓN.",headline:"Lee a tu manera.",intro:"Compara el original y su traducción, o céntrate solo en la traducción.",preferences:"Preferencias",target:"Traducir al",source:"Idioma de origen",display:"Modo de visualización",bilingual:"Bilingüe",both:"Original + traducción",translated:"Solo traducción",translationOnly:"Una lectura centrada",original:"Original",originalOnly:"Pausar la traducción",uiLanguage:"Idioma del complemento",followHint:"El modo automático sigue el idioma de Codex en un panel integrado, o el de tu navegador aquí.",enabled:"Activar los botones Translate",cache:"Guardar traducciones localmente",save:"Guardar preferencias",nextReply:"Estas preferencias se aplican a las nuevas respuestas de los chats con TwinText activado.",preview:"Probar una traducción",private:"Privado por defecto",inputLabel:"Texto para traducir",placeholder:"Pega un párrafo o una respuesta Markdown…",preserve:"El código, las rutas y los enlaces se conservan.",translate:"Traducir",empty:"Tu traducción aparecerá aquí.",copy:"Copiar el texto mostrado",models:"Paquete de idiomas",noFees:"Sin costes de API",modelInfo:"Inglés, chino, japonés, francés y español. Descárgalo una vez y traduce sin conexión.",install:"Descargar el paquete de cinco idiomas",clearCache:"Borrar traducciones guardadas",footer:"Para una lectura más tranquila y clara.",auto:"Detectar automáticamente",follow:"Automático · seguir el idioma del anfitrión",en:"Inglés",zh:"Chino",ja:"Japonés",fr:"Francés",es:"Español",saved:"Preferencias guardadas.",working:"Traduciendo…",downloading:"Descargando modelos…",installed:"Paquete de idiomas listo.",modelCount:"{count} de 8 modelos instalados",missing:"Descarga el paquete de idiomas para empezar.",copied:"Copiado.",cleared:"Traducciones guardadas borradas.",pasteFirst:"Añade texto primero.",route:"Ruta de traducción",ready:"Los cinco idiomas están listos.",copyFailed:"Selecciona el texto mostrado y cópialo manualmente."}
  };
  const desktopWords = {"en": {"openDesktop": "Open floating reader", "desktopOpened": "Floating reader opened.", "nextReply": "Click a reply’s Translate button, or paste text in the reader."}, "zh": {"openDesktop": "打开浮动阅读窗口", "desktopOpened": "已打开浮动阅读窗口。", "nextReply": "点击回复下的 Translate 按钮，或在阅读器中粘贴文本。"}, "ja": {"openDesktop": "フローティングリーダーを開く", "desktopOpened": "リーダーを開きました。", "nextReply": "返信の Translate ボタン、またはリーダーへの貼り付けを使用します。"}, "fr": {"openDesktop": "Ouvrir le lecteur flottant", "desktopOpened": "Lecteur flottant ouvert.", "nextReply": "Cliquez sur Translate sous une réponse ou collez du texte dans le lecteur."}, "es": {"openDesktop": "Abrir el lector flotante", "desktopOpened": "Lector flotante abierto.", "nextReply": "Pulsa Translate en una respuesta o pega texto en el lector."}};
  for (const [code, words] of Object.entries(desktopWords)) Object.assign(translations[code], words);
  const providerWords = {
    en: {provider:"Translation provider",googleFree:"Google Free (experimental)","zh-TW":"Chinese (Traditional)",googleNotice:"Uses a keyless interface not officially supported by Google Cloud. It may be rate limited, fail or change; availability, translation quality and free quota are not guaranteed. Text to translate is sent to Google."},
    zh: {provider:"翻译引擎",googleFree:"Google 免费翻译（实验性）","zh-TW":"中文（繁体）",googleNotice:"使用非 Google Cloud 正式支持的免 Key 接口，可能限流、失效或变更；不保证可用性、翻译质量或免费额度。待翻译文本会发送至 Google。"},
    ja: {provider:"翻訳エンジン",googleFree:"Google 無料翻訳（試験的）","zh-TW":"中国語（繁体字）",googleNotice:"Google Cloud が正式にサポートしないキー不要のインターフェースを使用します。制限、停止、変更の可能性があり、可用性、翻訳品質、無料枠は保証されません。翻訳するテキストは Google に送信されます。"},
    fr: {provider:"Moteur de traduction",googleFree:"Google gratuit (expérimental)","zh-TW":"Chinois (traditionnel)",googleNotice:"Interface sans clé non officiellement prise en charge par Google Cloud : elle peut être limitée, indisponible ou modifiée. Disponibilité, qualité et quota gratuit non garantis. Le texte à traduire est envoyé à Google."},
    es: {provider:"Motor de traducción",googleFree:"Google gratis (experimental)","zh-TW":"Chino (tradicional)",googleNotice:"Interfaz sin clave sin soporte oficial de Google Cloud. Puede limitarse, fallar o cambiar; no se garantizan disponibilidad, calidad ni cuota gratuita. El texto a traducir se envía a Google."}
  };
  for (const [code, words] of Object.entries(providerWords)) Object.assign(translations[code], words);
  const followWords = {
    en:{followCodex:"Follow Codex window",followCodexHint:"Windows and X11/XWayland. The floating button follows Codex; click to show or hide translation. Native Wayland uses manual placement."},
    zh:{followCodex:"跟随 Codex 窗口",followCodexHint:"支持 Windows 和 X11/XWayland。浮动按钮跟随 Codex，点击可显示或隐藏翻译。原生 Wayland 需手动放置。"},
    ja:{followCodex:"Codex ウィンドウに追従",followCodexHint:"Windows と X11/XWayland に対応。ボタンをクリックして翻訳を表示・非表示。ネイティブ Wayland では手動で配置します。"},
    fr:{followCodex:"Suivre la fenêtre Codex",followCodexHint:"Windows et X11/XWayland. Le bouton suit Codex ; cliquez pour afficher ou masquer la traduction. Placement manuel sous Wayland natif."},
    es:{followCodex:"Seguir la ventana de Codex",followCodexHint:"Windows y X11/XWayland. El botón sigue a Codex; haga clic para mostrar u ocultar la traducción. Wayland nativo requiere colocación manual."}
  };
  for (const [code, words] of Object.entries(followWords)) Object.assign(translations[code], words);
  const messageWords = {
    en:{manualReaderHint:"Click Translate / Original on a completed Codex reply. Windows requires Open Codex with TwinText.cmd; Linux uses manual Paste. Codex UI changes may affect buttons.",sessionCache:"Only remember translations until TwinText exits",sessionCacheHint:"Fragments and reader translations stay in memory. Existing disk cache is ignored; Clear cache removes it. Originals and settings are kept."},
    zh:{manualReaderHint:"点击 Codex 已完成回复下的 Translate / Original。Windows 需使用 Open Codex with TwinText.cmd；Linux 可手动粘贴。Codex 界面变更可能影响按钮。",sessionCache:"仅本次运行缓存译文（退出后释放）",sessionCacheHint:"翻译片段和阅读器译文仅存于内存，忽略旧磁盘缓存。点击“清除缓存”可清除旧译文，保留原文和设置。"},
    ja:{manualReaderHint:"完了した返信の Translate / Original をクリック。Windows は Open Codex with TwinText.cmd、Linux は手動貼り付けを使用します。Codex の UI 変更でボタンに影響する場合があります。",sessionCache:"TwinText 終了まで訳文を記憶",sessionCacheHint:"断片とリーダー訳文はメモリ内のみ。既存のディスクキャッシュは無視し、キャッシュ消去で削除。原文と設定は保持します。"},
    fr:{manualReaderHint:"Cliquez sur Translate / Original sous une réponse terminée. Windows nécessite Open Codex with TwinText.cmd ; Linux utilise le collage manuel. Les changements de Codex peuvent affecter les boutons.",sessionCache:"Garder les traductions jusqu’à la fermeture de TwinText",sessionCacheHint:"Fragments et traductions du lecteur en mémoire. Le cache disque est ignoré ; Effacer le cache le supprime. Originaux et préférences conservés."},
    es:{manualReaderHint:"Pulsa Translate / Original bajo una respuesta completa. Windows requiere Open Codex with TwinText.cmd; Linux usa pegado manual. Los cambios de Codex pueden afectar los botones.",sessionCache:"Recordar traducciones solo hasta cerrar TwinText",sessionCacheHint:"Fragmentos y traducciones del lector solo en memoria. Se ignora la caché en disco; Borrar caché la elimina. Se conservan originales y ajustes."}
  };
  for (const [code, words] of Object.entries(messageWords)) Object.assign(translations[code], words);
  let locale = "en", hostLocale = navigator.language, lastResult = null, lastStatus = null;
  let translationBusy = false, modelsBusy = false;
  let bridgeId = 0;
  const pending = new Map();
  const pageAbort = new AbortController();
  const cancelRequest = id => window.parent.postMessage({jsonrpc:"2.0",method:"notifications/cancelled",params:{requestId:id}}, "*");
  window.addEventListener("pagehide", () => {
    pageAbort.abort();
    if (boot.embedded) for (const [id, item] of pending) {
      if (item.method === "tools/call") cancelRequest(id);
      clearTimeout(item.timer); item.reject(new Error("Translation cancelled."));
    }
    pending.clear();
  });
  const t = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replace(`{${name}}`, value), translations[locale][key] ?? translations.en[key] ?? key);
  const baseLocale = code => { const base = String(code || "en").toLowerCase().split(/[-_]/)[0]; return translations[base] ? base : "en"; };
  function notify(message, error = false) { $("notice").textContent = message; $("notice").classList.toggle("error", error); $("notice").hidden = false; }
  function request(method, params = {}, timeout = 60000) {
    const id = ++bridgeId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { if (method === "tools/call") cancelRequest(id); pending.delete(id); reject(new Error("Codex did not respond. Try the standalone settings page.")); }, timeout);
      pending.set(id, {resolve, reject, timer, method});
      window.parent.postMessage({jsonrpc:"2.0", id, method, params}, "*");
    });
  }
  window.addEventListener("message", event => {
    if (!boot.embedded || event.source !== window.parent || !event.data || event.data.jsonrpc !== "2.0") return;
    const message = event.data;
    if (pending.has(message.id)) {
      const item = pending.get(message.id); pending.delete(message.id); clearTimeout(item.timer);
      message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result);
    } else if (message.method === "ui/notifications/host-context-changed") {
      hostLocale = message.params?.locale ?? message.params?.hostContext?.locale ?? hostLocale;
      localize();
      tool("twintext_set_settings", {host_locale:baseLocale(hostLocale)}).catch(() => {});
    }
  });
  async function tool(name, args = {}) {
    if (boot.embedded) {
      const result = await request("tools/call", {name, arguments:args}, name === "twintext_install_models" ? 3600000 : 120000);
      if (result.isError) throw new Error(result.content?.map(item => item.text || "").join("\n") || "TwinText tool failed.");
      return result.structuredContent ?? JSON.parse(result.content[0].text);
    }
    const response = await fetch("/api/tool", {method:"POST", signal:pageAbort.signal, headers:{"Content-Type":"application/json","X-TwinText-Token":boot.token}, body:JSON.stringify({name, arguments:args})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "TwinText request failed.");
    return result;
  }
  function selectOptions(element, automatic) {
    const previous = element.value;
    element.replaceChildren();
    const codes = Object.keys(translations);
    if (element !== $("ui-language") && $("provider").value === "google-free") codes.push("zh-TW");
    const entries = automatic ? [["auto", t(automatic)], ...codes.map(code => [code, t(code)])] : codes.map(code => [code, t(code)]);
    for (const [value, label] of entries) { const option = new Option(label, value); element.add(option); }
    if ([...element.options].some(option => option.value === previous)) element.value = previous;
  }
  function localize() {
    const chosen = $("ui-language").value || "auto";
    locale = chosen === "auto" ? baseLocale(hostLocale) : baseLocale(chosen);
    document.documentElement.lang = locale;
    document.title = `TwinText · ${t("tagline")}`;
    for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
    for (const element of document.querySelectorAll("[data-placeholder]")) element.placeholder = t(element.dataset.placeholder);
    selectOptions($("source"), "auto"); selectOptions($("target")); selectOptions($("ui-language"), "follow");
    cacheControls();
    $("ui-language").value = chosen;
    if (lastStatus) showModels(lastStatus);
    if (lastResult) renderResult();
    if (boot.embedded) window.parent.postMessage({jsonrpc:"2.0",method:"ui/notifications/size-changed",params:{height:document.documentElement.scrollHeight}}, "*");
  }
  function cacheControls() {
    $("session-cache").disabled = !$("cache").checked;
  }
  function showModels(status) {
    const azure = $("provider").value === "azure";
    const google = $("provider").value === "google-free";
    for (const option of $("provider").options) if (option.value === "google-free") option.textContent = t("googleFree");
    const unsaved = $("provider").value !== (status.provider || status.settings.provider || "offline");
    $("provider-hint").hidden = !unsaved;
    $("translate").disabled = unsaved || translationBusy;
    $("install").disabled = unsaved || modelsBusy;
    $("offline-controls").hidden = azure || google;
    $("azure-controls").hidden = !azure;
    $("google-controls").hidden = !google;
    $("azure-status").textContent = status.azure_configured ? "Credentials configured" : "Credentials not configured";
    $("cloud-usage").textContent = status.cloud_usage_label || "";
    document.querySelector('[data-i18n="local"]').textContent = status.provider === "google-free" ? t("googleFree") : status.provider === "azure" ? "Microsoft Azure Translator" : t("local");
    document.querySelector('[data-i18n="tagline"]').textContent = status.provider === "google-free" ? t("googleFree") : status.provider === "azure" ? "Azure translation for Codex" : t("tagline");
    const models = status.installed_models || [], count = models.length;
    $("model-status").textContent = status.engine_error || (count >= 8 ? t("ready") : t("modelCount", {count}));
    $("model-list").replaceChildren();
    for (const model of models) { const chip = document.createElement("span"); chip.className = "model-chip"; chip.textContent = `${t(model.source)} → ${t(model.target)}`; $("model-list").append(chip); }
    $("install").hidden = count >= 8;
  }
  function mode() { return document.querySelector("input[name=mode]:checked").value; }
  function renderResult() {
    if (!lastResult) return;
    $("result").replaceChildren();
    const displayMode = mode();
    for (const block of lastResult.blocks) {
      if (!block.original.trim()) continue;
      const append = (text, kind) => { const element = document.createElement("div"); element.className = `result-block ${kind}`; element.textContent = text; $("result").append(element); };
      if (block.protected) append(block.original, "protected");
      else if (displayMode === "original") append(block.original, "");
      else if (displayMode === "translated") append(block.translation, "translation");
      else { append(block.original, "original"); if (block.original !== block.translation) append(block.translation, "translation"); }
    }
    $("route").textContent = lastResult.route.length > 1 ? `${t("route")}: ${lastResult.route.map(code => t(code)).join(" → ")}` : "";
    $("copy").hidden = false;
  }
  function displayText() {
    return lastResult.blocks.map(block => mode() === "original" ? block.original : mode() === "bilingual" && block.original !== block.translation ? block.original.replace(/\n+$/, "") + "\n\n" + block.translation : block.translation).join("");
  }
  $("open-desktop").addEventListener("click", async () => {
    try { await tool("twintext_open_desktop"); notify(t("desktopOpened")); }
    catch (error) { notify(error.message, true); }
  });
  $("ui-language").addEventListener("change", localize);
  $("cache").addEventListener("change", cacheControls);
  $("provider").addEventListener("change", () => { localize(); });
  document.querySelectorAll("input[name=mode]").forEach(input => input.addEventListener("change", renderResult));
  $("settings-form").addEventListener("submit", async event => {
    event.preventDefault(); $("save").disabled = true;
    try {
      lastStatus = await tool("twintext_set_settings", {provider:$("provider").value,follow_codex:$("follow-codex").checked,target:$("target").value,source:$("source").value,mode:mode(),ui_language:$("ui-language").value,enabled:$("enabled").checked,cache:$("cache").checked,cache_lifetime:$("session-cache").checked ? "session" : "disk"});
      localize(); notify(t("saved"));
    } catch (error) { notify(error.message, true); } finally { $("save").disabled = false; }
  });
  $("translate").addEventListener("click", async () => {
    if (!$("input").value.trim()) { notify(t("pasteFirst"), true); return; }
    const original = $("input").value;
    lastResult = {blocks:[{original,translation:original,protected:false}],route:[]};
    renderResult();
    translationBusy = true;
    $("translate").disabled = true; $("translate").textContent = t("working"); $("input").setAttribute("aria-busy", "true");
    try {
      // Always obtain the translation once; display modes then switch without inference.
      lastResult = await tool("twintext_translate", {text:$("input").value,source:$("source").value,target:$("target").value,mode:"translated"});
      renderResult(); $("notice").hidden = true;
      lastStatus = await tool("twintext_status"); showModels(lastStatus);
    } catch (error) { notify(error.message, true); } finally { translationBusy = false; if (lastStatus) showModels(lastStatus); $("translate").textContent = t("translate"); $("input").setAttribute("aria-busy", "false"); }
  });
  $("copy").addEventListener("click", async () => { try { await navigator.clipboard.writeText(displayText()); notify(t("copied")); } catch { notify(t("copyFailed"), true); } });
  $("clear-cache").addEventListener("click", async () => { try { await tool("twintext_clear_cache"); notify(t("cleared")); } catch (error) { notify(error.message, true); } });
  $("install").addEventListener("click", async () => {
    modelsBusy = true;
    $("install").disabled = true; $("install").textContent = t("downloading");
    try { await tool("twintext_install_models"); lastStatus = await tool("twintext_status"); showModels(lastStatus); notify(t("installed")); }
    catch (error) { notify(error.message, true); }
    finally { modelsBusy = false; if (lastStatus) showModels(lastStatus); $("install").textContent = t("install"); }
  });
  async function start() {
    localize();
    try {
      if (boot.embedded) {
        const initialization = await request("ui/initialize", {appInfo:{name:"TwinText",version:"0.10.0"},appCapabilities:{},protocolVersion:"2026-01-26"});
        hostLocale = initialization.hostContext?.locale || hostLocale;
        window.parent.postMessage({jsonrpc:"2.0",method:"ui/notifications/initialized"}, "*");
      }
      lastStatus = await tool("twintext_status");
      if (boot.embedded && lastStatus.settings.host_locale !== baseLocale(hostLocale)) {
        lastStatus = await tool("twintext_set_settings", {host_locale:baseLocale(hostLocale)});
      }
      const settings = lastStatus.settings;
      $("provider").value = settings.provider || "offline";
      localize();
      $("follow-codex").checked = settings.follow_codex ?? false;
      $("target").value = settings.target; $("source").value = settings.source; $("ui-language").value = settings.ui_language;
      document.querySelector(`input[name=mode][value=${settings.mode}]`).checked = true;
      $("enabled").checked = settings.enabled; $("cache").checked = settings.cache;
      $("session-cache").checked = settings.cache_lifetime === "session";
      localize();
    } catch (error) { notify(error.message, true); }
  }
  start();
})();

