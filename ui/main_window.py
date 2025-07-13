import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QIcon, QClipboard

from core.screenshot_handler import take_screenshot
from core.ai_services import get_question_from_image, get_answer_from_text

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_pinned = True
        self.is_expanded = False
        self.compact_size = QSize(80, 160)
        self.expanded_size = QSize(400, 350)
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
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                border: 1px solid rgba(0, 0, 0, 0.2);
            }
        """)

        # --- Icon View Widgets ---
        self.icon_view_widget = QWidget()
        self.icon_view_widget.setStyleSheet("background-color: transparent; border: none;")
        icon_layout = QVBoxLayout(self.icon_view_widget)
        icon_layout.setContentsMargins(0,0,0,0)
        
        self.capture_button = QPushButton("📸")
        self.capture_button.setFixedSize(50, 50)
        self.capture_button.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 25px;
                color: black;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(30, 30)
        self.pin_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 15px;
                color: green; /* Pinned state */
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        self.exit_button_compact = QPushButton("✕")
        self.exit_button_compact.setFixedSize(30, 30)
        self.exit_button_compact.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 15px;
                color: black;
            }
            QPushButton:hover {
                background-color: rgba(200, 0, 0, 0.4);
            }
        """)

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
        self.back_button = QPushButton("Back") # Renamed from close_button
        self.exit_button_expanded = QPushButton("Exit")
        button_layout.addStretch()
        button_layout.addWidget(self.get_answer_button)
        button_layout.addWidget(self.copy_answer_button)
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
        self.back_button.clicked.connect(self.hide_result_view)
        self.exit_button_compact.clicked.connect(QApplication.instance().quit)
        self.exit_button_expanded.clicked.connect(QApplication.instance().quit)

        # Make window draggable
        self.old_pos = self.pos()

    def on_capture_clicked(self):
        self.hide()
        QApplication.processEvents()
        
        screenshot_bytes = take_screenshot()
        question_text = get_question_from_image(screenshot_bytes)
        
        self.show()
        self.show_result_view(question_text)

    def show_result_view(self, question_text):
        if self.is_expanded:
            return
        self.is_expanded = True
        
        self.question_input.setText(question_text)
        self.answer_display.setText("Getting answer...")
        QApplication.processEvents()

        self.icon_view_widget.setVisible(False)
        self.result_view_widget.setVisible(True)
        
        self.animate_size(self.expanded_size)
        
        self.get_initial_answer()

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
        answer = get_answer_from_text(self.question_input.text())
        self.answer_display.setText(answer)

    def get_new_answer(self):
        question = self.question_input.text()
        if not question.strip():
            self.answer_display.setText("Please enter a question.")
            return
        self.answer_display.setText("Getting new answer...")
        QApplication.processEvents()
        answer = get_answer_from_text(question)
        self.answer_display.setText(answer)

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
            self.pin_button.setStyleSheet(self.pin_button.styleSheet().replace("color: dimgray;", "color: green;"))
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.pin_button.setStyleSheet(self.pin_button.styleSheet().replace("color: green;", "color: dimgray;"))
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