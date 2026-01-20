#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.
#  Generalized for reuse by Pho Hale.

import sys
from typing import Optional, Callable
from qtpy import QtWidgets, QtCore, QtGui


class TextStream(QtCore.QObject):
    """A thread-safe text stream that emits signals when text is written.
    
    Attributes:
        source: The source identifier for this stream ("stdout", "stderr", or custom).
    """
    text_written = QtCore.Signal(str, str)  # (text, source)

    def __init__(self, original_stream, source: str = "stdout"):
        super().__init__()
        self._original_stream = original_stream
        self._buffer = ""
        self._source = source


    @property
    def source(self) -> str:
        """Return the source identifier for this stream."""
        return self._source


    def write(self, text):
        """Write text and emit signal for UI update."""
        if text:
            self._buffer += text
            # Emit signal for thread-safe UI update
            try:
                self.text_written.emit(text, self._source)
            except Exception:
                # If signal emission fails, fallback to original stream
                if self._original_stream:
                    try:
                        self._original_stream.write(text)
                    except Exception:
                        pass
        return len(text) if text else 0


    def flush(self):
        """Flush the stream."""
        if self._original_stream:
            self._original_stream.flush()


    def isatty(self):
        """Check if this is a TTY."""
        return False


    def readable(self):
        """Check if stream is readable."""
        return False


    def writable(self):
        """Check if stream is writable."""
        return True


    def seekable(self):
        """Check if stream is seekable."""
        return False


class ConsoleOutputWidget(QtWidgets.QWidget):
    """Widget that displays stdout/stderr output in a scrollable text area.
    
    Features:
        - Optional stdout/stderr capture (can function as pure log viewer)
        - Callback support for external logging/processing
        - Auto-scroll with toggle control
        - Line limit to prevent memory issues
        - Thread-safe text updates via Qt signals
    
    Args:
        parent: Parent widget.
        capture_stdout: Whether to capture sys.stdout. Defaults to True.
        capture_stderr: Whether to capture sys.stderr. Defaults to True.
        text_callback: Optional callback function called on every text write.
            Receives (text: str, source: str) where source is "stdout", "stderr", or "manual".
        max_lines: Maximum number of lines to retain. Defaults to 10000.
    """

    def __init__(self, parent=None, capture_stdout: bool = True, capture_stderr: bool = True, text_callback: Optional[Callable[[str, str], None]] = None, max_lines: int = 10000):
        super().__init__(parent)
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._stdout_stream: Optional[TextStream] = None
        self._stderr_stream: Optional[TextStream] = None
        self._capture_stdout = capture_stdout
        self._capture_stderr = capture_stderr
        self._text_callback = text_callback
        self._max_lines = max_lines
        self._auto_scroll = True
        self._setup_ui()
        self._setup_streams()


    def _setup_ui(self):
        """Set up the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar with controls
        toolbar = QtWidgets.QHBoxLayout()
        
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        auto_scroll_cb = QtWidgets.QCheckBox("Auto-scroll")
        auto_scroll_cb.setChecked(True)
        auto_scroll_cb.toggled.connect(self._on_auto_scroll_toggled)
        toolbar.addWidget(auto_scroll_cb)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Text display area
        self._text_edit = QtWidgets.QPlainTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QtWidgets.QApplication.font())
        self._text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        layout.addWidget(self._text_edit)


    def _setup_streams(self):
        """Set up stdout/stderr redirection based on capture settings."""
        if self._capture_stdout:
            self._stdout_stream = TextStream(self._original_stdout, source="stdout")
            self._stdout_stream.text_written.connect(self._on_text_written)
            sys.stdout = self._stdout_stream

        if self._capture_stderr:
            self._stderr_stream = TextStream(self._original_stderr, source="stderr")
            self._stderr_stream.text_written.connect(self._on_text_written)
            sys.stderr = self._stderr_stream


    def _on_text_written(self, text: str, source: str):
        """Handle text written from captured streams."""
        self._append_text_internal(text, source)


    def _append_text_internal(self, text: str, source: str):
        """Internal method to append text and fire callback."""
        if not text:
            return

        # Fire callback if registered
        if self._text_callback is not None:
            try:
                self._text_callback(text, source)
            except Exception:
                pass  # Don't let callback errors break the widget

        # Safety check: ensure widget is ready
        if not hasattr(self, '_text_edit') or self._text_edit is None:
            # Fallback to original stream if widget not ready
            if self._original_stdout:
                self._original_stdout.write(text)
            return

        try:
            # Append text
            self._text_edit.moveCursor(QtGui.QTextCursor.End)
            self._text_edit.insertPlainText(text)

            # Limit buffer size
            document = self._text_edit.document()
            if document.blockCount() > self._max_lines:
                cursor = QtGui.QTextCursor(document)
                cursor.movePosition(QtGui.QTextCursor.Start)
                cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.MoveAnchor, document.blockCount() - self._max_lines)
                cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
                cursor.movePosition(QtGui.QTextCursor.End, QtGui.QTextCursor.KeepAnchor)
                cursor.removeSelectedText()

            # Auto-scroll if enabled
            if self._auto_scroll:
                scrollbar = self._text_edit.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            # If widget operations fail, fallback to original stream
            if self._original_stdout:
                try:
                    self._original_stdout.write(text)
                except Exception:
                    pass


    def append_text(self, text: str, source: str = "manual"):
        """Public method to append text programmatically.
        
        Args:
            text: The text to append.
            source: Source identifier for the text. Defaults to "manual".
        """
        self._append_text_internal(text, source)


    def set_capture(self, stdout: bool, stderr: bool):
        """Enable or disable stream capture at runtime.
        
        Args:
            stdout: Whether to capture stdout.
            stderr: Whether to capture stderr.
        """
        # Handle stdout
        if stdout and not self._capture_stdout:
            # Enable stdout capture
            self._stdout_stream = TextStream(self._original_stdout, source="stdout")
            self._stdout_stream.text_written.connect(self._on_text_written)
            sys.stdout = self._stdout_stream
            self._capture_stdout = True
        elif not stdout and self._capture_stdout:
            # Disable stdout capture
            if sys.stdout is self._stdout_stream:
                sys.stdout = self._original_stdout
            self._stdout_stream = None
            self._capture_stdout = False

        # Handle stderr
        if stderr and not self._capture_stderr:
            # Enable stderr capture
            self._stderr_stream = TextStream(self._original_stderr, source="stderr")
            self._stderr_stream.text_written.connect(self._on_text_written)
            sys.stderr = self._stderr_stream
            self._capture_stderr = True
        elif not stderr and self._capture_stderr:
            # Disable stderr capture
            if sys.stderr is self._stderr_stream:
                sys.stderr = self._original_stderr
            self._stderr_stream = None
            self._capture_stderr = False


    def set_text_callback(self, callback: Optional[Callable[[str, str], None]]):
        """Set or update the text callback.
        
        Args:
            callback: Callback function receiving (text, source), or None to remove.
        """
        self._text_callback = callback


    def _on_auto_scroll_toggled(self, checked):
        """Handle auto-scroll checkbox toggle."""
        self._auto_scroll = checked


    def clear(self):
        """Clear the text display."""
        self._text_edit.clear()


    def restore_streams(self):
        """Restore original stdout/stderr streams."""
        if self._stdout_stream is not None and sys.stdout is self._stdout_stream:
            sys.stdout = self._original_stdout
        if self._stderr_stream is not None and sys.stderr is self._stderr_stream:
            sys.stderr = self._original_stderr


    def closeEvent(self, event):
        """Handle widget close event."""
        self.restore_streams()
        super().closeEvent(event)
