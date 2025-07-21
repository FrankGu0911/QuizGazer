import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QFrame, QCheckBox,QStyleFactory 
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
        self.compact_width = 80
        self.expanded_width = 480 # compact_width + result_view_width
        self.window_height = 400
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        self.setup_ui()
        self.result_view_widget.hide() # Start in compact mode

    def setup_ui(self):
        self.setWindowTitle("QuizGazer")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, self.compact_width, self.window_height)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # Use QHBoxLayout for side-by-side icon bar and result view
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Style for the window background
        self.central_widget.setStyleSheet("""
            QWidget#central_widget {
                background-color: rgba(240, 240, 240, 0.9);
                border-radius: 10px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.central_widget.setObjectName("central_widget")


        # --- Common Styles ---
        self.base_button_style = """
            QPushButton {
                font-size: 16px;
                background-color: #EAEAEA; /* Light gray background */
                border: 1px solid #D0D0D0; /* Light border */
                border-radius: 8px;
                color: #333; /* Dark text */
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #DCDCDC; /* Slightly darker on hover */
            }
            QPushButton:pressed {
                background-color: #C8C8C8; /* Darker when pressed */
            }
        """
        self.capture_button_style = self.base_button_style.replace("15px", "25px").replace("16px", "24px")
        self.exit_button_style = self.base_button_style + """
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.6);
                color: white;
            }
        """

        # --- Left Icon Bar ---
        self.icon_bar_widget = QWidget()
        self.icon_bar_widget.setFixedWidth(self.compact_width)
        self.icon_bar_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0.05); border-radius: 0px;")
        icon_layout = QVBoxLayout(self.icon_bar_widget)
        icon_layout.setContentsMargins(10,10,10,10)
        
        self.capture_button = QPushButton("📸")
        self.capture_button.setFixedSize(50, 50)
        self.capture_button.setStyleSheet(self.capture_button_style)
        
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(30, 30)
        self.pin_button.setStyleSheet(self.base_button_style + "QPushButton { color: green; }")
        
        self.exit_button = QPushButton("✕")
        self.exit_button.setFixedSize(30, 30)
        self.exit_button.setStyleSheet(self.exit_button_style)

        icon_layout.addWidget(self.capture_button, alignment=Qt.AlignTop | Qt.AlignHCenter)
        icon_layout.addWidget(self.pin_button, alignment=Qt.AlignTop | Qt.AlignHCenter)
        
        self.force_search_checkbox = QCheckBox("🌐")
        self.force_search_checkbox.setStyleSheet("QCheckBox { color: #333; } QCheckBox::indicator { width: 15px; height: 15px; }")
        icon_layout.addWidget(self.force_search_checkbox, alignment=Qt.AlignTop | Qt.AlignHCenter)

        icon_layout.addStretch()
        icon_layout.addWidget(self.exit_button, alignment=Qt.AlignBottom | Qt.AlignHCenter)
        
        # --- Right Result View ---
        self.result_view_widget = QWidget()
        result_view_layout = QVBoxLayout(self.result_view_widget)
        result_view_layout.setContentsMargins(10,10,10,10)

        question_label = QLabel("Question (editable):")
        question_label.setStyleSheet("color: #333;")
        self.question_input = QTextEdit()
        self.question_input.setStyleSheet("border: 1px solid #cccccc; padding: 5px; background-color: white; color: #333; border-radius: 5px;")
        
        answer_label = QLabel("Answer:")
        answer_label.setStyleSheet("color: #333;")
        self.answer_display = QTextEdit()
        self.answer_display.setReadOnly(True)
        self.answer_display.setStyleSheet("background-color: #f9f9f9; border: 1px solid #cccccc; padding: 5px; color: #333; border-radius: 5px;")
        
        # Bottom button layout for result view
        bottom_button_layout = QHBoxLayout()
        self.get_answer_button = QPushButton("Get New Answer")
        self.copy_answer_button = QPushButton("Copy Answer")
        self.back_button = QPushButton("Back")
        
        self.get_answer_button.setStyleSheet(self.base_button_style)
        self.copy_answer_button.setStyleSheet(self.base_button_style)
        self.back_button.setStyleSheet(self.base_button_style)

        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.get_answer_button)
        bottom_button_layout.addWidget(self.copy_answer_button)
        bottom_button_layout.addWidget(self.back_button)

        result_view_layout.addWidget(question_label)
        result_view_layout.addWidget(self.question_input)
        result_view_layout.addWidget(answer_label)
        result_view_layout.addWidget(self.answer_display)
        result_view_layout.addLayout(bottom_button_layout)

        # Add widgets to main layout
        self.main_layout.addWidget(self.icon_bar_widget)
        self.main_layout.addWidget(self.result_view_widget)

        # Connect signals
        self.capture_button.clicked.connect(self.on_capture_clicked)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.exit_button.clicked.connect(QApplication.instance().quit)
        self.get_answer_button.clicked.connect(self.get_new_answer)
        self.copy_answer_button.clicked.connect(self.copy_answer)
        self.back_button.clicked.connect(self.hide_result_view)

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
        self.question_input.setPlainText(question_text)
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
            self.question_input.setPlainText(initial_question_text)
            self.answer_display.setText("Getting answer...")
            return
            
        self.is_expanded = True
        self.result_view_widget.show()
        self.question_input.setPlainText(initial_question_text)
        self.answer_display.setText("Getting answer...")
        self.animate_size(QSize(self.expanded_width, self.window_height))
        
        self.get_initial_answer()

    def hide_result_view(self, animated=True):
        if not self.is_expanded and not animated:
             self.resize(self.compact_width, self.window_height)
             self.result_view_widget.hide()
             return

        if not self.is_expanded:
            return

        self.is_expanded = False
        self.result_view_widget.hide()
        if animated:
            self.animate_size(QSize(self.compact_width, self.window_height))
        else:
            self.resize(self.compact_width, self.window_height)

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
            # Check if the press is on the icon bar to allow dragging
            if self.icon_bar_widget.geometry().contains(event.pos()):
                 self.old_pos = event.globalPosition().toPoint()
                 event.accept()
            else:
                event.ignore()


    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion")) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec())