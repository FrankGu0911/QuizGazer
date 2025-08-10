"""
Simplified Knowledge Base Settings Dialog - Temporary version for testing.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class KnowledgeBaseSettingsDialog(QDialog):
    """Simplified knowledge base settings dialog for testing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("知识库设置")
        self.setMinimumSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("知识库设置")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Status
        status_label = QLabel("知识库设置功能暂时不可用")
        status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        # Info
        info_label = QLabel(
            "知识库设置包括:\n\n"
            "• API配置 (OpenAI, Azure, 等)\n"
            "• 向量数据库设置\n"
            "• 缓存配置\n"
            "• 性能参数调整\n\n"
            "这些功能正在开发中，请等待后续版本更新。"
        )
        info_label.setWordWrap(True)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        layout.addWidget(title_label)
        layout.addWidget(status_label)
        layout.addWidget(info_label)
        layout.addStretch()
        layout.addWidget(button_box)