#!/usr/bin/env python3
"""SAGE UI — PyQt6 interface for the cognitive operating system.

Features:
- Dark theme with blue accents (Mark XXXIX style)
- Chat interface with message history
- Voice input (microphone) and output (TTS)
- System metrics display
- Tool execution feedback
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QRectF, Qt, QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar,
)

# ---------------------------------------------------------------------------
# Colors (Mark XXXIX style)
# ---------------------------------------------------------------------------

class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ---------------------------------------------------------------------------
# System Metrics
# ---------------------------------------------------------------------------

class SysMetrics:
    """Background thread that collects CPU, memory, network stats."""

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
# Message Bubble
# ---------------------------------------------------------------------------

class MessageBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui(text)

    def _setup_ui(self, text: str):
        self.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL2 if self.is_user else C.PRI_GHO};
                border: 1px solid {C.BORDER if self.is_user else C.BORDER_B};
                border-radius: 12px;
                padding: 12px;
                margin: 4px 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Sender label
        sender = QLabel("You" if self.is_user else "Sage")
        sender.setStyleSheet(f"""
            color: {C.PRI if self.is_user else C.GREEN};
            font-size: 11px;
            font-weight: bold;
            border: none;
            background: transparent;
        """)
        layout.addWidget(sender)

        # Message text
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"""
            color: {C.WHITE};
            font-size: 14px;
            border: none;
            background: transparent;
            padding: 4px 0;
        """)
        layout.addWidget(msg)


# ---------------------------------------------------------------------------
# System Metrics Bar
# ---------------------------------------------------------------------------

class MetricsBar(QFrame):
    """Displays CPU, memory, network stats."""

    def __init__(self, metrics: SysMetrics, parent=None):
        super().__init__(parent)
        self.metrics = metrics
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C.BAR_BG};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(24)

        self.cpu_label = self._make_label("CPU")
        self.cpu_bar = self._make_bar()
        self.mem_label = self._make_label("MEM")
        self.mem_bar = self._make_bar()
        self.net_label = self._make_label("NET")

        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.mem_label)
        layout.addWidget(self.mem_bar)
        layout.addWidget(self.net_label)
        layout.addStretch()

        # Update timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(2000)

    def _make_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; border: none; background: transparent;")
        return label

    def _make_bar(self) -> QProgressBar:
        bar = QProgressBar()
        bar.setFixedWidth(80)
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C.DARK};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {C.PRI};
                border-radius: 3px;
            }}
        """)
        return bar

    def _update(self):
        self.cpu_bar.setValue(int(self.metrics.cpu))
        self.mem_bar.setValue(int(self.metrics.mem))
        up = self.metrics.net_up
        down = self.metrics.net_down
        self.net_label.setText(f"NET ↑{up:.0f} ↓{down:.0f} KB/s")


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class SageUI(QMainWindow):
    """Main SAGE interface."""

    user_message = pyqtSignal(str)

    def __init__(self, process_fn=None):
        super().__init__()
        self.process_fn = process_fn
        self.metrics = SysMetrics()
        self._voice_active = False

        self.setWindowTitle("SAGE — Cognitive Operating System")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)

        self._setup_ui()
        self.user_message.connect(self._on_user_message)

    def _setup_ui(self):
        # Central widget
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
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border-bottom: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title = QLabel("SAGE")
        title.setStyleSheet(f"""
            color: {C.PRI};
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Cognitive Operating System")
        subtitle.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: 12px;
            margin-left: 12px;
        """)
        layout.addWidget(subtitle)

        layout.addStretch()

        # Status
        status = QLabel("● Online")
        status.setStyleSheet(f"""
            color: {C.GREEN};
            font-size: 12px;
        """)
        layout.addWidget(status)

        return header

    def _make_chat_area(self) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"background: {C.BG};")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for messages
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {C.BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {C.DARK};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C.PRI_DIM};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        # Messages container
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(20, 16, 20, 16)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_widget)
        layout.addWidget(self.scroll)

        # Welcome message
        self._add_system_message("Welcome to Sage. Type a message or click the microphone to speak.")

        return container

    def _make_input_area(self) -> QFrame:
        container = QFrame()
        container.setFixedHeight(72)
        container.setStyleSheet(f"""
            QFrame {{
                background: {C.PANEL};
                border-top: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Text input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: {C.DARK};
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {C.PRI};
            }}
        """)
        self.input_field.returnPressed.connect(self._send_message)
        layout.addWidget(self.input_field, 1)

        # Voice button
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(44, 44)
        self.voice_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.DARK};
                border: 1px solid {C.BORDER};
                border-radius: 22px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                border-color: {C.PRI};
                background: {C.PRI_GHO};
            }}
        """)
        self.voice_btn.clicked.connect(self._toggle_voice)
        layout.addWidget(self.voice_btn)

        # Send button
        self.send_btn = QPushButton("→")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI};
                color: {C.DARK};
                border: none;
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {C.BORDER_B};
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        layout.addWidget(self.send_btn)

        return container

    def _add_message(self, text: str, is_user: bool):
        """Add a message bubble to the chat."""
        bubble = MessageBubble(text, is_user)
        # Insert before the stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _add_system_message(self, text: str):
        """Add a system message (centered, muted)."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: 12px;
            padding: 16px;
            border: none;
            background: transparent;
        """)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, label)

    def _scroll_to_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send_message(self):
        """Handle send button or Enter key."""
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self._add_message(text, is_user=True)

        # Process in background thread
        threading.Thread(target=self._process_in_background, args=(text,), daemon=True).start()

    def _process_in_background(self, text: str):
        """Run Sage processing in background thread."""
        if self.process_fn:
            try:
                response = self.process_fn(text)
            except Exception as e:
                response = f"Error: {e}"
        else:
            response = f"Echo: {text}"

        # Emit signal to update UI from main thread
        self.user_message.emit(response)

    def _on_user_message(self, response: str):
        """Handle response from background thread."""
        self._add_message(response, is_user=False)

    def _toggle_voice(self):
        """Toggle voice input."""
        if self._voice_active:
            self._voice_active = False
            self.voice_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.DARK};
                    border: 1px solid {C.BORDER};
                    border-radius: 22px;
                    font-size: 18px;
                }}
                QPushButton:hover {{
                    border-color: {C.PRI};
                    background: {C.PRI_GHO};
                }}
            """)
        else:
            self._voice_active = True
            self.voice_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.RED};
                    border: 1px solid {C.RED};
                    border-radius: 22px;
                    font-size: 18px;
                }}
            """)
            # Start voice recording in background
            threading.Thread(target=self._voice_loop, daemon=True).start()

    def _voice_loop(self):
        """Record audio, transcribe, process."""
        try:
            from embodiment.voice_io import record_audio, transcribe_with_whisper
            self._add_system_message("Listening... speak now")
            audio = record_audio(max_seconds=15)
            if audio is None:
                self._add_system_message("No speech detected")
                self._voice_active = False
                return

            text = transcribe_with_whisper(audio)
            if not text:
                self._add_system_message("Could not understand audio")
                self._voice_active = False
                return

            self._add_message(text, is_user=True)
            self.user_message.emit(self.process_fn(text) if self.process_fn else f"Echo: {text}")

        except Exception as e:
            self._add_system_message(f"Voice error: {e}")
        finally:
            self._voice_active = False
            self.voice_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.DARK};
                    border: 1px solid {C.BORDER};
                    border-radius: 22px;
                    font-size: 18px;
                }}
                QPushButton:hover {{
                    border-color: {C.PRI};
                    background: {C.PRI_GHO};
                }}
            """)

    def closeEvent(self, event):
        self.metrics._running = False
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_ui(process_fn=None):
    """Launch the SAGE UI."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = SageUI(process_fn=process_fn)
    window.show()

    return app.exec()


if __name__ == "__main__":
    run_ui()
