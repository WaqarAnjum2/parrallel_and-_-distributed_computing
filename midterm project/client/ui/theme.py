"""
Unified Modern Light Design Tokens & Styles for Distributed GPU Client.
"""

# Color Palette (Crisp High-Tech Light Mode)
BG_WINDOW = "#F8FAFC"       # Slate 50
BG_PANEL = "#FFFFFF"        # Pure White Card
BG_INPUT = "#FFFFFF"        # Input background
BG_SUBTLE = "#F1F5F9"       # Slate 100
BORDER_COLOR = "#E2E8F0"    # Slate 200
BORDER_FOCUS = "#2563EB"    # Cobalt 500

TEXT_MAIN = "#0F172A"       # Slate 900
TEXT_MUTED = "#64748B"      # Slate 500
TEXT_SECONDARY = "#334155"  # Slate 700

PRIMARY_BLUE = "#2563EB"    # Electric Cobalt Blue
PRIMARY_HOVER = "#1D4ED8"   # Darker Blue
SIGNAL_GREEN = "#10B981"    # Emerald
SIGNAL_AMBER = "#F59E0B"    # Amber
SIGNAL_RED = "#EF4444"      # Crimson
SIGNAL_PURPLE = "#8B5CF6"   # Violet

LIGHT_THEME_QSS = f"""
QMainWindow {{
    background-color: {BG_WINDOW};
}}
QWidget {{
    background-color: transparent;
    color: {TEXT_MAIN};
    font-family: 'Segoe UI', Inter, -apple-system, system-ui, sans-serif;
}}
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px;
    font-weight: 700;
    font-size: 13px;
    color: {TEXT_MAIN};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: {PRIMARY_BLUE};
    background-color: {BG_WINDOW};
    border-radius: 4px;
}}
QLineEdit, QSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_MAIN};
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {PRIMARY_BLUE};
    background-color: #FFFFFF;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    background-color: {BG_PANEL};
}}
QTabBar::tab {{
    background-color: {BG_SUBTLE};
    color: {TEXT_MUTED};
    padding: 10px 22px;
    border: 1px solid {BORDER_COLOR};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {PRIMARY_BLUE};
    border-bottom: 2px solid {PRIMARY_BLUE};
}}
QTabBar::tab:hover:!selected {{
    background-color: #E2E8F0;
    color: {TEXT_MAIN};
}}
QScrollBar:vertical {{
    background: {BG_WINDOW};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QStatusBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {BORDER_COLOR};
    color: {TEXT_MUTED};
}}
"""
