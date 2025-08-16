"""
Knowledge Base Panel - UI components for knowledge base management.
"""

import os
import sys
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextEdit, QLineEdit, QComboBox, QProgressBar,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QCheckBox, QGroupBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QIcon

# Import knowledge base services
try:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core import ai_services
    from core.knowledge_base.models import DocumentType
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Knowledge base not available: {e}")
    KNOWLEDGE_BASE_AVAILABLE = False
    # Create a mock DocumentType for when knowledge base is not available

    class DocumentType:
        KNOWLEDGE_DOCUMENT = "knowledge_document"
        QUESTION_BANK = "question_bank"


class DocumentUploadDialog(QDialog):
    """Dialog for uploading documents to knowledge base."""

    def __init__(self, collections: List = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("上传文档")
        self.setMinimumSize(550, 450)
        self.resize(650, 500)
        self.collections = collections or []
        self.selected_files = []

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox("选择文件")
        file_layout = QVBoxLayout(file_group)

        file_button_layout = QHBoxLayout()
        self.select_files_button = QPushButton("选择文件...")
        self.select_files_button.clicked.connect(self.select_files)
        file_button_layout.addWidget(self.select_files_button)
        file_button_layout.addStretch()

        self.files_list = QListWidget()
        self.files_list.setMinimumHeight(120)
        self.files_list.setMaximumHeight(150)

        file_layout.addLayout(file_button_layout)
        file_layout.addWidget(self.files_list)

        # Document type selection
        type_group = QGroupBox("文档类型")
        type_layout = QVBoxLayout(type_group)

        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItem("知识文档 (PDF, Markdown)", "knowledge")
        self.doc_type_combo.addItem("题库 (CSV)", "question_bank")

        type_layout.addWidget(self.doc_type_combo)

        # Collection selection
        collection_group = QGroupBox("目标集合")
        collection_layout = QVBoxLayout(collection_group)

        collection_selection_layout = QHBoxLayout()
        self.collection_combo = QComboBox()
        self.collection_combo.addItem("创建新集合...", None)

        for collection in self.collections:
            self.collection_combo.addItem(collection.name, collection.id)

        self.new_collection_button = QPushButton("新建集合")
        self.new_collection_button.clicked.connect(self.create_new_collection)

        collection_selection_layout.addWidget(self.collection_combo)
        collection_selection_layout.addWidget(self.new_collection_button)

        # New collection fields (initially hidden)
        self.new_collection_widget = QWidget()
        new_collection_layout = QFormLayout(self.new_collection_widget)

        self.collection_name_input = QLineEdit()
        self.collection_name_input.setMinimumHeight(30)
        
        self.collection_description_input = QTextEdit()
        self.collection_description_input.setMinimumHeight(80)
        self.collection_description_input.setMaximumHeight(120)

        new_collection_layout.addRow("集合名称:", self.collection_name_input)
        new_collection_layout.addRow("描述:", self.collection_description_input)

        self.new_collection_widget.hide()

        collection_layout.addLayout(collection_selection_layout)
        collection_layout.addWidget(self.new_collection_widget)

        # Buttons
        button_layout = QHBoxLayout()
        self.upload_button = QPushButton("上传")
        self.cancel_button = QPushButton("取消")

        self.upload_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.upload_button)
        button_layout.addWidget(self.cancel_button)

        # Add all groups to main layout
        layout.addWidget(file_group)
        layout.addWidget(type_group)
        layout.addWidget(collection_group)
        layout.addLayout(button_layout)

        # Connect signals
        self.collection_combo.currentIndexChanged.connect(
            self.on_collection_changed)

    def select_files(self):
        """Open file dialog to select documents."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(
            "Documents (*.pdf *.md *.csv);;PDF Files (*.pdf);;Markdown Files (*.md);;CSV Files (*.csv)")

        if file_dialog.exec():
            self.selected_files = file_dialog.selectedFiles()
            self.update_files_list()

    def update_files_list(self):
        """Update the files list widget."""
        self.files_list.clear()
        for file_path in self.selected_files:
            filename = os.path.basename(file_path)
            self.files_list.addItem(filename)

    def on_collection_changed(self):
        """Handle collection selection change."""
        current_data = self.collection_combo.currentData()
        if current_data is None:  # "Create new collection" selected
            self.new_collection_widget.show()
        else:
            self.new_collection_widget.hide()

    def create_new_collection(self):
        """Show new collection creation fields."""
        self.collection_combo.setCurrentIndex(
            0)  # Select "Create new collection"
        self.new_collection_widget.show()

    def get_upload_data(self):
        """Get the upload configuration."""
        if not self.selected_files:
            return None

        doc_type = self.doc_type_combo.currentData()
        collection_id = self.collection_combo.currentData()

        result = {
            'files': self.selected_files,
            'document_type': doc_type,
            'collection_id': collection_id
        }

        # If creating new collection, add collection info
        if collection_id is None:
            collection_name = self.collection_name_input.text().strip()
            collection_description = self.collection_description_input.toPlainText().strip()

            if not collection_name:
                QMessageBox.warning(self, "错误", "请输入集合名称")
                return None

            result['new_collection'] = {
                'name': collection_name,
                'description': collection_description
            }

        return result


class CreateCollectionDialog(QDialog):
    """Dialog for creating a new collection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新集合")
        self.setMinimumSize(500, 350)
        self.resize(600, 400)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Form
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入集合名称...")

        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(120)
        self.description_input.setMaximumHeight(200)
        self.description_input.setPlaceholderText("输入集合描述（可选）...")

        form_layout.addRow("名称*:", self.name_input)
        form_layout.addRow("描述:", self.description_input)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("创建")
        self.cancel_button = QPushButton("取消")

        self.create_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

    def get_collection_data(self):
        """Get the collection data from the form."""
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "错误", "请输入集合名称")
            return None

        return {
            'name': name,
            'description': description
        }


class CollectionDetailsDialog(QDialog):
    """Dialog for viewing collection details and documents."""

    def __init__(self, collection_id: str, parent=None):
        super().__init__(parent)
        self.collection_id = collection_id
        self.collection = None
        self.documents = []

        self.setWindowTitle("集合详情")
        self.setMinimumSize(700, 500)
        
        # Detect theme
        self.is_dark_mode = self.detect_dark_mode()

        self.setup_ui()
        self.load_collection_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Collection info section
        info_group = QGroupBox("集合信息")
        info_layout = QFormLayout(info_group)

        self.name_label = QLabel()
        self.description_label = QLabel()
        self.created_label = QLabel()
        self.doc_count_label = QLabel()
        self.chunk_count_label = QLabel()

        info_layout.addRow("名称:", self.name_label)
        info_layout.addRow("描述:", self.description_label)
        info_layout.addRow("创建时间:", self.created_label)
        info_layout.addRow("文档数量:", self.doc_count_label)
        info_layout.addRow("知识片段:", self.chunk_count_label)

        # Documents section
        docs_group = QGroupBox("文档列表")
        docs_layout = QVBoxLayout(docs_group)

        # Documents table
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(5)
        self.documents_table.setHorizontalHeaderLabels(
            ["文件名", "类型", "大小", "处理时间", "操作"])

        docs_header = self.documents_table.horizontalHeader()
        docs_header.setSectionResizeMode(0, QHeaderView.Stretch)
        docs_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        docs_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        docs_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        docs_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        docs_layout.addWidget(self.documents_table)

        # Buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.close_button = QPushButton("关闭")

        self.refresh_button.clicked.connect(self.load_collection_data)
        self.close_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.close_button)

        # Add to main layout
        layout.addWidget(info_group)
        layout.addWidget(docs_group)
        layout.addLayout(button_layout)

    def load_collection_data(self):
        """Load collection data and documents."""
        if not KNOWLEDGE_BASE_AVAILABLE:
            return

        try:
            # Get collection info
            collections = ai_services.get_knowledge_base_collections()
            self.collection = None

            for collection in collections:
                if collection.id == self.collection_id:
                    self.collection = collection
                    break

            if not self.collection:
                QMessageBox.warning(self, "错误", "集合不存在")
                self.reject()
                return

            # Update collection info
            self.name_label.setText(self.collection.name)
            self.description_label.setText(
                self.collection.description or "无描述")

            created_time = self.collection.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(
                self.collection.created_at, 'strftime') else str(self.collection.created_at)
            self.created_label.setText(created_time)
            self.doc_count_label.setText(str(self.collection.document_count))
            self.chunk_count_label.setText(str(self.collection.total_chunks))

            # Get collection statistics for more details
            kb_manager = ai_services.get_knowledge_base_manager()
            if kb_manager:
                stats = kb_manager.get_collection_stats(self.collection_id)
                if 'recent_documents' in stats:
                    self.update_documents_table(stats['recent_documents'])

        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载集合数据失败: {e}")
    
    def detect_dark_mode(self):
        """Detect if the system is using dark mode."""
        try:
            import sys
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
            from PySide6.QtWidgets import QApplication
            palette = QApplication.palette()
            window_color = palette.color(palette.Window)
            return window_color.lightness() < 128
        except:
            return False  # Default to light mode if detection fails
    
    def get_button_style(self, button_type="default"):
        """Get button style based on current theme and button type."""
        is_dark = self.is_dark_mode
        
        if button_type == "danger":  # 删除按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #8B0000;
                    color: #FFFFFF;
                    border: 1px solid #A52A2A;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #A52A2A;
                }
                QPushButton:pressed {
                    background-color: #660000;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #ffcccc;
                    color: #8B0000;
                    border: 1px solid #ffaaaa;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffaaaa;
                }
                QPushButton:pressed {
                    background-color: #ff9999;
                }
                """
        elif button_type == "info":  # 预览按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    border: 1px solid #3B82F6;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3B82F6;
                }
                QPushButton:pressed {
                    background-color: #1E40AF;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #cceeff;
                    color: #1E3A8A;
                    border: 1px solid #aaddff;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #aaddff;
                }
                QPushButton:pressed {
                    background-color: #99ccff;
                }
                """
        else:  # 默认按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #404040;
                    color: #FFFFFF;
                    border: 1px solid #606060;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                """

    def update_documents_table(self, documents):
        """Update the documents table."""
        self.documents_table.setRowCount(len(documents))

        for row, doc in enumerate(documents):
            # Filename
            self.documents_table.setItem(
                row, 0, QTableWidgetItem(doc.get('filename', '未知')))

            # Type (would need to be added to document info)
            doc_type = doc.get('document_type', '未知')
            self.documents_table.setItem(row, 1, QTableWidgetItem(doc_type))

            # Size (would need to be added to document info)
            file_size = doc.get('file_size', 0)
            if file_size > 0:
                size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * \
                    1024 else f"{file_size / (1024*1024):.1f} MB"
            else:
                size_str = "未知"
            self.documents_table.setItem(row, 2, QTableWidgetItem(size_str))

            # Processed time
            processed_time = doc.get('processed_at', '未知')
            if processed_time != '未知':
                try:
                    from datetime import datetime
                    if isinstance(processed_time, str):
                        processed_time = datetime.fromisoformat(
                            processed_time.replace('Z', '+00:00'))
                    processed_time = processed_time.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            self.documents_table.setItem(
                row, 3, QTableWidgetItem(str(processed_time)))

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            remove_button = QPushButton("移除")
            remove_button.setMaximumSize(50, 25)
            remove_button.setStyleSheet(self.get_button_style("danger"))
            remove_button.clicked.connect(lambda checked, doc_id=doc.get('id'): self.remove_document(doc_id))

            # Add preview button
            preview_button = QPushButton("预览")
            preview_button.setMaximumSize(50, 25)
            preview_button.setStyleSheet(self.get_button_style("info"))
            preview_button.clicked.connect(lambda checked, doc_id=doc.get('id'): self.preview_document(doc_id))

            actions_layout.addWidget(preview_button)
            actions_layout.addWidget(remove_button)
            actions_layout.addStretch()

            self.documents_table.setCellWidget(row, 4, actions_widget)
    
    def remove_document(self, document_id: str):
        """Remove a document from the collection."""
        if not document_id:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个文档吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                kb_manager = ai_services.get_knowledge_base_manager()
                if kb_manager:
                    success = kb_manager.delete_document(document_id)
                    if success:
                        QMessageBox.information(self, "成功", "文档已删除")
                        self.load_collection_data()  # Refresh the data
                    else:
                        QMessageBox.warning(self, "错误", "删除文档失败")
                else:
                    QMessageBox.warning(self, "错误", "知识库管理器不可用")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除文档时出错: {e}")
    
    def preview_document(self, document_id: str):
        """Preview document chunks."""
        if not document_id:
            return
        
        try:
            kb_manager = ai_services.get_knowledge_base_manager()
            if kb_manager:
                chunks = kb_manager.get_document_chunks(document_id)
                if chunks:
                    dialog = DocumentPreviewDialog(document_id, chunks, self)
                    dialog.exec()
                else:
                    QMessageBox.information(self, "信息", "该文档没有可预览的内容")
            else:
                QMessageBox.warning(self, "错误", "知识库管理器不可用")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"预览文档时出错: {e}")
    
    def detect_dark_mode(self):
        """Detect if the system is using dark mode."""
        try:
            import sys
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
            from PySide6.QtWidgets import QApplication
            palette = QApplication.palette()
            window_color = palette.color(palette.Window)
            return window_color.lightness() < 128
        except:
            return False  # Default to light mode if detection fails
    
    def get_button_style(self, button_type="default"):
        """Get button style based on current theme and button type."""
        is_dark = self.is_dark_mode
        
        if button_type == "danger":  # 删除按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #8B0000;
                    color: #FFFFFF;
                    border: 1px solid #A52A2A;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #A52A2A;
                }
                QPushButton:pressed {
                    background-color: #660000;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #ffcccc;
                    color: #8B0000;
                    border: 1px solid #ffaaaa;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffaaaa;
                }
                QPushButton:pressed {
                    background-color: #ff9999;
                }
                """
        elif button_type == "info":  # 预览按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    border: 1px solid #3B82F6;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3B82F6;
                }
                QPushButton:pressed {
                    background-color: #1E40AF;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #cceeff;
                    color: #1E3A8A;
                    border: 1px solid #aaddff;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #aaddff;
                }
                QPushButton:pressed {
                    background-color: #99ccff;
                }
                """
        else:  # 默认按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #404040;
                    color: #FFFFFF;
                    border: 1px solid #606060;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                """


class DocumentPreviewDialog(QDialog):
    """Dialog for previewing document chunks."""
    
    def __init__(self, document_id: str, chunks: list, parent=None):
        super().__init__(parent)
        self.document_id = document_id
        self.chunks = chunks
        
        self.setWindowTitle("文档预览")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header info
        info_label = QLabel(f"文档ID: {self.document_id} | 共 {len(self.chunks)} 个片段")
        info_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)
        
        # Chunks list
        self.chunks_list = QListWidget()
        
        for i, chunk in enumerate(self.chunks):
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            
            # Chunk header
            header_label = QLabel(f"片段 {i+1}")
            header_label.setStyleSheet("font-weight: bold; color: #0066cc;")
            
            # Chunk content
            content_text = QTextEdit()
            content_text.setPlainText(chunk.get('content', '无内容'))
            content_text.setMaximumHeight(150)
            content_text.setReadOnly(True)
            
            # Metadata
            metadata = chunk.get('metadata', {})
            metadata_text = f"索引: {metadata.get('chunk_index', 'N/A')} | 来源: {metadata.get('source_file', 'N/A')}"
            metadata_label = QLabel(metadata_text)
            metadata_label.setStyleSheet("color: #666666; font-size: 10px;")
            
            item_layout.addWidget(header_label)
            item_layout.addWidget(content_text)
            item_layout.addWidget(metadata_label)
            
            # Add to list
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.chunks_list.addItem(list_item)
            self.chunks_list.setItemWidget(list_item, item_widget)
        
        layout.addWidget(self.chunks_list)
        
        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)


class CollectionManagementDialog(QDialog):
    """Dialog for managing collections."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("集合管理")
        self.setMinimumSize(600, 400)
        self.collections = []
        
        # Detect theme
        self.is_dark_mode = self.detect_dark_mode()

        self.setup_ui()
        self.refresh_collections()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Collections table
        self.collections_table = QTableWidget()
        self.collections_table.setColumnCount(4)
        self.collections_table.setHorizontalHeaderLabels(
            ["名称", "文档数", "创建时间", "操作"])

        header = self.collections_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("创建集合")
        self.import_button = QPushButton("导入集合")
        self.refresh_button = QPushButton("刷新")
        self.close_button = QPushButton("关闭")

        self.create_button.clicked.connect(self.create_collection)
        self.import_button.clicked.connect(self.import_collection)
        self.refresh_button.clicked.connect(self.refresh_collections)
        self.close_button.clicked.connect(self.accept)

        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        layout.addWidget(self.collections_table)
        layout.addLayout(button_layout)

    def refresh_collections(self):
        """Refresh the collections list."""
        if not KNOWLEDGE_BASE_AVAILABLE:
            return

        try:
            self.collections = ai_services.get_knowledge_base_collections()
            self.update_collections_table()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取集合列表失败: {e}")

    def update_collections_table(self):
        """Update the collections table."""
        self.collections_table.setRowCount(len(self.collections))

        for row, collection in enumerate(self.collections):
            # Name
            self.collections_table.setItem(
                row, 0, QTableWidgetItem(collection.name))

            # Document count
            self.collections_table.setItem(
                row, 1, QTableWidgetItem(str(collection.document_count)))

            # Created time
            created_time = collection.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(
                collection.created_at, 'strftime') else str(collection.created_at)
            self.collections_table.setItem(
                row, 2, QTableWidgetItem(created_time))

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)

            # Details button
            details_button = QPushButton("详情")
            details_button.setMaximumSize(40, 25)
            details_button.clicked.connect(
                lambda checked, cid=collection.id: self.view_collection_details(cid))

            # Rename button
            rename_button = QPushButton("重命名")
            rename_button.setMaximumSize(50, 25)
            rename_button.clicked.connect(
                lambda checked, cid=collection.id: self.rename_collection(cid))

            # Export button
            export_button = QPushButton("导出")
            export_button.setMaximumSize(40, 25)
            export_button.clicked.connect(
                lambda checked, cid=collection.id: self.export_collection(cid))

            # Delete button
            delete_button = QPushButton("删除")
            delete_button.setMaximumSize(40, 25)
            delete_button.setStyleSheet(self.get_button_style("danger"))
            delete_button.clicked.connect(
                lambda checked, cid=collection.id: self.delete_collection(cid))

            actions_layout.addWidget(details_button)
            actions_layout.addWidget(rename_button)
            actions_layout.addWidget(export_button)
            actions_layout.addWidget(delete_button)
            actions_layout.addStretch()

            self.collections_table.setCellWidget(row, 3, actions_widget)

    def create_collection(self):
        """Create a new collection."""
        dialog = CreateCollectionDialog(self)

        if dialog.exec():
            collection_data = dialog.get_collection_data()
            if collection_data:
                try:
                    # Create collection using knowledge base manager
                    kb_manager = ai_services.get_knowledge_base_manager()
                    if kb_manager:
                        collection = kb_manager.create_collection(
                            name=collection_data['name'],
                            description=collection_data['description']
                        )
                        QMessageBox.information(
                            self, "成功", f"集合 '{collection.name}' 创建成功")
                        self.refresh_collections()
                    else:
                        QMessageBox.warning(self, "错误", "知识库管理器不可用")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"创建集合失败: {e}")

    def delete_collection(self, collection_id: str):
        """Delete a collection."""
        # Find collection name for confirmation
        collection_name = "未知集合"
        for collection in self.collections:
            if collection.id == collection_id:
                collection_name = collection.name
                break

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除集合 '{collection_name}' 吗？这将删除集合中的所有文档。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                kb_manager = ai_services.get_knowledge_base_manager()
                if kb_manager:
                    success = kb_manager.delete_collection(collection_id)
                    if success:
                        QMessageBox.information(self, "成功", "集合删除成功")
                        self.refresh_collections()
                    else:
                        QMessageBox.warning(self, "错误", "删除集合失败")
                else:
                    QMessageBox.warning(self, "错误", "知识库管理器不可用")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除集合失败: {e}")

    def rename_collection(self, collection_id: str):
        """Rename a collection."""
        # Find current collection
        current_collection = None
        for collection in self.collections:
            if collection.id == collection_id:
                current_collection = collection
                break

        if not current_collection:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("重命名集合")
        dialog.setMinimumSize(300, 100)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setText(current_collection.name)
        name_input.selectAll()

        layout.addRow("新名称:", name_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            new_name = name_input.text().strip()
            if not new_name:
                QMessageBox.warning(self, "错误", "请输入集合名称")
                return

            if new_name == current_collection.name:
                return  # No change

            try:
                # Note: This would require implementing rename functionality in the knowledge base manager
                QMessageBox.information(self, "提示", "重命名功能将在后续版本中实现")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名集合失败: {e}")

    def export_collection(self, collection_id: str):
        """Export a collection."""
        # Find collection name
        collection_name = "未知集合"
        for collection in self.collections:
            if collection.id == collection_id:
                collection_name = collection.name
                break

        # Choose export location
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("JSON Files (*.json)")
        file_dialog.setDefaultSuffix("json")
        file_dialog.selectFile(f"{collection_name}_export.json")

        if file_dialog.exec():
            export_path = file_dialog.selectedFiles()[0]

            try:
                kb_manager = ai_services.get_knowledge_base_manager()
                if kb_manager:
                    exported_file = kb_manager.export_collection(
                        collection_id, "json")

                    # Copy to selected location
                    import shutil
                    shutil.copy2(exported_file, export_path)

                    QMessageBox.information(
                        self, "成功", f"集合已导出到: {export_path}")
                else:
                    QMessageBox.warning(self, "错误", "知识库管理器不可用")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出集合失败: {e}")

    def import_collection(self):
        """Import a collection."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("JSON Files (*.json)")

        if file_dialog.exec():
            import_path = file_dialog.selectedFiles()[0]

            # Ask for merge strategy
            merge_dialog = QMessageBox(self)
            merge_dialog.setWindowTitle("导入策略")
            merge_dialog.setText("如果集合已存在，选择处理方式:")

            skip_button = merge_dialog.addButton("跳过", QMessageBox.ActionRole)
            replace_button = merge_dialog.addButton(
                "替换", QMessageBox.ActionRole)
            merge_button = merge_dialog.addButton("合并", QMessageBox.ActionRole)
            cancel_button = merge_dialog.addButton(
                "取消", QMessageBox.RejectRole)

            merge_dialog.exec()

            clicked_button = merge_dialog.clickedButton()
            if clicked_button == cancel_button:
                return

            if clicked_button == skip_button:
                merge_strategy = "skip"
            elif clicked_button == replace_button:
                merge_strategy = "replace"
            else:
                merge_strategy = "merge"

            try:
                kb_manager = ai_services.get_knowledge_base_manager()
                if kb_manager:
                    collection = kb_manager.import_collection(
                        import_path, merge_strategy)
                    QMessageBox.information(
                        self, "成功", f"集合 '{collection.name}' 导入成功")
                    self.refresh_collections()
                else:
                    QMessageBox.warning(self, "错误", "知识库管理器不可用")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入集合失败: {e}")

    def view_collection_details(self, collection_id: str):
        """View detailed information about a collection."""
        dialog = CollectionDetailsDialog(collection_id, self)
        dialog.exec()
    
    def detect_dark_mode(self):
        """Detect if the system is using dark mode."""
        try:
            import sys
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
            from PySide6.QtWidgets import QApplication
            palette = QApplication.palette()
            window_color = palette.color(palette.Window)
            return window_color.lightness() < 128
        except:
            return False  # Default to light mode if detection fails
    
    def get_button_style(self, button_type="default"):
        """Get button style based on current theme and button type."""
        is_dark = self.is_dark_mode
        
        if button_type == "danger":  # 删除按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #8B0000;
                    color: #FFFFFF;
                    border: 1px solid #A52A2A;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #A52A2A;
                }
                QPushButton:pressed {
                    background-color: #660000;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #ffcccc;
                    color: #8B0000;
                    border: 1px solid #ffaaaa;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffaaaa;
                }
                QPushButton:pressed {
                    background-color: #ff9999;
                }
                """
        elif button_type == "info":  # 预览按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    border: 1px solid #3B82F6;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3B82F6;
                }
                QPushButton:pressed {
                    background-color: #1E40AF;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #cceeff;
                    color: #1E3A8A;
                    border: 1px solid #aaddff;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #aaddff;
                }
                QPushButton:pressed {
                    background-color: #99ccff;
                }
                """
        else:  # 默认按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #404040;
                    color: #FFFFFF;
                    border: 1px solid #606060;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                """


class DocumentProcessingWorker(QThread):
    """Worker thread for document processing with real progress tracking."""

    progress_updated = Signal(int)  # Progress percentage (0-100)
    status_updated = Signal(str)    # Status message
    finished = Signal(bool, str)    # Success, message

    def __init__(self, upload_data):
        super().__init__()
        self.upload_data = upload_data
        self.current_file_index = 0
        self.total_files = 0
        self.file_progress_weights = []  # Weight of each file based on estimated complexity
        self.accumulated_progress = 0.0

    def run(self):
        """Process documents in background with real progress tracking."""
        try:
            if not KNOWLEDGE_BASE_AVAILABLE:
                self.finished.emit(False, "知识库功能不可用")
                return

            files = self.upload_data['files']
            collection_id = self.upload_data['collection_id']
            document_type = self.upload_data['document_type']
            self.total_files = len(files)

            # Calculate progress weights based on file sizes
            self._calculate_file_weights(files)

            # Get document type enum
            if document_type == "knowledge":
                doc_type = DocumentType.KNOWLEDGE_DOCUMENT
            elif document_type == "question_bank":
                doc_type = DocumentType.QUESTION_BANK
            else:
                self.finished.emit(False, f"未知的文档类型: {document_type}")
                return

            kb_manager = ai_services.get_knowledge_base_manager()
            if not kb_manager:
                self.finished.emit(False, "知识库管理器不可用")
                return

            successful_uploads = 0
            failed_uploads = []

            for i, file_path in enumerate(files):
                self.current_file_index = i
                filename = os.path.basename(file_path)
                self.status_updated.emit(f"处理文件 ({i+1}/{self.total_files}): {filename}")

                try:
                    # Submit document for processing
                    task = kb_manager.add_document_async(
                        collection_id=collection_id,
                        file_path=file_path,
                        doc_type=doc_type
                    )

                    # Register progress callback for real-time updates
                    kb_manager.task_manager.register_progress_callback(
                        task.id, 
                        self._on_task_progress
                    )

                    # Wait for processing to complete with real progress tracking
                    import time
                    max_wait_time = 600  # Increase to 10 minutes
                    wait_time = 0
                    last_progress = 0.0
                    stall_count = 0
                    max_stall_count = 30  # 30 seconds without progress = stall

                    while wait_time < max_wait_time:
                        task_status = kb_manager.get_processing_status(task.id)
                        
                        if task_status is None:
                            # Task was cleaned up, likely completed
                            break
                        elif task_status.status.value in ["completed", "failed", "cancelled"]:
                            break
                        
                        # Check for progress stall
                        if task_status.progress == last_progress:
                            stall_count += 1
                        else:
                            stall_count = 0
                            last_progress = task_status.progress
                        
                        # If stalled for too long, but progress is high, assume completion
                        if stall_count >= max_stall_count and task_status.progress >= 0.95:
                            print(f"🔄 [UI] 任务 {task.id[:8]}... 进度停滞但接近完成，假设已完成")
                            break

                        time.sleep(1)
                        wait_time += 1

                    # Check final status
                    final_status = kb_manager.get_processing_status(task.id)
                    
                    if final_status is None:
                        # Task was cleaned up, assume success
                        successful_uploads += 1
                        self._update_file_completed_progress()
                    elif final_status.status.value == "completed":
                        successful_uploads += 1
                        self._update_file_completed_progress()
                    elif final_status.status.value in ["failed", "cancelled"]:
                        error_msg = final_status.error_message or f"任务{final_status.status.value}"
                        failed_uploads.append(f"{filename}: {error_msg}")
                        self._update_file_completed_progress()
                    elif final_status.status.value == "processing":
                        # Still processing after timeout
                        if final_status.progress >= 0.95:
                            # Very high progress, likely completed but status not updated
                            print(f"✅ [UI] 任务 {task.id[:8]}... 进度 {final_status.progress:.1%}，假设完成")
                            successful_uploads += 1
                        else:
                            error_msg = f"处理超时 (进度: {final_status.progress:.1%})"
                            failed_uploads.append(f"{filename}: {error_msg}")
                        self._update_file_completed_progress()
                    else:
                        error_msg = f"未知状态: {final_status.status.value}"
                        failed_uploads.append(f"{filename}: {error_msg}")
                        self._update_file_completed_progress()

                except Exception as e:
                    failed_uploads.append(f"{filename}: {str(e)}")
                    self._update_file_completed_progress()

            # Final progress update
            self.progress_updated.emit(100)

            # Prepare result message
            if successful_uploads == self.total_files:
                message = f"所有 {self.total_files} 个文件处理完成"
                self.finished.emit(True, message)
            elif successful_uploads > 0:
                message = f"{successful_uploads}/{self.total_files} 个文件处理成功"
                if failed_uploads:
                    message += f"\n失败的文件:\n" + "\n".join(failed_uploads[:3])
                    if len(failed_uploads) > 3:
                        message += f"\n... 还有 {len(failed_uploads) - 3} 个失败"
                self.finished.emit(True, message)
            else:
                message = "所有文件处理失败"
                if failed_uploads:
                    message += f"\n错误信息:\n" + "\n".join(failed_uploads[:3])
                self.finished.emit(False, message)

        except Exception as e:
            self.finished.emit(False, f"处理失败: {str(e)}")

    def _calculate_file_weights(self, files):
        """Calculate progress weights for each file based on size."""
        import os
        file_sizes = []
        
        for file_path in files:
            try:
                size = os.path.getsize(file_path)
                file_sizes.append(size)
            except:
                file_sizes.append(1024 * 1024)  # Default 1MB if can't get size
        
        total_size = sum(file_sizes)
        if total_size == 0:
            # Equal weights if no size info
            self.file_progress_weights = [1.0 / len(files)] * len(files)
        else:
            # Weight by file size
            self.file_progress_weights = [size / total_size for size in file_sizes]
        
        print(f"📊 [UI] 文件权重分配: {[f'{w:.2%}' for w in self.file_progress_weights]}")

    def _on_task_progress(self, task_id: str, progress: float, message: str):
        """Handle real-time progress updates from task manager."""
        try:
            # Calculate overall progress
            # Progress for completed files + progress for current file
            completed_files_progress = sum(self.file_progress_weights[:self.current_file_index])
            current_file_progress = self.file_progress_weights[self.current_file_index] * progress
            overall_progress = completed_files_progress + current_file_progress
            
            # Convert to percentage and emit
            progress_percent = int(overall_progress * 100)
            progress_percent = min(progress_percent, 99)  # Cap at 99% until all files done
            
            self.progress_updated.emit(progress_percent)
            
            # Update status with detailed info
            filename = os.path.basename(self.upload_data['files'][self.current_file_index])
            detailed_message = f"处理文件 ({self.current_file_index+1}/{self.total_files}): {filename} - {message}"
            self.status_updated.emit(detailed_message)
            
            print(f"📈 [UI] 任务 {task_id[:8]}... 进度: {progress:.1%} -> 总体: {progress_percent}% ({message})")
            
        except Exception as e:
            print(f"❌ [UI] 进度回调错误: {e}")

    def _update_file_completed_progress(self):
        """Update progress when a file is completed."""
        # Calculate progress for all completed files
        completed_files_progress = sum(self.file_progress_weights[:self.current_file_index + 1])
        progress_percent = int(completed_files_progress * 100)
        progress_percent = min(progress_percent, 99)  # Cap at 99% until all files done
        
        self.progress_updated.emit(progress_percent)
        print(f"✅ [UI] 文件 {self.current_file_index + 1} 完成，总体进度: {progress_percent}%")


class KnowledgeBasePanel(QWidget):
    """Main knowledge base panel widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Detect theme
        self.is_dark_mode = self.detect_dark_mode()
        self.setup_theme_styles()
        self.collections = []
        self.selected_collections = []
        self.processing_worker = None

        self.setup_ui()
        self.refresh_data()
        
        # 在初始化完成后连接复选框信号，避免初始化时触发不必要的事件
        print("🔗 [知识库面板] 连接复选框状态变化信号...")
        self.enable_checkbox.stateChanged.connect(self.safe_toggle_knowledge_base)

        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def detect_dark_mode(self):
        """Detect if the system is using dark mode."""
        try:
            import sys
            if sys.platform == 'win32':
                import winreg
                try:
                    registry = winreg.ConnectRegistry(
                        None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(
                        registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    return value == 0  # 0 means dark mode, 1 means light mode
                except:
                    pass

            # Fallback: check Qt palette
            from PySide6.QtWidgets import QApplication
            palette = QApplication.palette()
            window_color = palette.color(palette.Window)
            return window_color.lightness() < 128
        except:
            return False  # Default to light mode if detection fails

    def get_button_style(self, button_type="default"):
        """Get button style based on current theme and button type."""
        is_dark = self.is_dark_mode
        
        if button_type == "danger":  # 删除按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #8B0000;
                    color: #FFFFFF;
                    border: 1px solid #A52A2A;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #A52A2A;
                }
                QPushButton:pressed {
                    background-color: #660000;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #ffcccc;
                    color: #8B0000;
                    border: 1px solid #ffaaaa;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffaaaa;
                }
                QPushButton:pressed {
                    background-color: #ff9999;
                }
                """
        elif button_type == "info":  # 预览按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    border: 1px solid #3B82F6;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3B82F6;
                }
                QPushButton:pressed {
                    background-color: #1E40AF;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #cceeff;
                    color: #1E3A8A;
                    border: 1px solid #aaddff;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #aaddff;
                }
                QPushButton:pressed {
                    background-color: #99ccff;
                }
                """
        else:  # 默认按钮
            if is_dark:
                return """
                QPushButton {
                    background-color: #404040;
                    color: #FFFFFF;
                    border: 1px solid #606060;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
                """
            else:
                return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                """

    def setup_theme_styles(self):
        """Setup theme-aware styles."""
        if self.is_dark_mode:
            # Dark theme
            self.bg_color = "#2D2D2D"
            self.text_color = "#E0E0E0"
            self.border_color = "#555555"
            self.button_bg = "#404040"
            self.button_hover = "#505050"
            self.input_bg = "#3A3A3A"
            self.group_bg = "#353535"
        else:
            # Light theme
            self.bg_color = "#FFFFFF"
            self.text_color = "#333333"
            self.border_color = "#CCCCCC"
            self.button_bg = "#EAEAEA"
            self.button_hover = "#DCDCDC"
            self.input_bg = "#FFFFFF"
            self.group_bg = "#F5F5F5"

        # Create style strings
        self.widget_style = f"""
            QWidget {{
                background-color: {self.bg_color};
                color: {self.text_color};
            }}
        """

        self.group_style = f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.border_color};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.group_bg};
                color: {self.text_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """

        self.button_style = f"""
            QPushButton {{
                background-color: {self.button_bg};
                border: 1px solid {self.border_color};
                border-radius: 4px;
                padding: 5px 10px;
                color: {self.text_color};
            }}
            QPushButton:hover {{
                background-color: {self.button_hover};
            }}
        """

        self.input_style = f"""
            QLineEdit, QTextEdit, QListWidget {{
                background-color: {self.input_bg};
                border: 1px solid {self.border_color};
                border-radius: 3px;
                padding: 3px;
                color: {self.text_color};
            }}
        """

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Apply theme to main widget
        self.setStyleSheet(self.widget_style)

        # Title
        title_label = QLabel("知识库")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(
            f"color: {self.text_color}; font-weight: bold;")

        # Status section
        status_group = QGroupBox("状态")
        status_group.setStyleSheet(self.group_style)
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("正在加载...")
        self.status_label.setStyleSheet(f"color: {self.text_color};")

        self.enable_checkbox = QCheckBox("启用知识库")
        self.enable_checkbox.setStyleSheet(f"color: {self.text_color};")
        # 先不连接信号，等初始化完成后再连接

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.enable_checkbox)

        # Collections section
        collections_group = QGroupBox("集合管理")
        collections_group.setStyleSheet(self.group_style)
        collections_layout = QVBoxLayout(collections_group)

        # Collection buttons
        collection_buttons_layout = QHBoxLayout()
        self.upload_button = QPushButton("上传文档")
        self.upload_button.setStyleSheet(self.button_style)

        self.manage_collections_button = QPushButton("管理集合")
        self.manage_collections_button.setStyleSheet(self.button_style)

        self.upload_button.clicked.connect(self.upload_documents)
        self.manage_collections_button.clicked.connect(self.manage_collections)

        collection_buttons_layout.addWidget(self.upload_button)
        collection_buttons_layout.addWidget(self.manage_collections_button)
        collection_buttons_layout.addStretch()

        # Collections list
        self.collections_list = QListWidget()
        self.collections_list.setMaximumHeight(150)
        self.collections_list.setStyleSheet(self.input_style)
        self.collections_list.itemChanged.connect(
            self.on_collection_selection_changed)

        collections_label = QLabel("选择用于查询的集合:")
        collections_label.setStyleSheet(f"color: {self.text_color};")

        collections_layout.addLayout(collection_buttons_layout)
        collections_layout.addWidget(collections_label)
        collections_layout.addWidget(self.collections_list)

        # Processing section
        processing_group = QGroupBox("处理状态")
        processing_group.setStyleSheet(self.group_style)
        processing_layout = QVBoxLayout(processing_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.processing_status_label = QLabel("无正在处理的任务")
        self.processing_status_label.setStyleSheet(
            f"color: {self.text_color};")

        processing_layout.addWidget(self.processing_status_label)
        processing_layout.addWidget(self.progress_bar)

        # Search preview section
        search_group = QGroupBox("知识搜索预览")
        search_group.setStyleSheet(self.group_style)
        search_layout = QVBoxLayout(search_group)

        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索查询...")
        self.search_input.setStyleSheet(self.input_style)

        self.search_button = QPushButton("搜索")
        self.search_button.setStyleSheet(self.button_style)
        self.search_button.clicked.connect(self.search_knowledge)

        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_button)

        self.search_results = QTextEdit()
        self.search_results.setMaximumHeight(100)
        self.search_results.setReadOnly(True)
        self.search_results.setStyleSheet(self.input_style)

        search_layout.addLayout(search_input_layout)
        search_layout.addWidget(self.search_results)

        # Add all groups to main layout
        layout.addWidget(title_label)
        layout.addWidget(status_group)
        layout.addWidget(collections_group)
        layout.addWidget(processing_group)
        layout.addWidget(search_group)
        layout.addStretch()

        # Initial state
        self.set_enabled_state(False)

    def refresh_data(self):
        """Refresh knowledge base data."""
        if not KNOWLEDGE_BASE_AVAILABLE:
            self.status_label.setText("知识库功能不可用")
            return

        try:
            # Simple refresh - just update UI to match backend
            self.refresh_ui_state()

            # Sync selected collections from backend before refreshing UI
            self.sync_selected_collections_from_backend()

            # Get collections
            self.collections = ai_services.get_knowledge_base_collections()
            self.update_collections_list()

        except Exception as e:
            self.status_label.setText(f"获取状态失败: {e}")
            self.set_enabled_state(False)

    def update_status_display(self, status: dict):
        """Update the status display."""
        if not status:
            self.status_label.setText("无法获取状态")
            return

        enabled = status.get('enabled', False)
        available = status.get('available', False)
        total_collections = status.get('total_collections', 0)
        total_documents = status.get('total_documents', 0)
        can_process = status.get('can_process_queries', False)

        status_text = f"可用: {'是' if available else '否'} | "
        status_text += f"集合: {total_collections} | "
        status_text += f"文档: {total_documents} | "
        status_text += f"可查询: {'是' if can_process else '否'}"

        self.status_label.setText(status_text)
    


    def update_collections_list(self):
        """Update the collections list widget while preserving selection state."""
        # Save current selection state before clearing
        previously_selected = set(self.selected_collections)
        print(f"🔄 [知识库面板] 刷新集合列表，保持选中状态: {previously_selected}")
        
        self.collections_list.clear()

        for collection in self.collections:
            item = QListWidgetItem(
                f"{collection.name} ({collection.document_count} 文档)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # Restore previous selection state
            if collection.id in previously_selected:
                item.setCheckState(Qt.Checked)
                print(f"   ✅ 恢复选中状态: {collection.name} ({collection.id})")
            else:
                item.setCheckState(Qt.Unchecked)
                
            item.setData(Qt.UserRole, collection.id)
            self.collections_list.addItem(item)

    def sync_selected_collections_from_backend(self):
        """Sync selected collections from backend to UI."""
        try:
            # Get currently selected collections from RAG pipeline
            rag_pipeline = ai_services.get_rag_pipeline()
            if rag_pipeline:
                backend_selected = rag_pipeline.get_selected_collections()
                if backend_selected != self.selected_collections:
                    print(f"🔄 [知识库面板] 同步后端选中集合: {backend_selected}")
                    self.selected_collections = backend_selected.copy()
                else:
                    print(f"✅ [知识库面板] 集合选择状态已同步: {len(self.selected_collections)} 个")
        except Exception as e:
            print(f"❌ [知识库面板] 同步选中集合失败: {e}")

    def set_enabled_state(self, enabled: bool):
        """Set the enabled state of controls."""
        self.upload_button.setEnabled(enabled)
        self.manage_collections_button.setEnabled(enabled)
        self.collections_list.setEnabled(enabled)
        self.search_button.setEnabled(enabled)
        self.search_input.setEnabled(enabled)

    def safe_toggle_knowledge_base(self, state):
        """Safe toggle with recursion protection."""
        # 在PySide6中，stateChanged信号传递的是整数值，需要与枚举的value比较
        is_checked = (state == Qt.CheckState.Checked.value)
        
        print("🔄 [知识库面板] 知识库启用勾选框状态变化")
        print(f"📋 [知识库面板] 新状态: {'选中' if is_checked else '未选中'}")
        
        # Prevent recursion during UI updates
        if hasattr(self, '_updating_checkbox') and self._updating_checkbox:
            print("🔒 [知识库面板] 检测到递归更新，跳过处理")
            return
        
        print("🎯 [知识库面板] 调用 toggle_knowledge_base...")
        self.toggle_knowledge_base(state)
    
    def toggle_knowledge_base(self, state):
        """Toggle knowledge base enabled state."""
        print("🎛️ [知识库面板] 开始切换知识库状态...")
        
        if not KNOWLEDGE_BASE_AVAILABLE:
            print("❌ [知识库面板] 知识库功能不可用，无法切换")
            return

        # Get intended state
        intended_enabled = (state == Qt.CheckState.Checked.value)
        print(f"🎯 [知识库面板] 目标状态: {'启用' if intended_enabled else '禁用'}")
        
        # Perform the operation
        print(f"🎛️ [知识库面板] 执行知识库{'启用' if intended_enabled else '禁用'}操作...")
        try:
            if intended_enabled:
                print("🚀 [知识库面板] 调用 ai_services.enable_knowledge_base()...")
                result = ai_services.enable_knowledge_base()
            else:
                print("🛑 [知识库面板] 调用 ai_services.disable_knowledge_base()...")
                result = ai_services.disable_knowledge_base()
            
            if result:
                print(f"✅ [知识库面板] 知识库{'启用' if intended_enabled else '禁用'}操作成功")
            else:
                print(f"❌ [知识库面板] 知识库{'启用' if intended_enabled else '禁用'}操作失败")
                
        except Exception as e:
            print(f"❌ [知识库面板] 知识库切换时发生错误: {e}")
            import traceback
            print(f"🔍 [知识库面板] 错误详情: {traceback.format_exc()}")
        
        # Always refresh UI to match actual backend state
        # This ensures UI is always consistent regardless of what happened
        self.simple_refresh_ui()
    
    def simple_refresh_ui(self):
        """Simple UI refresh to match backend state."""
        print("🔄 [知识库面板] 开始刷新UI状态...")
        try:
            # Get current backend state
            print("📊 [知识库面板] 获取后端状态...")
            status = ai_services.get_knowledge_base_status()
            enabled = status.get('enabled', False)
            available = status.get('available', False)
            print(f"📋 [知识库面板] 后端状态 - 启用: {enabled}, 可用: {available}")
            
            # Update checkbox - use a flag to prevent recursion
            current_checked = self.enable_checkbox.isChecked()
            print(f"🔘 [知识库面板] 当前复选框状态: {current_checked}, 目标状态: {enabled}")
            
            if not hasattr(self, '_updating_checkbox') or not self._updating_checkbox:
                if current_checked != enabled:
                    print(f"🔄 [知识库面板] 更新复选框状态: {current_checked} -> {enabled}")
                    self._updating_checkbox = True
                    try:
                        # 使用blockSignals来阻止信号发射
                        self.enable_checkbox.blockSignals(True)
                        self.enable_checkbox.setChecked(enabled)
                        self.enable_checkbox.blockSignals(False)
                    finally:
                        self._updating_checkbox = False
                else:
                    print("✅ [知识库面板] 复选框状态已同步，无需更新")
            else:
                print("🔒 [知识库面板] 正在更新中，跳过复选框状态更新")
            
            # Update buttons
            buttons_enabled = enabled and available
            self.upload_button.setEnabled(buttons_enabled)
            self.manage_collections_button.setEnabled(buttons_enabled)
            self.collections_list.setEnabled(buttons_enabled)
            self.search_button.setEnabled(buttons_enabled)
            self.search_input.setEnabled(buttons_enabled)
            
            # Update status text
            total_collections = status.get('total_collections', 0)
            total_documents = status.get('total_documents', 0)
            can_process = status.get('can_process_queries', False)
            
            status_text = f"可用: {'是' if available else '否'} | "
            status_text += f"集合: {total_collections} | "
            status_text += f"文档: {total_documents} | "
            status_text += f"可查询: {'是' if can_process else '否'}"
            
            self.status_label.setText(status_text)
            
        except Exception as e:
            print(f"Failed to refresh UI: {e}")
            # Safe fallback
            self.enable_checkbox.setChecked(False)
            self.upload_button.setEnabled(False)
            self.manage_collections_button.setEnabled(False)
            self.collections_list.setEnabled(False)
            self.search_button.setEnabled(False)
            self.search_input.setEnabled(False)
            self.status_label.setText("状态更新失败")
    
    def refresh_ui_state(self):
        """Refresh UI state to match backend (for compatibility)."""
        self.simple_refresh_ui()

    def on_collection_selection_changed(self, item):
        """Handle collection selection change."""
        print("🔄 [知识库面板] 集合选择状态变化")
        selected_ids = []

        for i in range(self.collections_list.count()):
            item = self.collections_list.item(i)
            # 修复PySide6复选框状态比较问题 - 直接比较枚举对象
            is_checked = (item.checkState() == Qt.CheckState.Checked)
            print(f"📋 [知识库面板] 集合 {i}: checkState={item.checkState()}, 是否选中={is_checked}")
            
            if is_checked:
                collection_id = item.data(Qt.UserRole)
                selected_ids.append(collection_id)
                print(f"   ✅ 选中集合: {collection_id}")

        self.selected_collections = selected_ids
        print(f"📊 [知识库面板] 总共选中 {len(selected_ids)} 个集合")

        # Update AI services with selected collections
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                print(f"🔧 [知识库面板] 更新AI服务的选中集合: {selected_ids}")
                ai_services.set_knowledge_base_collections(selected_ids)
                print("✅ [知识库面板] 集合设置成功")
            except Exception as e:
                print(f"❌ [知识库面板] 设置集合失败: {e}")

    def upload_documents(self):
        """Open document upload dialog."""
        dialog = DocumentUploadDialog(self.collections, self)

        if dialog.exec():
            upload_data = dialog.get_upload_data()
            if upload_data:
                self.start_document_processing(upload_data)

    def start_document_processing(self, upload_data):
        """Start document processing in background."""
        if self.processing_worker and self.processing_worker.isRunning():
            QMessageBox.warning(self, "警告", "已有文档正在处理中")
            return

        try:
            # Create new collection if needed
            collection_id = upload_data['collection_id']

            if collection_id is None and 'new_collection' in upload_data:
                kb_manager = ai_services.get_knowledge_base_manager()
                if kb_manager:
                    new_collection = kb_manager.create_collection(
                        name=upload_data['new_collection']['name'],
                        description=upload_data['new_collection']['description']
                    )
                    collection_id = new_collection.id
                    upload_data['collection_id'] = collection_id

                    # Refresh collections list
                    QTimer.singleShot(500, self.refresh_data)
                else:
                    QMessageBox.warning(self, "错误", "知识库管理器不可用")
                    return

            if not collection_id:
                QMessageBox.warning(self, "错误", "无效的集合ID")
                return

            self.processing_worker = DocumentProcessingWorker(upload_data)
            self.processing_worker.progress_updated.connect(
                self.update_progress)
            self.processing_worker.status_updated.connect(
                self.update_processing_status)
            self.processing_worker.finished.connect(
                self.on_processing_finished)

            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.processing_status_label.setText("开始处理文档...")

            self.processing_worker.start()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动文档处理失败: {e}")

    def update_progress(self, progress):
        """Update processing progress."""
        self.progress_bar.setValue(progress)

    def update_processing_status(self, status):
        """Update processing status message."""
        self.processing_status_label.setText(status)

    def on_processing_finished(self, success, message):
        """Handle processing completion."""
        self.progress_bar.hide()
        self.processing_status_label.setText("无正在处理的任务")

        if success:
            QMessageBox.information(self, "成功", message)
            # Refresh data after successful processing
            QTimer.singleShot(1000, self.refresh_data)
        else:
            QMessageBox.warning(self, "错误", message)

    def manage_collections(self):
        """Open collection management dialog."""
        dialog = CollectionManagementDialog(self)
        dialog.exec()

        # Refresh data after dialog closes
        self.refresh_data()

    def search_knowledge(self):
        """Search knowledge base with current query using RAG."""
        query = self.search_input.text().strip()
        if not query:
            self.search_results.setText("请输入搜索问题")
            return
        
        if not KNOWLEDGE_BASE_AVAILABLE:
            self.search_results.setText("知识库功能不可用")
            return
        
        # 检查是否选中了集合
        if not self.selected_collections:
            self.search_results.setText("请先选择要搜索的集合")
            return
        
        print(f"🔍 [知识库面板] 开始RAG搜索，查询: {query}")
        print(f"📚 [知识库面板] 使用集合: {self.selected_collections}")
        
        # 显示搜索中状态
        self.search_results.setText("🔍 正在搜索中，请稍候...")
        self.search_button.setEnabled(False)
        
        try:
            # 使用完整的RAG功能
            print("🚀 [知识库面板] 调用RAG增强响应")
            response = ai_services.get_answer_from_text(
                question_text=query,
                use_knowledge_base=True
            )
            
            if response:
                print(f"✅ [知识库面板] RAG搜索成功，响应长度: {len(response)} 字符")
                
                # 格式化显示结果
                formatted_result = f"🤖 RAG智能回答\n{'='*50}\n\n"
                formatted_result += f"❓ 问题: {query}\n\n"
                formatted_result += f"💡 回答:\n{response}\n\n"
                formatted_result += f"⏰ 搜索时间: {self.get_current_time()}"
                
                self.search_results.setText(formatted_result)
            else:
                print("❌ [知识库面板] RAG返回空响应")
                self.search_results.setText("未能生成回答，请尝试重新表述问题")
                
        except Exception as e:
            print(f"❌ [知识库面板] RAG搜索失败: {e}")
            import traceback
            print(f"🔍 [知识库面板] 错误详情: {traceback.format_exc()}")
            
            error_msg = f"搜索失败: {str(e)}\n\n"
            error_msg += "请检查:\n"
            error_msg += "• 知识库是否正常启用\n"
            error_msg += "• 是否选择了有效的集合\n"
            error_msg += "• 网络连接是否正常"
            
            self.search_results.setText(error_msg)
        
        finally:
            # 恢复搜索按钮
            self.search_button.setEnabled(True)
    
    def get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def closeEvent(self, event):
        """Handle widget close event."""
        if self.processing_worker and self.processing_worker.isRunning():
            self.processing_worker.terminate()
            self.processing_worker.wait()

        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

        event.accept()
