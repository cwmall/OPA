"""Matplotlib canvas interaction that cooperates with Qt page scrolling."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


class ClickActivatedFigureCanvas(FigureCanvasQTAgg):
    """Require an explicit canvas click before the wheel controls a plot.

    Engineering pages are commonly taller than the window.  A normal
    Matplotlib canvas consumes every wheel event under the pointer, which
    traps the operator at a chart while scrolling the page.  This canvas
    forwards the wheel to its containing scroll area until it is clicked.
    Clicking anywhere outside the canvas releases wheel control again.
    """

    def __init__(self, figure):
        super().__init__(figure)
        self._wheel_interaction_active = False
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setProperty("wheelInteractionActive", False)
        self.setToolTip(
            "Scrolls the page by default. Click the graph to enable wheel zoom; "
            "click outside the graph to return the wheel to page scrolling."
        )

    @property
    def wheel_interaction_active(self):
        return self._wheel_interaction_active

    def activate_wheel_interaction(self):
        if self._wheel_interaction_active:
            return
        self._wheel_interaction_active = True
        self.setProperty("wheelInteractionActive", True)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.style().unpolish(self)
        self.style().polish(self)

    def deactivate_wheel_interaction(self):
        if not self._wheel_interaction_active:
            return
        self._wheel_interaction_active = False
        self.setProperty("wheelInteractionActive", False)
        self.clearFocus()
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _containing_scroll_area(widget):
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parentWidget()
        return None

    @staticmethod
    def _wheel_delta(event, scroll_bar):
        pixel_delta = event.pixelDelta().y()
        if pixel_delta:
            return int(pixel_delta)
        wheel_steps = event.angleDelta().y() / 120.0
        return int(wheel_steps * max(scroll_bar.singleStep(), 20) * 3)

    def mousePressEvent(self, event):
        self.activate_wheel_interaction()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if self._wheel_interaction_active:
            super().wheelEvent(event)
            return

        scroll_area = self._containing_scroll_area(self)
        if scroll_area is None:
            event.ignore()
            return

        scroll_bar = scroll_area.verticalScrollBar()
        scroll_bar.setValue(
            scroll_bar.value() - self._wheel_delta(event, scroll_bar)
        )
        event.accept()
