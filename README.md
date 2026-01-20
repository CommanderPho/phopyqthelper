# PhoPyQtHelper

Reusable Qt widgets and helpers for Python applications.

## Installation

```bash
uv add phopyqthelper
```

## Widgets

### ConsoleOutputWidget

A Qt widget that displays stdout/stderr output in a scrollable text area with optional stream capture and callback support.

```python
from phopyqthelper.widgets import ConsoleOutputWidget

# Basic usage - captures stdout/stderr automatically
widget = ConsoleOutputWidget()

# Pure log viewer mode (no stream capture)
widget = ConsoleOutputWidget(capture_stdout=False, capture_stderr=False)

# With callback for external logging
def my_callback(text: str, source: str):
    # source is "stdout", "stderr", or "manual"
    print(f"[{source}] {text}")

widget = ConsoleOutputWidget(text_callback=my_callback)

# Programmatically append text
widget.append_text("Custom message", source="manual")
```
