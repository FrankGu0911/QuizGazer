import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import (Qt, QPoint, QPropertyAnimation, QEasingCurve, QSize,
                            QRunnable, Slot, Signal, QObject, QThreadPool)
from PySide6.QtGui import QIcon, QClipboard

from core.screenshot_handler import take_screenshot
from core.ai_services import get_question_from_image, get_answer_from_text

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
        self.is_pinned = True
        self.is_expanded = False
        self.compact_size = QSize(80, 160)
        self.expanded_size = QSize(400, 350)
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        self.setup_ui()
        self.hide_result_view(animated=False) # Start in compact mode

    def setup_ui(self):
        self.setWindowTitle("QuizGazer")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, self.compact_size.width(), self.compact_size.height())

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Style for the window background
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(240, 240, 240, 0.85);
                border-radius: 10px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)

        # --- Common Styles ---
        self.base_button_style = """
            QPushButton {{
                font-size: 16px;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 15px;
                color: #333;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 0, 0, 0.15);
            }}
        """
        self.capture_button_style = self.base_button_style.replace("15px", "25px").replace("16px", "24px")
        self.exit_button_style = self.base_button_style + """
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.6);
                color: white;
            }
        """

        # --- Icon View Widgets ---
        self.icon_view_widget = QWidget()
        self.icon_view_widget.setStyleSheet("background-color: transparent; border: none;")
        icon_layout = QVBoxLayout(self.icon_view_widget)
        icon_layout.setContentsMargins(0,0,0,0)
        
        self.capture_button = QPushButton("📸")
        self.capture_button.setFixedSize(50, 50)
        self.capture_button.setStyleSheet(self.capture_button_style)
        
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(30, 30)
        self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
        
        self.exit_button_compact = QPushButton("✕")
        self.exit_button_compact.setFixedSize(30, 30)
        self.exit_button_compact.setStyleSheet(self.exit_button_style)

        icon_layout.addWidget(self.capture_button, alignment=Qt.AlignCenter)
        icon_layout.addWidget(self.pin_button, alignment=Qt.AlignCenter)
        icon_layout.addWidget(self.exit_button_compact, alignment=Qt.AlignCenter)
        
        # --- Result View Widgets (initially hidden) ---
        self.result_view_widget = QWidget()
        self.result_view_widget.setStyleSheet("background-color: transparent; border: none;")
        result_layout = QVBoxLayout(self.result_view_widget)
        result_layout.setContentsMargins(0,0,0,0)

        question_label = QLabel("Question (editable):")
        self.question_input = QLineEdit()
        self.question_input.setStyleSheet("border: 1px solid #cccccc; padding: 5px; background-color: white; border-radius: 5px;")

        answer_label = QLabel("Answer:")
        self.answer_display = QTextEdit()
        self.answer_display.setReadOnly(True)
        self.answer_display.setStyleSheet("background-color: #f9f9f9; border: 1px solid #cccccc; padding: 5px; border-radius: 5px;")

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        button_layout = QHBoxLayout()
        self.get_answer_button = QPushButton("Get New Answer")
        self.copy_answer_button = QPushButton("Copy Answer")
        self.continue_button = QPushButton("Continue") # New button
        self.back_button = QPushButton("Back")
        self.exit_button_expanded = QPushButton("Exit")

        # Apply common style to result view buttons
        self.get_answer_button.setStyleSheet(self.base_button_style)
        self.copy_answer_button.setStyleSheet(self.base_button_style)
        self.continue_button.setStyleSheet(self.base_button_style)
        self.back_button.setStyleSheet(self.base_button_style)
        self.exit_button_expanded.setStyleSheet(self.exit_button_style)
        
        button_layout.addStretch()
        button_layout.addWidget(self.get_answer_button)
        button_layout.addWidget(self.copy_answer_button)
        button_layout.addWidget(self.continue_button)
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.exit_button_expanded)

        result_layout.addWidget(question_label)
        result_layout.addWidget(self.question_input)
        result_layout.addWidget(answer_label)
        result_layout.addWidget(self.answer_display)
        result_layout.addWidget(separator)
        result_layout.addLayout(button_layout)

        # Add both views to the main layout
        self.layout.addWidget(self.icon_view_widget)
        self.layout.addWidget(self.result_view_widget)

        # Connect signals
        self.capture_button.clicked.connect(self.on_capture_clicked)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.get_answer_button.clicked.connect(self.get_new_answer)
        self.copy_answer_button.clicked.connect(self.copy_answer)
        self.continue_button.clicked.connect(self.on_capture_clicked) # Connect to capture
        self.back_button.clicked.connect(self.hide_result_view)
        self.exit_button_compact.clicked.connect(QApplication.instance().quit)
        self.exit_button_expanded.clicked.connect(QApplication.instance().quit)

        # Make window draggable
        self.old_pos = self.pos()

    def on_capture_clicked(self):
        self.hide()
        QApplication.processEvents() # Ensure window is hidden before screenshot
        
        screenshot_bytes = take_screenshot()
        if not screenshot_bytes:
            self.show()
            return

        self.show()
        self.show_result_view("Extracting question from image...")

        # Run get_question_from_image in a worker thread
        worker = Worker(get_question_from_image, screenshot_bytes)
        worker.signals.result.connect(self.on_question_ready)
        worker.signals.error.connect(self.on_ai_error)
        self.threadpool.start(worker)

    def on_question_ready(self, question_text):
        """Handles the result from get_question_from_image."""
        self.question_input.setText(question_text)
        self.get_initial_answer()

    def on_answer_ready(self, answer_text):
        """Handles the result from get_answer_from_text."""
        self.answer_display.setText(answer_text)

    def on_ai_error(self, error_tuple):
        """Handles errors from AI services."""
        print("AI Error:", error_tuple)
        self.answer_display.setText(f"An error occurred: {error_tuple}")

    def show_result_view(self, initial_question_text=""):
        if self.is_expanded:
            self.question_input.setText(initial_question_text)
            self.answer_display.setText("Getting answer...")
            return
            
        self.is_expanded = True
        
        self.question_input.setText(initial_question_text)
        self.answer_display.setText("Getting answer...")

        self.icon_view_widget.setVisible(False)
        self.result_view_widget.setVisible(True)
        
        self.animate_size(self.expanded_size)

    def hide_result_view(self, animated=True):
        if not self.is_expanded and animated:
            return
        self.is_expanded = False
        
        self.icon_view_widget.setVisible(True)
        self.result_view_widget.setVisible(False)
        if animated:
            self.animate_size(self.compact_size)
        else:
            self.resize(self.compact_size)

    def get_initial_answer(self):
        question = self.question_input.text()
        if not question.strip() or "Extracting" in question:
            return # Don't get answer if question is not ready
        self.answer_display.setText("Getting answer...")
        
        worker = Worker(get_answer_from_text, question)
        worker.signals.result.connect(self.on_answer_ready)
        worker.signals.error.connect(self.on_ai_error)
        self.threadpool.start(worker)

    def get_new_answer(self):
        question = self.question_input.text()
        if not question.strip():
            self.answer_display.setText("Please enter a question.")
            return
            
        self.answer_display.setText("Getting new answer...")
        
        worker = Worker(get_answer_from_text, question)
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

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: dimgray; }")
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())