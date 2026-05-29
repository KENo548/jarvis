#!/usr/bin/env python3
"""SAGE UI — Golden Ratio + Old Money aesthetic PyQt6 interface."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QRectF, Qt, QTimer, QUrl, pyqtSignal, QObject,
)
from PyQt6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPen,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget, QProgressBar,
)

# ---------------------------------------------------------------------------
# Golden Ratio Old Money Palette
# ---------------------------------------------------------------------------
# Golden Ratio: 1 : 1.618
# Old Money: navy, cream, gold, understated elegance

PHI = 1.618

class C:
    # Backgrounds — deep navy, almost black
    BG         = "#0a0e14"
    PANEL      = "#0f1520"
    PANEL2     = "#141c28"
    SURFACE    = "#1a2332"

    # Borders — subtle gold/cream
    BORDER     = "#2a3a4e"
    BORDER_F   = "#c9a962"   # Gold accent (old money)
    BORDER_S   = "#8b7d5e"   # Muted gold

    # Primary — warm gold (old money, not neon)
    PRI        = "#c9a962"
    PRI_DIM    = "#8b7d5e"
    PRI_GHO    = "#1a1f14"

    # Accent — deep burgundy
    ACC        = "#8b2252"
    ACC2       = "#c9a962"

    # Status
    GREEN      = "#4a7c59"
    GREEN_D    = "#2d5a3a"
    RED        = "#8b3a3a"

    # Text — cream/ivory tones
    TEXT       = "#e8dcc8"    # Warm ivory
    TEXT_DIM   = "#6b7d8e"
    TEXT_MED   = "#9ba8b4"
    WHITE      = "#f5f0e8"    # Warm white
    DARK       = "#060810"

    # Bars
    BAR_BG     = "#0c1018"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ---------------------------------------------------------------------------
# System Metrics (background thread)
# ---------------------------------------------------------------------------

class SysMetrics:
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.net_up = 0.0
        self.net_down = 0.0
        self._running = True
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        self.cpu = psutil.cpu_percent(interval=None)
        self.mem = psutil.virtual_memory().percent
        net = psutil.net_io_counters()
        now = time.time()
        dt = now - self._last_net_t
        if dt > 0:
            self.net_up = (net.bytes_sent - self._last_net.bytes_sent) / dt / 1024
            self.net_down = (net.bytes_recv - self._last_net.bytes_recv) / dt / 1024
        self._last_net = net
        self._last_net_t = now


# ---------------------------------------------------------------------------
# Golden Ratio Helpers
# ---------------------------------------------------------------------------

def phi_scale(base: float) -> int:
    """Scale a dimension by golden ratio."""
    return int(base * PHI)

def phi_split(total: int) -> tuple[int, int]:
    """Split total into golden ratio parts."""
    small = int(total / PHI)
    return total - small, small


# ---------------------------------------------------------------------------
# Message Bubble — Old Money Style
# ---------------------------------------------------------------------------

class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui(text)

    def _setup_ui(self, text: str):
        if self.is_user:
            bg = C.SURFACE
            border = C.BORDER
            sender_color = C.PRI
            sender_text = "You"
        else:
            bg = C.PRI_GHO
            border = C.BORDER_F
            sender_color = C.GREEN
            sender_text = "Sage"

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 14px 18px;
                margin: 4px 0;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        # Sender — small caps, elegant
        sender = QLabel(sender_text)
        sender.setStyleSheet(f"""
            color: {sender_color};
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            border: none;
            background: transparent;
        """)
        layout.addWidget(sender)

        # Message — warm ivory, serif-like
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"""
            color: {C.WHITE};
            font-size: 14px;
            line-height: 1.5;
            border: none;
            background: transparent;
            padding: 2px 0;
        """)
        layout.addWidget(msg)


# ---------------------------------------------------------------------------
# System Metrics Bar — Old Money
# ---------------------------------------------------------------------------

class MetricsBar(QFrame):
    def __init__(self, metrics: SysMetrics, parent=None):
        super().__init__(parent)
        self.metrics = metrics
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C.BAR_BG};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 4, 24, 4)
        layout.setSpacing(32)

        self.cpu_label = self._label("CPU")
        self.cpu_bar = self._bar()
        self.mem_label = self._label("MEM")
        self.mem_bar = self._bar()
        self.net_label = self._label("NET")

        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.mem_label)
        layout.addWidget(self.mem_bar)
        layout.addWidget(self.net_label)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(2000)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; border: none; background: transparent; letter-spacing: 1px;")
        return label

    def _bar(self) -> QProgressBar:
        bar = QProgressBar()
        bar.setFixedWidth(80)
        bar.setFixedHeight(6)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C.DARK};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {C.PRI_DIM};
                border-radius: 2px;
            }}
        """)
        return bar

    def _update(self):
        self.cpu_bar.setValue(int(self.metrics.cpu))
        self.mem_bar.setValue(int(self.metrics.mem))
        self.net_label.setText(f"NET \u2191{self.metrics.net_up:.0f} \u2193{self.metrics.net_down:.0f} KB/s")


# ---------------------------------------------------------------------------
# Main Window — Old Money Elegance
# ---------------------------------------------------------------------------

class SageUI(QMainWindow):
    # Signals for thread-safe UI updates
    response_ready = pyqtSignal(str)
    system_msg_ready = pyqtSignal(str)
    voice_status_ready = pyqtSignal(str)

    def __init__(self, process_fn=None):
        super().__init__()
        self.process_fn = process_fn
        self.metrics = SysMetrics()
        self._voice_active = False
        self._processing = False

        # Connect signals
        self.response_ready.connect(self._on_response)
        self.system_msg_ready.connect(self._on_system_msg)
        self.voice_status_ready.connect(self._on_voice_status)

        self.setWindowTitle("SAGE")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self._make_header()
        main_layout.addWidget(header)

        # Metrics bar
        metrics_bar = MetricsBar(self.metrics)
        main_layout.addWidget(metrics_bar)

        # Chat area
        chat_widget = self._make_chat_area()
        main_layout.addWidget(chat_widget, 1)

        # Input area
        input_widget = self._make_input_area()
        main_layout.addWidget(input_widget)

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 0, 28, 0)

        # Title — elegant, spaced
        title = QLabel("SAGE")
        title.setStyleSheet(f"""
            color: {C.PRI};
            font-size: 20px;
            font-weight: 300;
            letter-spacing: 8px;
        """)
        layout.addWidget(title)

        # Thin gold line separator
        sep = QLabel("\u2014")
        sep.setStyleSheet(f"color: {C.BORDER_F}; font-size: 16px; margin: 0 12px; border: none; background: transparent;")
        layout.addWidget(sep)

        # Subtitle
        subtitle = QLabel("Cognitive Operating System")
        subtitle.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: 11px;
            letter-spacing: 1px;
        """)
        layout.addWidget(subtitle)

        layout.addStretch()

        # Status
        status = QLabel("\u25cf Online")
        status.setStyleSheet(f"color: {C.GREEN}; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(status)

        return header

    def _make_chat_area(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"background: {C.BG};")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {C.BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {C.DARK};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C.PRI_DIM};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(28, 20, 28, 20)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_widget)
        layout.addWidget(self.scroll)

        # Welcome
        self._add_system_msg("How may I assist you today?")

        return container

    def _make_input_area(self) -> QFrame:
        container = QFrame()
        container.setFixedHeight(76)
        container.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border-top: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(14)

        # Text input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 11px 18px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {C.BORDER_F};
            }}
        """)
        self.input_field.returnPressed.connect(self._send_message)
        layout.addWidget(self.input_field, 1)

        # Voice button
        self.voice_btn = QPushButton("\U0001f3a4")
        self.voice_btn.setFixedSize(44, 44)
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_style_normal()
        self.voice_btn.clicked.connect(self._toggle_voice)
        layout.addWidget(self.voice_btn)

        # Send button
        self.send_btn = QPushButton("\u2192")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI};
                color: {C.DARK};
                border: none;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {C.BORDER_F};
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        layout.addWidget(self.send_btn)

        return container

    def _voice_style_normal(self):
        self.voice_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.DARK};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                border-color: {C.BORDER_F};
                background: {C.PRI_GHO};
            }}
        """)

    def _voice_style_active(self):
        self.voice_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.ACC};
                border: 1px solid {C.ACC};
                border-radius: 4px;
                font-size: 18px;
            }}
        """)

    # --- Thread-safe message methods ---

    def _add_message(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _add_system_msg(self, text: str):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: 12px;
            padding: 16px;
            border: none;
            background: transparent;
            letter-spacing: 0.5px;
        """)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, label)

    def _scroll_to_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # --- Slots connected to signals ---

    def _on_response(self, response: str):
        self._add_message(response, is_user=False)
        self._processing = False
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)

    def _on_system_msg(self, text: str):
        self._add_system_msg(text)

    def _on_voice_status(self, status: str):
        if status == "listening":
            self._add_system_msg("Listening... speak now")
        elif status == "error":
            self._add_system_msg("Could not understand. Please try again.")
        elif status == "done":
            pass

    # --- User actions ---

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text or self._processing:
            return

        self.input_field.clear()
        self._add_message(text, is_user=True)

        self._processing = True
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)

        threading.Thread(target=self._process_in_background, args=(text,), daemon=True).start()

    def _process_in_background(self, text: str):
        if self.process_fn:
            try:
                response = self.process_fn(text)
            except Exception as e:
                response = f"Error: {e}"
        else:
            response = f"Echo: {text}"

        self.response_ready.emit(response)

    def _toggle_voice(self):
        if self._voice_active:
            self._voice_active = False
            self._voice_style_normal()
        else:
            self._voice_active = True
            self._voice_style_active()
            threading.Thread(target=self._voice_loop, daemon=True).start()

    def _voice_loop(self):
        try:
            from embodiment.voice_io import record_audio, transcribe_with_whisper

            self.voice_status_ready.emit("listening")
            audio = record_audio(max_seconds=15)

            if audio is None:
                self.voice_status_ready.emit("error")
                self._voice_active = False
                self._voice_style_normal()
                return

            text = transcribe_with_whisper(audio)
            if not text:
                self.voice_status_ready.emit("error")
                self._voice_active = False
                self._voice_style_normal()
                return

            # Emit signal to add user message on main thread
            self.system_msg_ready.emit(f"You said: {text}")

            # Process
            if self.process_fn:
                response = self.process_fn(text)
            else:
                response = f"Echo: {text}"

            self.response_ready.emit(response)

        except Exception as e:
            self.system_msg_ready.emit(f"Voice error: {e}")
        finally:
            self._voice_active = False
            self._voice_style_normal()

    def closeEvent(self, event):
        self.metrics._running = False
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_ui(process_fn=None):
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Georgia", 10)  # Serif font — old money
    app.setFont(font)

    window = SageUI(process_fn=process_fn)
    window.show()

    return app.exec()


if __name__ == "__main__":
    run_ui()
