from PyQt6 import sip
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication

GRIP = 7  # px от края окна


_EDGE_CURSORS = {
    Qt.Edge.LeftEdge:                        Qt.CursorShape.SizeHorCursor,
    Qt.Edge.RightEdge:                       Qt.CursorShape.SizeHorCursor,
    Qt.Edge.TopEdge:                         Qt.CursorShape.SizeVerCursor,
    Qt.Edge.BottomEdge:                      Qt.CursorShape.SizeVerCursor,
    Qt.Edge.LeftEdge  | Qt.Edge.TopEdge:     Qt.CursorShape.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.BottomEdge:  Qt.CursorShape.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.TopEdge:     Qt.CursorShape.SizeBDiagCursor,
    Qt.Edge.LeftEdge  | Qt.Edge.BottomEdge:  Qt.CursorShape.SizeBDiagCursor,
}


def _detect_edge(gx, gy, rect):
    """Определяем край по глобальным координатам мыши и геометрии окна."""
    x = gx - rect.x()
    y = gy - rect.y()
    w, h = rect.width(), rect.height()

    edge = Qt.Edge(0)
    if 0 <= x <= GRIP:
        edge |= Qt.Edge.LeftEdge
    elif w - GRIP <= x <= w:
        edge |= Qt.Edge.RightEdge
    if 0 <= y <= GRIP:
        edge |= Qt.Edge.TopEdge
    elif h - GRIP <= y <= h:
        edge |= Qt.Edge.BottomEdge
    return edge


class ResizeFilter(QObject):
    """Фильтр на уровне приложения — ловит события у краёв frameless-окна."""

    def __init__(self, window):
        super().__init__(QApplication.instance())
        self._win = window
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if sip.isdeleted(self._win):
            QApplication.instance().removeEventFilter(self)
            return False
        if self._win.isMaximized():
            return False

        t = event.type()

        if t == QEvent.Type.MouseMove:
            gpos = QCursor.pos()
            rect = self._win.frameGeometry()
            if rect.contains(gpos):
                edge = _detect_edge(gpos.x(), gpos.y(), rect)
                cursor = _EDGE_CURSORS.get(edge)
                if cursor:
                    self._win.setCursor(QCursor(cursor))
                    return False
            # Сбрасываем только если курсор был изменён нами
            self._win.unsetCursor()

        elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            gpos = QCursor.pos()
            rect = self._win.frameGeometry()
            if rect.contains(gpos):
                edge = _detect_edge(gpos.x(), gpos.y(), rect)
                if edge:
                    self._win.windowHandle().startSystemResize(edge)
                    return True

        return False
