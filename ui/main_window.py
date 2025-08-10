import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QFrame, QCheckBox, QStyleFactory,
    QDialog, QComboBox, QFormLayout, QPushButton, QDialogButtonBox, QTabWidget
)
from PySide6.QtCore import (Qt, QPoint, QPropertyAnimation, QEasingCurve, QSize,
                            QRunnable, Slot, Signal, QObject, QThreadPool)
from PySide6.QtGui import QIcon, QClipboard

from core.screenshot_handler import take_screenshot, get_available_screens
from utils.config_manager import get_app_config, save_app_config
from core.ai_services import get_question_from_image, get_answer_from_text, get_direct_answer_from_image
# Try to import full knowledge base components, fallback to simplified versions
try:
    from ui.knowledge_base_panel import KnowledgeBasePanel
    from ui.knowledge_base_settings import KnowledgeBaseSettingsDialog
    print("Using full knowledge base components")
except ImportError as e:
    print(f"Using simplified knowledge base components: {e}")
    from ui.knowledge_base_panel_simple import KnowledgeBasePanel
    from ui.knowledge_base_settings_simple import KnowledgeBaseSettingsDialog

# --- Settings Dialog ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(300)
        
        # Get current settings
        self.app_config = get_app_config()
        self.screens = get_available_screens()
        
        # Create form layout
        layout = QFormLayout(self)
        
        # Screen selection
        self.screen_combo = QComboBox()
        current_screen = self.app_config.get('screen_number', 1)
        
        for screen in self.screens:
            screen_text = f"Screen {screen['number']}: {screen['width']}x{screen['height']}"
            self.screen_combo.addItem(screen_text, screen['number'])
            
            # Select current screen
            if screen['number'] == current_screen:
                self.screen_combo.setCurrentIndex(self.screen_combo.count() - 1)
        
        layout.addRow("Screenshot Screen:", self.screen_combo)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)
    
    def get_settings(self):
        """Returns the selected settings"""
        screen_number = self.screen_combo.currentData()
        return {
            'screen_number': screen_number
        }

# --- Worker for Multithreading ---
class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.
    Supported signals are:
    - finished: No data
    - error: tuple (exctype, value, traceback.format_exc())
    - result: object data returned from processing, anything
    '''
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)

class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    '''
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit((type(e), e, e.__traceback__))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_pinned = True  # 默认置顶
        self.is_expanded = True  # 默认展开模式
        self.compact_width = 80
        self.expanded_width = 480 # compact_width + result_view_width
        self.window_height = 400
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(4)
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        self.setup_ui()
        # 不再隐藏结果视图，默认显示
        
        # Set up theme monitoring
        self.setup_theme_monitoring()
        
        # Ensure initial button styles are correct (after theme is applied)
        self.update_pin_button_style()
    
    def detect_dark_mode(self):
        """Detect if the system is using dark mode."""
        try:
            if sys.platform == 'win32':
                import winreg
                try:
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    return value == 0  # 0 means dark mode, 1 means light mode
                except:
                    pass
            
            # Fallback: check Qt palette
            palette = QApplication.palette()
            window_color = palette.color(palette.Window)
            return window_color.lightness() < 128
        except:
            return False  # Default to light mode if detection fails
    
    def apply_theme_styles(self):
        """Apply theme-aware styles based on dark/light mode."""
        if self.is_dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme styles."""
        # Dark theme colors
        bg_color = "rgba(45, 45, 45, 0.95)"
        border_color = "rgba(80, 80, 80, 0.8)"
        button_bg = "#404040"
        button_border = "#606060"
        button_hover = "#505050"
        button_pressed = "#353535"
        text_color = "#E0E0E0"
        input_bg = "#2D2D2D"
        input_border = "#555555"
        
        # Main window background
        self.central_widget.setStyleSheet(f"""
            QWidget#central_widget {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid {border_color};
            }}
        """)
        
        # Button styles
        self.base_button_style = f"""
            QPushButton {{
                font-size: 12px;
                background-color: {button_bg};
                border: 1px solid {button_border};
                border-radius: 8px;
                color: {text_color};
                padding: 5px;
                margin: 5px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {button_pressed};
            }}
        """
        
        # Icon bar style
        self.icon_bar_style = f"background-color: rgba(30, 30, 30, 0.8); border-radius: 0px;"
        
        # Input/text styles
        self.input_style = f"""
            border: 1px solid {input_border};
            padding: 5px;
            background-color: {input_bg};
            color: {text_color};
            border-radius: 5px;
        """
        
        self.readonly_input_style = f"""
            background-color: #3A3A3A;
            border: 1px solid {input_border};
            padding: 5px;
            color: {text_color};
            border-radius: 5px;
        """
        
        # Label style
        self.label_style = f"color: {text_color};"
        
        # Update button styles that depend on base_button_style
        self.capture_button_style = self.base_button_style.replace("12px", "16px")
        self.exit_button_style = self.base_button_style + """
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.6);
                color: white;
            }
        """
    
    def apply_light_theme(self):
        """Apply light theme styles."""
        # Light theme colors (original)
        bg_color = "rgba(240, 240, 240, 0.9)"
        border_color = "rgba(0, 0, 0, 0.1)"
        button_bg = "#EAEAEA"
        button_border = "#D0D0D0"
        button_hover = "#DCDCDC"
        button_pressed = "#C8C8C8"
        text_color = "#333"
        input_bg = "white"
        input_border = "#cccccc"
        
        # Main window background
        self.central_widget.setStyleSheet(f"""
            QWidget#central_widget {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid {border_color};
            }}
        """)
        
        # Button styles
        self.base_button_style = f"""
            QPushButton {{
                font-size: 12px;
                background-color: {button_bg};
                border: 1px solid {button_border};
                border-radius: 8px;
                color: {text_color};
                padding: 5px;
                margin: 5px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {button_pressed};
            }}
        """
        
        # Icon bar style
        self.icon_bar_style = "background-color: rgba(0, 0, 0, 0.05); border-radius: 0px;"
        
        # Input/text styles
        self.input_style = f"""
            border: 1px solid {input_border};
            padding: 5px;
            background-color: {input_bg};
            color: {text_color};
            border-radius: 5px;
        """
        
        self.readonly_input_style = f"""
            background-color: #f9f9f9;
            border: 1px solid {input_border};
            padding: 5px;
            color: {text_color};
            border-radius: 5px;
        """
        
        # Label style
        self.label_style = f"color: {text_color};"
        
        # Update button styles that depend on base_button_style
        self.capture_button_style = self.base_button_style.replace("12px", "16px")
        self.exit_button_style = self.base_button_style + """
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.6);
                color: white;
            }
        """
    
    def update_all_styles(self):
        """Update all component styles after theme change."""
        if hasattr(self, 'central_widget'):
            # Update main window
            self.apply_theme_styles()
            
            # Update icon bar
            if hasattr(self, 'icon_bar_widget'):
                self.icon_bar_widget.setStyleSheet(self.icon_bar_style)
            
            # Update buttons
            button_components = [
                'capture_button', 'pin_button', 'knowledge_base_button', 
                'settings_button', 'exit_button', 'get_answer_button', 'copy_answer_button'
            ]
            
            for button_name in button_components:
                if hasattr(self, button_name):
                    button = getattr(self, button_name)
                    if button_name == 'capture_button':
                        button.setStyleSheet(self.capture_button_style)
                    elif button_name == 'exit_button':
                        button.setStyleSheet(self.exit_button_style)
                    elif button_name == 'pin_button':
                        if self.is_pinned:
                            button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
                        else:
                            button.setStyleSheet(self.base_button_style + "QPushButton { color: dimgray; }")
                    elif button_name in ['knowledge_base_button', 'settings_button']:
                        button.setStyleSheet(self.base_button_style + "QPushButton { font-size: 20px; }")
                    else:
                        button.setStyleSheet(self.base_button_style)
            
            # Update text inputs
            if hasattr(self, 'question_input'):
                self.question_input.setStyleSheet(self.input_style)
            if hasattr(self, 'answer_display'):
                self.answer_display.setStyleSheet(self.readonly_input_style)
            
            # Update labels
            label_components = ['question_label', 'answer_label']
            for label_name in label_components:
                if hasattr(self, label_name):
                    getattr(self, label_name).setStyleSheet(self.label_style)
            
            # Update checkboxes
            checkbox_style = f"QCheckBox {{ {self.label_style} }} QCheckBox::indicator {{ width: 15px; height: 15px; }}"
            if hasattr(self, 'force_search_checkbox'):
                self.force_search_checkbox.setStyleSheet(checkbox_style)
            if hasattr(self, 'direct_mode_checkbox'):
                self.direct_mode_checkbox.setStyleSheet(checkbox_style)
    
    def setup_theme_monitoring(self):
        """Set up monitoring for theme changes."""
        from PySide6.QtCore import QTimer
        
        self.theme_check_timer = QTimer()
        self.theme_check_timer.timeout.connect(self.check_theme_change)
        self.theme_check_timer.start(2000)  # Check every 2 seconds
    
    def check_theme_change(self):
        """Check if the system theme has changed."""
        current_dark_mode = self.detect_dark_mode()
        if current_dark_mode != self.is_dark_mode:
            print(f"Theme changed: {'Dark' if current_dark_mode else 'Light'} mode detected")
            self.is_dark_mode = current_dark_mode
            self.update_all_styles()
    
    def update_pin_button_style(self):
        """Update pin button style based on current state."""
        if hasattr(self, 'pin_button'):
            if self.is_pinned:
                self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
            else:
                self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: dimgray; }")

    def setup_ui(self):
        self.setWindowTitle("QuizGazer")
        # 初始化时设置基本窗口标志 - 移除Tool标志，使用Window标志
        # 根据初始置顶状态设置窗口标志
        flags = Qt.FramelessWindowHint | Qt.Window
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置窗口为DPI感知
        if sys.platform == 'win32':
            self.setAttribute(Qt.WA_NativeWindow)
        self.setGeometry(100, 100, self.expanded_width, self.window_height)  # 默认使用展开宽度

        # Detect dark mode
        self.is_dark_mode = self.detect_dark_mode()
        
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # Use QHBoxLayout for side-by-side icon bar and result view
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Apply theme-aware styles
        self.apply_theme_styles()
        self.central_widget.setObjectName("central_widget")


        # --- Common Styles (now set by theme) ---
        # Button styles are now defined in theme methods

        # --- Left Icon Bar ---
        self.icon_bar_widget = QWidget()
        self.icon_bar_widget.setFixedWidth(self.compact_width)
        self.icon_bar_widget.setStyleSheet(self.icon_bar_style)
        icon_layout = QVBoxLayout(self.icon_bar_widget)
        icon_layout.setContentsMargins(10,10,10,10)
        
        self.capture_button = QPushButton("📸")
        self.capture_button.setFixedSize(50, 50)
        self.capture_button.setStyleSheet(self.capture_button_style)
        
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(30, 30)
        self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
        
        self.knowledge_base_button = QPushButton("📚")
        self.knowledge_base_button.setFixedSize(40, 40)
        self.knowledge_base_button.setStyleSheet(self.base_button_style + "QPushButton { font-size: 20px; }")
        self.knowledge_base_button.setToolTip("知识库")
        
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.setStyleSheet(self.base_button_style + "QPushButton { font-size: 20px; }")
        
        self.exit_button = QPushButton("✕")
        self.exit_button.setFixedSize(30, 30)
        self.exit_button.setStyleSheet(self.exit_button_style)

        icon_layout.addWidget(self.capture_button, alignment=Qt.AlignTop | Qt.AlignHCenter)
        icon_layout.addWidget(self.pin_button, alignment=Qt.AlignTop | Qt.AlignHCenter)
        
        self.force_search_checkbox = QCheckBox("🌐")
        checkbox_style = f"QCheckBox {{ {self.label_style} }} QCheckBox::indicator {{ width: 15px; height: 15px; }}"
        self.force_search_checkbox.setStyleSheet(checkbox_style)
        self.force_search_checkbox.setToolTip("强制使用搜索工具")
        icon_layout.addWidget(self.force_search_checkbox, alignment=Qt.AlignTop | Qt.AlignHCenter)

        self.direct_mode_checkbox = QCheckBox("👁️")
        self.direct_mode_checkbox.setStyleSheet(checkbox_style)
        self.direct_mode_checkbox.setToolTip("直接模式：适用于包含图形、图表的题目")
        icon_layout.addWidget(self.direct_mode_checkbox, alignment=Qt.AlignTop | Qt.AlignHCenter)

        icon_layout.addStretch()
        icon_layout.addWidget(self.knowledge_base_button, alignment=Qt.AlignBottom | Qt.AlignHCenter)
        icon_layout.addWidget(self.settings_button, alignment=Qt.AlignBottom | Qt.AlignHCenter)
        icon_layout.addWidget(self.exit_button, alignment=Qt.AlignBottom | Qt.AlignHCenter)
        
        # --- Right Result View with Tabs ---
        self.result_view_widget = QWidget()
        result_view_layout = QVBoxLayout(self.result_view_widget)
        result_view_layout.setContentsMargins(10,10,10,10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Main tab (original functionality)
        self.main_tab = QWidget()
        main_tab_layout = QVBoxLayout(self.main_tab)
        
        self.question_label = QLabel("Question (editable):")
        self.question_label.setStyleSheet(self.label_style)
        self.question_input = QTextEdit()
        self.question_input.setStyleSheet(self.input_style)
        
        self.answer_label = QLabel("Answer:")
        self.answer_label.setStyleSheet(self.label_style)
        self.answer_display = QTextEdit()
        self.answer_display.setReadOnly(True)
        self.answer_display.setStyleSheet(self.readonly_input_style)
        
        # Bottom button layout for main tab
        bottom_button_layout = QHBoxLayout()
        self.get_answer_button = QPushButton("Get New Answer")
        self.copy_answer_button = QPushButton("Copy Answer")
        
        self.get_answer_button.setStyleSheet(self.base_button_style)
        self.copy_answer_button.setStyleSheet(self.base_button_style)

        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.get_answer_button)
        bottom_button_layout.addWidget(self.copy_answer_button)

        main_tab_layout.addWidget(self.question_label)
        main_tab_layout.addWidget(self.question_input)
        main_tab_layout.addWidget(self.answer_label)
        main_tab_layout.addWidget(self.answer_display)
        main_tab_layout.addLayout(bottom_button_layout)
        
        # Knowledge base tab
        self.knowledge_base_tab = KnowledgeBasePanel()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.main_tab, "问答")
        self.tab_widget.addTab(self.knowledge_base_tab, "知识库")
        
        result_view_layout.addWidget(self.tab_widget)

        # Add widgets to main layout
        self.main_layout.addWidget(self.icon_bar_widget)
        self.main_layout.addWidget(self.result_view_widget)

        # Connect signals
        self.capture_button.clicked.connect(self.on_capture_clicked)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.knowledge_base_button.clicked.connect(self.show_knowledge_base)
        self.settings_button.clicked.connect(self.show_settings)
        self.exit_button.clicked.connect(QApplication.instance().quit)
        self.get_answer_button.clicked.connect(self.get_new_answer)
        self.copy_answer_button.clicked.connect(self.copy_answer)
        
        # 确保窗口在初始化时正确设置为置顶
        # 这部分代码将在窗口显示后通过showEvent处理

        # Make window draggable
        self.old_pos = self.pos()

    def on_capture_clicked(self):
        # 保存当前窗口位置
        current_pos = self.pos()
        
        # 临时隐藏窗口进行截图
        self.setWindowOpacity(0)  # 使用透明度而不是完全隐藏
        QApplication.processEvents() # 确保窗口透明化生效
        
        screenshot_bytes = take_screenshot()
        
        # 恢复窗口
        self.setWindowOpacity(1)
        self.move(current_pos)  # 确保窗口位置不变
        
        if not screenshot_bytes:
            return

        # 检查是否使用直接模式
        if self.direct_mode_checkbox.isChecked():
            # 直接模式：一步到位获取答案
            self.question_input.setPlainText("正在直接分析图片并获取答案...")
            self.answer_display.setText("Please wait...")

            force_search = self.force_search_checkbox.isChecked()
            worker = Worker(get_direct_answer_from_image, screenshot_bytes, force_search=force_search)
            worker.signals.result.connect(self.on_direct_answer_ready)
            worker.signals.error.connect(self.on_ai_error)
            self.threadpool.start(worker)
        else:
            # 传统模式：先提取问题，再获取答案
            self.question_input.setPlainText("Extracting question from image...")
            self.answer_display.setText("Please wait...")

            worker = Worker(get_question_from_image, screenshot_bytes)
            worker.signals.result.connect(self.on_question_ready)
            worker.signals.error.connect(self.on_ai_error)
            self.threadpool.start(worker)

    def on_question_ready(self, question_text):
        """Handles the result from get_question_from_image."""
        self.question_input.setPlainText(question_text)

        # 检查VLM是否成功识别到问题
        # 如果返回空列表或错误信息，不自动请求LLM
        if self._should_skip_llm_request(question_text):
            self.answer_display.setText("未识别到问题，请检查图片内容或手动输入问题。")
            return

        self.get_initial_answer()  # 自动获取答案

    def _should_skip_llm_request(self, question_text):
        """判断是否应该跳过LLM请求"""
        if not question_text or not question_text.strip():
            return True

        # 检查是否为空JSON数组
        stripped_text = question_text.strip()
        if stripped_text == "[]":
            return True

        return False

    def on_direct_answer_ready(self, answer_text):
        """处理直接模式的答案结果"""
        self.question_input.setPlainText("直接模式：已分析图片内容")
        self.answer_display.setText(answer_text)

    def on_answer_ready(self, answer_text):
        """Handles the result from get_answer_from_text."""
        self.answer_display.setText(answer_text)

    def on_ai_error(self, error_tuple):
        """Handles errors from AI services."""
        print("AI Error:", error_tuple)
        self.answer_display.setText(f"An error occurred: {error_tuple}")

    def show_result_view(self, initial_question_text=""):
        # 如果已经是展开状态，只更新文本
        if self.is_expanded:
            if initial_question_text:
                self.question_input.setPlainText(initial_question_text)
                self.answer_display.setText("Getting answer...")
            return
            
        # 否则展开UI
        self.is_expanded = True
        self.result_view_widget.show()
        if initial_question_text:
            self.question_input.setPlainText(initial_question_text)
            self.answer_display.setText("Getting answer...")
        self.animate_size(QSize(self.expanded_width, self.window_height))

    def hide_result_view(self, animated=True):
        # 在新的设计中，我们不再隐藏结果视图，而是切换到紧凑模式
        if not self.is_expanded:
            return
            
        self.is_expanded = False
        if animated:
            self.animate_size(QSize(self.compact_width, self.window_height))
        else:
            self.resize(self.compact_width, self.window_height)
        self.result_view_widget.hide()

    def get_initial_answer(self):
        question = self.question_input.toPlainText()
        if not question.strip() or "Extracting" in question:
            return
        self.answer_display.setText("Getting answer...")
        
        force_search = self.force_search_checkbox.isChecked()
        worker = Worker(get_answer_from_text, question, force_search=force_search)
        worker.signals.result.connect(self.on_answer_ready)
        worker.signals.error.connect(self.on_ai_error)
        self.threadpool.start(worker)

    def get_new_answer(self):
        question = self.question_input.toPlainText()
        if not question.strip():
            self.answer_display.setText("Please enter a question.")
            return
            
        self.answer_display.setText("Getting new answer...")
        
        force_search = self.force_search_checkbox.isChecked()
        worker = Worker(get_answer_from_text, question, force_search=force_search)
        worker.signals.result.connect(self.on_answer_ready)
        worker.signals.error.connect(self.on_ai_error)
        self.threadpool.start(worker)

    def copy_answer(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.answer_display.toPlainText())

    def animate_size(self, size):
        self.animation = QPropertyAnimation(self, b"size")
        self.animation.setDuration(250)
        self.animation.setEndValue(size)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        self.animation.start()

    def set_window_pin_state(self, pin_state):
        """设置窗口的置顶状态（主要用于初始化）"""
        # 保存当前状态
        old_state = self.is_pinned
        
        # 设置新状态
        self.is_pinned = pin_state
        
        # 如果状态不同，调用toggle_pin来设置
        if old_state != pin_state:
            # 恢复状态，因为toggle_pin会反转它
            self.is_pinned = not pin_state
            self.toggle_pin()
        else:
            # 状态相同，只更新按钮样式
            if pin_state:
                self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
            else:
                self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: dimgray; }")
    
    def toggle_pin(self):
        """切换窗口置顶状态"""
        self.is_pinned = not self.is_pinned
        
        # 更新按钮样式
        self.update_pin_button_style()
        
        # 在Windows上使用更可靠的方法
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            
            try:
                hwnd = int(self.winId())
                
                # 保存当前位置和大小
                current_pos = self.pos()
                current_size = self.size()
                
                if self.is_pinned:
                    # 设置为置顶窗口
                    print("Setting window to topmost...")
                    
                    # 使用Qt方法设置窗口标志
                    flags = self.windowFlags()
                    flags |= Qt.WindowStaysOnTopHint
                    self.setWindowFlags(flags)
                    self.show()
                    
                    # 使用Windows API强制置顶
                    result = ctypes.windll.user32.SetWindowPos(
                        hwnd, -1,  # HWND_TOPMOST
                        0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
                    )
                    print(f"Set topmost result: {result}")
                    
                else:
                    # 取消置顶
                    print("Setting window to normal z-order...")
                    
                    # 使用Qt方法移除窗口标志
                    flags = self.windowFlags()
                    flags &= ~Qt.WindowStaysOnTopHint
                    self.setWindowFlags(flags)
                    self.show()
                    
                    # 使用Windows API确保取消置顶
                    result = ctypes.windll.user32.SetWindowPos(
                        hwnd, -2,  # HWND_NOTOPMOST
                        0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
                    )
                    print(f"Remove topmost result: {result}")
                
                # 恢复窗口位置和大小
                self.resize(current_size)
                self.move(current_pos)
                    
            except Exception as e:
                print(f"Windows API error: {e}")
                # 如果API失败，回退到Qt方法
                self._toggle_pin_qt()
        else:
            # 非Windows系统使用Qt方法
            self._toggle_pin_qt()
            
    def _toggle_pin_qt(self):
        """使用Qt方法切换窗口置顶状态（备用方法）"""
        # 保存当前位置和大小
        current_pos = self.pos()
        current_size = self.size()
            
        # 使用Qt标准方法
        flags = self.windowFlags()
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
            print("Qt: Window set to stay on top")
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            print("Qt: Window set to normal z-order")
        
        # 应用新标志并恢复位置和大小
        self.setWindowFlags(flags)
        self.show()
        self.resize(current_size)
        self.move(current_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Allow dragging from anywhere on the window
            # Store the cursor position relative to the window
            self.drag_position = event.position().toPoint()
            event.accept()


    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            # Move window to new position
            global_pos = event.globalPosition().toPoint()
            self.move(global_pos - self.drag_position)
            event.accept()
            
    def showEvent(self, event):
        """窗口显示事件，用于确保窗口在显示后正确设置置顶状态"""
        super().showEvent(event)
        
        # 窗口显示后，使用定时器延迟设置置顶状态，确保窗口完全初始化
        if sys.platform == 'win32' and self.is_pinned:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._ensure_topmost)  # 延迟100ms执行
            
    def _ensure_topmost(self):
        """确保窗口置顶的辅助方法"""
        if not self.is_pinned:
            return
            
        import ctypes
        try:
            hwnd = int(self.winId())
            
            # 多步骤确保窗口置顶
            print("Ensuring window is topmost...")
            
            # 1. 设置为TOPMOST
            result1 = ctypes.windll.user32.SetWindowPos(
                hwnd, -1,  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
            )
            
            # 2. 激活窗口
            ctypes.windll.user32.SetActiveWindow(hwnd)
            
            # 3. 设置为前台窗口
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            
            # 4. 再次确认TOPMOST
            result2 = ctypes.windll.user32.SetWindowPos(
                hwnd, -1,  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0010  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
            )
            
            print(f"Ensure topmost results: {result1}, {result2}")
            
            # 验证窗口状态
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            is_topmost = (ex_style & 0x00000008) != 0  # WS_EX_TOPMOST
            print(f"Window topmost status: {is_topmost}")
            
        except Exception as e:
            print(f"Ensure topmost error: {e}")
            
    def show_knowledge_base(self):
        """Switch to knowledge base tab"""
        self.tab_widget.setCurrentIndex(1)  # Switch to knowledge base tab
    
    def show_settings(self):
        """Shows the settings dialog"""
        # Create a menu to choose between general settings and knowledge base settings
        from PySide6.QtWidgets import QMenu
        from PySide6.QtCore import QPoint
        
        menu = QMenu(self)
        general_action = menu.addAction("常规设置")
        kb_action = menu.addAction("知识库设置")
        
        # Show menu at button position
        button_pos = self.settings_button.mapToGlobal(QPoint(0, self.settings_button.height()))
        action = menu.exec(button_pos)
        
        if action == general_action:
            dialog = SettingsDialog(self)
            if dialog.exec():
                # Save settings if dialog was accepted
                settings = dialog.get_settings()
                save_app_config(settings)
        elif action == kb_action:
            dialog = KnowledgeBaseSettingsDialog(self)
            dialog.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion")) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec())