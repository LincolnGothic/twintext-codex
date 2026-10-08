"""Qt floating reader. Translation and reply selection stay outside Codex context."""

import queue
import sqlite3
import threading

from PySide6.QtCore import QEvent, QLocale, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from twintext.bridge import Inbox, desktop_lock
from twintext.cache import Cache
from twintext.config import (
    LANGUAGES,
    MODES,
    WORKFLOWS,
    TwinTextError,
    load_settings,
    update_settings,
)
from twintext.service import Service

WORDS = {
    "en": {
        "drag": "Drag to move",
        "expand": "Open TwinText",
        "clear_cache": "Clear cache",
        "cache_cleared": "Translation cache cleared",
        "cache_hint": (
            "Reuses up to 10,000 translated fragments; no timed expiry. Turnin"
            "g this off keeps existing entries. Clear cache deletes them."
        ),
        "inbox_hint": "Deletes received replies, separately from the translation cache.",
        "offline": "Offline · on your computer",
        "settings": "Settings",
        "collapse": "Collapse",
        "source": "Source language",
        "target": "Translate into",
        "mode": "Display mode",
        "ui": "Interface language",
        "auto": "Automatic",
        "bilingual": "Bilingual",
        "translated": "Translation only",
        "original": "Original",
        "enabled": "Receive Codex replies",
        "cache": "Remember translations locally",
        "start": "Open floating button on new replies",
        "pin": "Keep above other windows",
        "paste": "Paste text",
        "translate": "Translate",
        "copy": "Copy displayed text",
        "clear": "Clear received replies",
        "quit": "Quit",
        "empty": "Completed Codex replies appear here. You can also paste text to translate.",
        "waiting": "Waiting for a completed reply",
        "working": "Translating locally…",
        "ready": "Ready",
        "paused": "Automatic capture is paused",
        "manual": "Pasted text",
        "placeholder": "Paste a paragraph or Markdown…",
        "error": "Translation failed",
        "codex": "Codex reply",
        "locale_hint": (
            "Automatic uses the last Codex settings-panel language, or your system language."
        ),
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "fr": "French",
        "es": "Spanish",
    },
    "zh": {
        "drag": "拖动以移动",
        "expand": "打开 TwinText",
        "clear_cache": "清除缓存",
        "cache_cleared": "翻译缓存已清除",
        "cache_hint": (
            "最多保存 10,000 条翻译片段，无定时过期。关闭后保留已有记录；“清除缓存”会删除它们。"
        ),
        "inbox_hint": "删除接收到的回复，不清除翻译缓存。",
        "offline": "离线 · 在本机运行",
        "settings": "设置",
        "collapse": "收起",
        "source": "原文语言",
        "target": "翻译为",
        "mode": "显示模式",
        "ui": "界面语言",
        "auto": "自动",
        "bilingual": "双语对照",
        "translated": "仅译文",
        "original": "原文",
        "enabled": "接收 Codex 回复",
        "cache": "在本机保存翻译缓存",
        "start": "收到新回复时打开浮动按钮",
        "pin": "保持窗口置顶",
        "paste": "粘贴文本",
        "translate": "翻译",
        "copy": "复制显示的文本",
        "clear": "清除收到的回复",
        "quit": "退出",
        "empty": "完整的 Codex 回复将显示在这里。也可以粘贴文本翻译。",
        "waiting": "等待完整回复",
        "working": "正在本机翻译…",
        "ready": "就绪",
        "paused": "已暂停自动接收",
        "manual": "粘贴的文本",
        "placeholder": "粘贴段落或 Markdown…",
        "error": "翻译失败",
        "codex": "Codex 回复",
        "locale_hint": "自动模式使用上次 Codex 设置面板的语言；若不可用，则使用系统语言。",
        "en": "英语",
        "zh": "中文",
        "ja": "日语",
        "fr": "法语",
        "es": "西班牙语",
    },
    "ja": {
        "drag": "ドラッグして移動",
        "expand": "TwinText を開く",
        "clear_cache": "キャッシュを消去",
        "cache_cleared": "翻訳キャッシュを消去しました",
        "cache_hint": (
            "翻訳の断片を最大10,000件保存します。期限はありません。"
            "無効にしても既存の記録は残ります。消去ボタンで削除できます。"
        ),
        "inbox_hint": "受信した返信を削除します。翻訳キャッシュは残ります。",
        "offline": "オフライン · このコンピューターで実行",
        "settings": "設定",
        "collapse": "折りたたむ",
        "source": "原文の言語",
        "target": "翻訳先",
        "mode": "表示モード",
        "ui": "表示言語",
        "auto": "自動",
        "bilingual": "二言語表示",
        "translated": "訳文のみ",
        "original": "原文",
        "enabled": "Codex の返信を受信",
        "cache": "翻訳をローカルに保存",
        "start": "新しい返信でフローティングボタンを開く",
        "pin": "最前面に表示",
        "paste": "テキストを貼り付け",
        "translate": "翻訳",
        "copy": "表示テキストをコピー",
        "clear": "受信した返信を消去",
        "quit": "終了",
        "empty": "完了した Codex の返信がここに表示されます。テキストの貼り付けもできます。",
        "waiting": "返信の完了を待機中",
        "working": "ローカルで翻訳中…",
        "ready": "準備完了",
        "paused": "自動受信を停止中",
        "manual": "貼り付けたテキスト",
        "placeholder": "文章や Markdown を貼り付け…",
        "error": "翻訳に失敗",
        "codex": "Codex の返信",
        "locale_hint": "自動設定は最後の Codex 設定パネルの言語、またはシステム言語に従います。",
        "en": "英語",
        "zh": "中国語",
        "ja": "日本語",
        "fr": "フランス語",
        "es": "スペイン語",
    },
    "fr": {
        "drag": "Glisser pour déplacer",
        "expand": "Ouvrir TwinText",
        "clear_cache": "Vider le cache",
        "cache_cleared": "Cache de traduction vidé",
        "cache_hint": (
            "Réutilise jusqu’à 10 000 fragments, sans expiration. Désactiver c"
            "onserve les entrées existantes. Vider le cache les supprime."
        ),
        "inbox_hint": "Supprime les réponses reçues, séparément du cache de traduction.",
        "offline": "Hors ligne · sur votre ordinateur",
        "settings": "Paramètres",
        "collapse": "Réduire",
        "source": "Langue source",
        "target": "Traduire en",
        "mode": "Affichage",
        "ui": "Langue de l’interface",
        "auto": "Automatique",
        "bilingual": "Bilingue",
        "translated": "Traduction seule",
        "original": "Original",
        "enabled": "Recevoir les réponses de Codex",
        "cache": "Mémoriser les traductions localement",
        "start": "Ouvrir le bouton flottant à chaque nouvelle réponse",
        "pin": "Garder au premier plan",
        "paste": "Coller du texte",
        "translate": "Traduire",
        "copy": "Copier le texte affiché",
        "clear": "Effacer les réponses reçues",
        "quit": "Quitter",
        "empty": (
            "Les réponses terminées de Codex apparaissent ici. Vous pouvez aussi coller du texte."
        ),
        "waiting": "En attente d’une réponse terminée",
        "working": "Traduction locale…",
        "ready": "Prêt",
        "paused": "Réception automatique suspendue",
        "manual": "Texte collé",
        "placeholder": "Collez un paragraphe ou du Markdown…",
        "error": "Échec de la traduction",
        "codex": "Réponse de Codex",
        "locale_hint": (
            "Le mode automatique utilise la dernière langue du panneau Codex, ou celle du système."
        ),
        "en": "Anglais",
        "zh": "Chinois",
        "ja": "Japonais",
        "fr": "Français",
        "es": "Espagnol",
    },
    "es": {
        "drag": "Arrastrar para mover",
        "expand": "Abrir TwinText",
        "clear_cache": "Vaciar caché",
        "cache_cleared": "Caché de traducción vaciada",
        "cache_hint": (
            "Reutiliza hasta 10 000 fragmentos, sin caducidad. Desactivar cons"
            "erva las entradas existentes. Vaciar caché las elimina."
        ),
        "inbox_hint": "Elimina las respuestas recibidas, por separado de la caché de traducción.",
        "offline": "Sin conexión · en tu ordenador",
        "settings": "Ajustes",
        "collapse": "Contraer",
        "source": "Idioma de origen",
        "target": "Traducir al",
        "mode": "Visualización",
        "ui": "Idioma de la interfaz",
        "auto": "Automático",
        "bilingual": "Bilingüe",
        "translated": "Solo traducción",
        "original": "Original",
        "enabled": "Recibir respuestas de Codex",
        "cache": "Guardar traducciones localmente",
        "start": "Abrir el botón flotante con nuevas respuestas",
        "pin": "Mantener encima de otras ventanas",
        "paste": "Pegar texto",
        "translate": "Traducir",
        "copy": "Copiar el texto mostrado",
        "clear": "Borrar respuestas recibidas",
        "quit": "Salir",
        "empty": "Las respuestas completas de Codex aparecen aquí. También puedes pegar texto.",
        "waiting": "Esperando una respuesta completa",
        "working": "Traduciendo localmente…",
        "ready": "Listo",
        "paused": "Recepción automática pausada",
        "manual": "Texto pegado",
        "placeholder": "Pega un párrafo o Markdown…",
        "error": "Error de traducción",
        "codex": "Respuesta de Codex",
        "locale_hint": (
            "El modo automático usa el último idioma del panel de Codex, o el del sistema."
        ),
        "en": "Inglés",
        "zh": "Chino",
        "ja": "Japonés",
        "fr": "Francés",
        "es": "Español",
    },
}


for _language, _labels in {
    "en": ("Translation location", "Floating window", "Codex chat"),
    "zh": ("翻译显示位置", "浮动窗口", "Codex 聊天"),
    "ja": ("翻訳の表示先", "フローティングウィンドウ", "Codex チャット"),
    "fr": ("Emplacement de la traduction", "Fenêtre flottante", "Conversation Codex"),
    "es": ("Ubicación de traducción", "Ventana flotante", "Chat de Codex"),
}.items():
    WORDS[_language].update(dict(zip(("workflow", "desktop", "chat"), _labels, strict=True)))


def display_text(result, mode):
    if mode == "original":
        return result["original"]
    return "".join(
        block["original"].rstrip("\n") + "\n\n" + block["translation"]
        if mode == "bilingual" and block["original"] != block["translation"]
        else block["translation"]
        for block in result["blocks"]
    )


class Translator:
    """One daemon worker owns the model; replace pending work with the latest request."""

    def __init__(self, service=None):
        self.service = service or Service()
        self.jobs = queue.Queue(maxsize=1)
        self.results = queue.SimpleQueue()
        threading.Thread(target=self.run, daemon=True, name="twintext-model").start()

    def submit(self, revision, text, source, target):
        try:
            self.jobs.get_nowait()
        except queue.Empty:
            pass
        self.jobs.put_nowait((revision, text, source, target))

    def run(self):
        while True:
            revision, text, source, target = self.jobs.get()
            try:
                result = self.service.translate(
                    text, source=source, target=target, mode="translated"
                )
                self.results.put((revision, result, None))
            except Exception as exc:
                self.results.put((revision, None, str(exc)))


class Reader(QTextBrowser):
    def loadResource(self, resource_type, name):
        # Replies may contain Markdown images: do not fetch remote or local resources.
        return None


def start_window_move(widget):
    handle = widget.window().windowHandle()
    return handle.startSystemMove() if handle else False


class Header(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            start_window_move(self)


class DragHandle(Header):
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 36)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#9ec8b9"))
        for x in (11, 18):
            for y in (11, 18, 25):
                painter.drawEllipse(x - 2, y - 2, 4, 4)


class ExpandButton(QPushButton):
    """Click opens the reader; a deliberate drag moves the floating control."""

    def mousePressEvent(self, event):
        self.drag_origin = event.globalPosition().toPoint()
        self.dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "drag_origin"):
            distance = (event.globalPosition().toPoint() - self.drag_origin).manhattanLength()
            if not self.dragged and distance >= QApplication.startDragDistance():
                self.dragged = True
                self.setDown(False)
                start_window_move(self)
        if not getattr(self, "dragged", False):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "dragged", False):
            self.setDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class Companion(QWidget):
    def __init__(self, inbox=None, translator=None):
        super().__init__()
        self.inbox = inbox or Inbox()
        self.translator = translator or Translator()
        self.settings = load_settings()
        self.revision = 0
        self.text = ""
        self.last_result = None
        self.rows = []
        self.ids = ()
        self.activation = self.inbox.activation()
        self.status_key = "waiting"
        self.setWindowTitle("TwinText Desktop")
        self.setMinimumSize(420, 440)
        self.resize(570, 680)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 12)
        layout.setSpacing(12)
        header = Header()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        brand = QLabel("TwinText")
        brand.setObjectName("brand")
        brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header_layout.addWidget(brand)
        header_layout.addStretch()
        self.settings_button = QPushButton()
        self.collapse_button = QPushButton("−")
        self.collapse_button.setFixedWidth(36)
        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.collapse_button)
        layout.addWidget(header)
        self.offline = QLabel()
        self.offline.setObjectName("muted")
        layout.addWidget(self.offline)
        self.sessions = QComboBox()
        layout.addWidget(self.sessions)
        self.preferences = QFrame()
        self.preferences.setObjectName("preferences")
        form = QFormLayout(self.preferences)
        self.selects = {}
        self.labels = {}
        for key in ("workflow", "source", "target", "mode", "ui"):
            label = QLabel()
            combo = QComboBox()
            self.labels[key] = label
            self.selects[key] = combo
            form.addRow(label, combo)
        self.checks = {}
        for key in ("enabled", "cache", "start", "pin"):
            box = QCheckBox()
            self.checks[key] = box
            form.addRow(box)
        self.locale_hint = QLabel()
        self.locale_hint.setWordWrap(True)
        self.locale_hint.setObjectName("muted")
        form.addRow(self.locale_hint)
        self.cache_button = QPushButton()
        form.addRow(self.cache_button)
        self.preference_scroll = QScrollArea()
        self.preference_scroll.setWidgetResizable(True)
        self.preference_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preference_scroll.setWidget(self.preferences)
        self.preference_scroll.setMinimumHeight(140)
        self.preference_scroll.setMaximumHeight(360)
        self.preference_scroll.hide()
        layout.addWidget(self.preference_scroll)
        self.reader = Reader()
        self.reader.setOpenLinks(False)
        self.reader.setOpenExternalLinks(False)
        self.reader.setObjectName("reader")
        self.reader.document().setDefaultStyleSheet(
            "pre { background: #e9efed; padding: 10px; } "
            "a { color: #196d5d; } blockquote { color: #536861; }"
        )
        layout.addWidget(self.reader, 1)
        self.editor = QPlainTextEdit()
        self.editor.setMaximumHeight(105)
        self.editor.hide()
        layout.addWidget(self.editor)
        actions = QHBoxLayout()
        self.paste_button = QPushButton()
        self.translate_button = QPushButton()
        self.translate_button.hide()
        self.copy_button = QPushButton()
        self.copy_button.setEnabled(False)
        for button in (self.paste_button, self.translate_button, self.copy_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        footer = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.clear_button = QPushButton()
        self.quit_button = QPushButton()
        footer.addWidget(self.clear_button)
        footer.addWidget(self.quit_button)
        footer.addWidget(QSizeGrip(self))
        layout.addLayout(footer)
        self.orb = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.orb.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.orb.setWindowTitle("TwinText")
        self.orb.installEventFilter(self)
        self.orb.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        orb_layout = QHBoxLayout(self.orb)
        orb_layout.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setObjectName("orbPanel")
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(5, 5, 8, 5)
        panel_layout.setSpacing(0)
        self.orb_handle = DragHandle()
        panel_layout.addWidget(self.orb_handle)
        self.orb_button = ExpandButton("TwinText  ↗")
        self.orb_button.setObjectName("orbExpand")
        self.orb_button.setMinimumSize(116, 36)
        self.orb_button.clicked.connect(self.expand)
        panel_layout.addWidget(self.orb_button)
        self.orb_quit_button = QPushButton("×")
        self.orb_quit_button.setObjectName("orbQuit")
        self.orb_quit_button.setFixedSize(28, 36)
        self.orb_quit_button.clicked.connect(self.quit)
        panel_layout.addWidget(self.orb_quit_button)
        orb_layout.addWidget(panel)
        self.orb.setFixedSize(196, 48)
        self.setStyleSheet(STYLE)
        self.orb.setStyleSheet(STYLE)
        self.localize()
        self.apply_pin()
        self.settings_button.clicked.connect(
            lambda: self.preference_scroll.setVisible(not self.preference_scroll.isVisible())
        )
        self.collapse_button.clicked.connect(self.collapse)
        self.cache_button.clicked.connect(self.clear_cache)
        self.paste_button.clicked.connect(self.paste)
        self.translate_button.clicked.connect(self.translate_manual)
        self.copy_button.clicked.connect(self.copy)
        self.clear_button.clicked.connect(self.clear)
        self.quit_button.clicked.connect(self.quit)
        self.sessions.currentIndexChanged.connect(self.select_reply)
        for combo in self.selects.values():
            combo.currentIndexChanged.connect(self.save_preferences)
        for box in self.checks.values():
            box.toggled.connect(self.save_preferences)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(300)
        self.poll()

    def t(self, key):
        language = self.settings.ui_language
        if language == "auto":
            language = self.settings.host_locale
        if language == "auto":
            language = QLocale.system().name().split("_")[0]
        return WORDS.get(language, WORDS["en"])[key]

    def localize(self):
        for button, key in (
            (self.settings_button, "settings"),
            (self.paste_button, "paste"),
            (self.translate_button, "translate"),
            (self.copy_button, "copy"),
            (self.clear_button, "clear"),
            (self.cache_button, "clear_cache"),
            (self.quit_button, "quit"),
        ):
            button.setText(self.t(key))
        self.offline.setText(self.t("offline"))
        self.locale_hint.setText(self.t("locale_hint"))
        self.editor.setPlaceholderText(self.t("placeholder"))
        self.collapse_button.setToolTip(self.t("collapse"))
        self.orb_handle.setToolTip(self.t("drag"))
        self.orb_handle.setAccessibleName(self.t("drag"))
        self.orb_button.setToolTip(self.t("expand"))
        self.orb_button.setAccessibleName(self.t("expand"))
        self.orb_quit_button.setToolTip(self.t("quit"))
        self.orb_quit_button.setAccessibleName(self.t("quit"))
        self.checks["cache"].setToolTip(self.t("cache_hint"))
        self.clear_button.setToolTip(self.t("inbox_hint"))
        for key, combo in self.selects.items():
            combo.blockSignals(True)
            combo.clear()
            codes = WORKFLOWS if key == "workflow" else MODES if key == "mode" else list(LANGUAGES)
            if key in ("source", "ui"):
                codes = ["auto", *codes]
            for code in codes:
                combo.addItem(self.t(code), code)
            field = "ui_language" if key == "ui" else key
            combo.setCurrentIndex(combo.findData(getattr(self.settings, field)))
            combo.blockSignals(False)
            self.labels[key].setText(self.t(key))
        for key, box in self.checks.items():
            field = {"start": "desktop_auto_start", "pin": "always_on_top"}.get(key, key)
            box.blockSignals(True)
            box.setChecked(getattr(self.settings, field))
            box.setText(self.t(key))
            box.blockSignals(False)
        self.update_status()
        if not self.text:
            self.reader.setPlainText(self.t("empty"))

    def update_status(self):
        self.status.setText(self.t(self.status_key))

    def save_preferences(self):
        previous = self.settings
        try:
            self.settings = update_settings(
                workflow=self.selects["workflow"].currentData(),
                source=self.selects["source"].currentData(),
                target=self.selects["target"].currentData(),
                mode=self.selects["mode"].currentData(),
                ui_language=self.selects["ui"].currentData(),
                enabled=self.checks["enabled"].isChecked(),
                cache=self.checks["cache"].isChecked(),
                desktop_auto_start=self.checks["start"].isChecked(),
                always_on_top=self.checks["pin"].isChecked(),
            )
            self.settings_changed(previous)
        except (TwinTextError, OSError) as exc:
            self.status.setText(str(exc))

    def settings_changed(self, previous):
        self.localize()
        if previous.always_on_top != self.settings.always_on_top:
            self.apply_pin()
        if (previous.source, previous.target, previous.cache) != (
            self.settings.source,
            self.settings.target,
            self.settings.cache,
        ):
            self.translate_current()
        elif previous.mode != self.settings.mode:
            if self.settings.mode == "original":
                self.revision += 1
                self.reader.setMarkdown(self.text)
            elif self.last_result:
                self.render_result()
            else:
                self.translate_current()

    def apply_pin(self):
        for window in (self, self.orb):
            visible = window.isVisible()
            window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.settings.always_on_top)
            if visible:
                window.show()

    def expand(self):
        self.orb.hide()
        self.show()
        self.raise_()
        self.activateWindow()
        self.orb_button.setText("TwinText  ↗")

    def collapse(self):
        self.hide()
        self.orb.show()

    def clear_cache(self):
        try:
            Cache().clear()
            self.status.setText(self.t("cache_cleared"))
        except (OSError, sqlite3.Error) as exc:
            self.status.setText(str(exc))

    def quit(self):
        self.timer.stop()
        self.hide()
        self.orb.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.accept()
        self.quit()

    def eventFilter(self, watched, event):
        if watched is self.orb and event.type() == QEvent.Type.Close:
            self.quit()
        return super().eventFilter(watched, event)

    def paste(self):
        self.editor.show()
        self.translate_button.show()
        self.editor.setPlainText(QApplication.clipboard().text()[:100_000])
        self.editor.setFocus()

    def translate_manual(self):
        text = self.editor.toPlainText()
        if not text.strip():
            return
        self.sessions.blockSignals(True)
        self.sessions.setCurrentIndex(-1)
        self.sessions.setPlaceholderText(self.t("manual"))
        self.sessions.blockSignals(False)
        self.text = text
        self.translate_current()

    def select_reply(self, index):
        if index >= 0 and index < len(self.rows):
            self.text = self.rows[index]["text"]
            self.translate_current()

    def translate_current(self):
        self.revision += 1
        self.last_result = None
        self.copy_button.setEnabled(bool(self.text))
        self.reader.setMarkdown(self.text or self.t("empty"))
        if self.text and self.settings.mode != "original":
            self.status_key = "working"
            self.translator.submit(
                self.revision, self.text, self.settings.source, self.settings.target
            )
        else:
            self.status_key = "ready" if self.text else "waiting"
        self.update_status()

    def render_result(self):
        self.reader.setMarkdown(display_text(self.last_result, self.settings.mode))

    def copy(self):
        text = display_text(self.last_result, self.settings.mode) if self.last_result else self.text
        QApplication.clipboard().setText(text)

    def clear(self):
        self.inbox.clear()
        self.revision += 1
        self.text = ""
        self.last_result = None
        self.rows = []
        self.ids = ()
        self.sessions.clear()
        self.editor.clear()
        self.copy_button.setEnabled(False)
        self.status_key = "waiting"
        self.localize()

    def poll(self):
        try:
            current = load_settings()
            if current != self.settings:
                previous, self.settings = self.settings, current
                self.settings_changed(previous)
            activation = self.inbox.activation()
            if activation != self.activation:
                self.activation = activation
                self.expand()
            rows = self.inbox.replies()
            ids = tuple(row["id"] for row in rows)
            if ids != self.ids:
                self.rows, self.ids = rows, ids
                self.sessions.blockSignals(True)
                self.sessions.clear()
                for row in rows:
                    self.sessions.addItem(f"{self.t('codex')} · {row['session'][:12]}", row["id"])
                self.sessions.blockSignals(False)
                if rows:
                    self.select_reply(0)
                    if self.orb.isVisible():
                        self.orb_button.setText("TwinText  ●")
                else:
                    self.text = ""
                    self.translate_current()
            while True:
                try:
                    revision, result, error = self.translator.results.get_nowait()
                except queue.Empty:
                    break
                if revision != self.revision:
                    continue
                if error:
                    self.status_key = "error"
                    self.status.setText(self.t("error") + ": " + error)
                else:
                    self.last_result = result
                    self.render_result()
                    self.status_key = "ready"
                    self.update_status()
        except (TwinTextError, OSError, sqlite3.Error) as exc:
            self.status.setText(str(exc))


STYLE = """
QWidget { background: #f7faf8; color: #20352e; font-size: 13px; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #196d5d; }
QLabel#muted { color: #60766d; font-size: 12px; }
QPushButton { background: #e7f0eb; border: 1px solid #d2e1d8; border-radius: 8px;
padding: 8px 12px; }
QPushButton:hover { background: #d6e8df; }
QPushButton:disabled { color: #91a39a; }
QComboBox, QPlainTextEdit { background: white; border: 1px solid #d2e1d8;
border-radius: 7px; padding: 6px; }
QComboBox { min-height: 20px; }
QPushButton { min-height: 16px; }
QTextBrowser#reader { background: white; border: 1px solid #d2e1d8; border-radius: 12px;
padding: 14px; font-size: 14px; }
QFrame#preferences { background: #edf4ef; border-radius: 9px; }
QFrame#orbPanel { background: #173f35; border: 1px solid #396757; border-radius: 23px; }
QFrame#orbPanel QWidget { background: transparent; }
QPushButton#orbExpand, QPushButton#orbQuit { background: transparent; color: #f0fff8; border: none;
border-radius: 18px; padding: 6px 10px; font-size: 13px; font-weight: 600; }
QPushButton#orbExpand:hover, QPushButton#orbQuit:hover { background: #285647; }
QPushButton#orbQuit { padding: 0; font-size: 18px; }
QCheckBox { padding: 2px; }
"""


def run(background=False):
    lock = desktop_lock()
    if lock is None:
        if not background:
            Inbox().activate()
        return 0
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("TwinText Desktop")
    app.setDesktopFileName("twintext")
    app.setQuitOnLastWindowClosed(False)
    icon = QPixmap(64, 64)
    icon.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon)
    painter.fillRect(icon.rect(), QColor("#196d5d"))
    painter.setPen(Qt.GlobalColor.white)
    font = painter.font()
    font.setPixelSize(26)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "TT")
    painter.end()
    app.setWindowIcon(QIcon(icon))
    window = Companion()
    window.collapse() if background else window.show()
    try:
        return app.exec()
    finally:
        window.hide()
        window.orb.hide()
        lock.close()
