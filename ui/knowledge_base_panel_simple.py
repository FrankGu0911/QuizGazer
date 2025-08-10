"""
Simplified Knowledge Base Panel - Temporary version for testing.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class KnowledgeBasePanel(QWidget):
    """Simplified knowledge base panel for testing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("知识库")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Status
        status_label = QLabel("知识库功能暂时不可用")
        status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        # Placeholder content
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setPlainText(
            "知识库功能正在开发中...\n\n"
            "功能包括:\n"
            "- 文档上传和管理\n"
            "- 智能搜索和检索\n"
            "- 集合管理\n"
            "- RAG问答增强\n\n"
            "请等待后续版本更新。"
        )
        
        # Placeholder button
        placeholder_button = QPushButton("功能开发中")
        placeholder_button.setEnabled(False)
        
        layout.addWidget(title_label)
        layout.addWidget(status_label)
        layout.addWidget(content_text)
        layout.addWidget(placeholder_button)
        layout.addStretch()