"""Place TwinText beside a Codex window without changing Codex itself."""

from PySide6.QtCore import QEvent, QObject, QPoint, QRect
from PySide6.QtWidgets import QApplication

from twintext.window_tracking import create_tracker


def logical_bounds(target, screens):
    """Convert OS pixels to Qt's coordinates, including negative monitor origins."""
    screen = next((s for s in screens if s.name() == target.screen_name), screens[0])
    scale = screen.devicePixelRatio()
    origin = screen.geometry().topLeft()
    native = QPoint(*target.monitor) if target.monitor else origin
    return QRect(origin.x() + round((target.x - native.x()) / scale),
                 origin.y() + round((target.y - native.y()) / scale),
                 round(target.width / scale), round(target.height / scale))


def confined(position, size, area):
    return QPoint(max(area.left(), min(position.x(), area.right() - size.width() + 1)),
                  max(area.top(), min(position.y(), area.bottom() - size.height() + 1)))


class WindowFollower(QObject):
    def __init__(self, companion, factory=create_tracker):
        super().__init__(companion)
        self.window = companion
        self.factory = factory
        self.tracker = None
        self.failed = False
        self.bounds = None
        self.offset = None
        self.reader_offset = None
        self.moving = False
        self.hidden = False
        self.status = "follow_waiting"
        companion.orb.installEventFilter(self)
        companion.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.Move and self.bounds is not None
                and not self.moving and not self.hidden and watched.isVisible()):
            offset = watched.pos() - self.bounds.topLeft()
            if watched is self.window.orb:
                self.offset = offset
            elif watched is self.window:
                self.reader_offset = offset
        return False

    def close(self):
        if self.tracker:
            try:
                self.tracker.close()
            except Exception:
                pass
            finally:
                self.tracker = None

    def tick(self):
        window = self.window
        if window.dismissed:
            self.close()
            self.hidden = False
            return
        enabled = window.settings.follow_codex and (
            window.settings.workflow == "desktop" or window.settings.floating_chat)
        if not enabled:
            self.close()
            if self.hidden:
                window.orb.show()
                window.setVisible(window.reader_open)
            self.hidden = False
            self.bounds = None
            self.failed = False
            return
        if self.failed:
            return
        try:
            if self.tracker is None:
                self.tracker = self.factory()
            snapshot = self.tracker.read()
        except Exception:
            # Unsupported hosts and lost display connections leave a usable manual button.
            self.close()
            self.failed = True
            self.status = "follow_unavailable"
            if self.hidden:
                window.orb.show()
                window.setVisible(window.reader_open)
            self.hidden = False
            return
        target = snapshot.target
        if target:
            self.bounds = logical_bounds(target, QApplication.screens())
        self.status = "following" if target else "follow_waiting"
        # Keep settings reachable even when Codex has closed or is not focused.
        if not window.preference_scroll.isHidden() or self.bounds is None:
            return
        own_ids = {int(widget.effectiveWinId()) for widget in QApplication.topLevelWidgets()
                   if widget.effectiveWinId()}
        visible = bool(target and target.visible and snapshot.foreground in own_ids | {target.id})
        self.hidden = not visible
        if not visible:
            window.hide()
            window.orb.hide()
            return
        self.moving = True
        try:
            bounds = self.bounds
            if self.offset is None:
                self.offset = QPoint(bounds.width() - window.orb.width() - 16, 100)
            screen = QApplication.screenAt(bounds.center()) or window.orb.screen()
            area = screen.availableGeometry()
            # Keep the button inside Codex, even after resizing to a smaller window.
            orb_area = bounds.intersected(area)
            if orb_area.isEmpty():
                orb_area = area
            position = confined(bounds.topLeft() + self.offset, window.orb.size(), orb_area)
            window.orb.move(position)
            window.orb.show()
            if window.reader_open:
                position = (bounds.topLeft() + self.reader_offset if self.reader_offset is not None
                            else position - QPoint(window.width() + 12, 0))
                window.move(confined(position, window.size(), area))
                window.show()
            window.orb_button.setChecked(window.reader_open)
        finally:
            self.moving = False
