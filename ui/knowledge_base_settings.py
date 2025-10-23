"""
Knowledge Base Settings Panel - UI for configuring knowledge base settings.
"""

import os
import sys
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QPushButton, QLabel, QCheckBox, QComboBox,
    QSpinBox, QTabWidget, QWidget, QMessageBox, QProgressBar,
    QFrame, QScrollArea, QDialogButtonBox, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap

# Import checkbox utilities for robust state handling
try:
    from utils.checkbox_utils import CheckboxStateHandler, is_checkbox_checked
except ImportError:
    # Fallback if utils not available
    class CheckboxStateHandler:
        @staticmethod
        def is_checked_safe(checkbox):
            try:
                return checkbox.isChecked()
            except:
                return False
    
    def is_checkbox_checked(checkbox):
        return CheckboxStateHandler.is_checked_safe(checkbox)

# Import configuration and AI services
try:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.config_manager import (
        get_knowledge_base_config, get_chromadb_config, 
        get_embedding_api_config, get_reranker_api_config,
        save_knowledge_base_config, save_chromadb_config,
        save_embedding_api_config, save_reranker_api_config
    )
    from core import ai_services
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Configuration not available: {e}")
    CONFIG_AVAILABLE = False


class APIConnectionTester(QThread):
    """Thread for testing API connections."""
    
    test_completed = Signal(str, bool, str)  # api_type, success, message
    
    def __init__(self, api_type: str, config: Dict[str, Any]):
        super().__init__()
        self.api_type = api_type
        self.config = config
    
    def run(self):
        """Test API connection."""
        try:
            if self.api_type == "embedding":
                success, message = self.test_embedding_api()
            elif self.api_type == "reranker":
                success, message = self.test_reranker_api()
            elif self.api_type == "chromadb":
                success, message = self.test_chromadb_connection()
            else:
                success, message = False, f"Unknown API type: {self.api_type}"
            
            self.test_completed.emit(self.api_type, success, message)
            
        except Exception as e:
            self.test_completed.emit(self.api_type, False, f"Test failed: {str(e)}")
    
    def test_embedding_api(self):
        """Test embedding API connection."""
        try:
            import requests
            import json
            
            endpoint = self.config.get('endpoint', '')
            api_key = self.config.get('api_key', '')
            model = self.config.get('model', '')
            
            if not all([endpoint, api_key, model]):
                return False, "Missing required configuration"
            
            # Test with a simple text
            test_data = {
                "model": model,
                "input": "test embedding"
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                endpoint,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Embedding API connection successful"
            else:
                return False, f"API returned status {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def test_reranker_api(self):
        """Test reranker API connection."""
        try:
            import requests
            import json
            
            endpoint = self.config.get('endpoint', '')
            api_key = self.config.get('api_key', '')
            model = self.config.get('model', '')
            
            if not all([endpoint, api_key, model]):
                return False, "Missing required configuration"
            
            # Test with simple rerank data
            test_data = {
                "model": model,
                "query": "test query",
                "documents": ["test document 1", "test document 2"]
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # For reranker, we might need to use a different endpoint
            rerank_endpoint = endpoint.replace('/embeddings', '/rerank') if '/embeddings' in endpoint else endpoint
            
            response = requests.post(
                rerank_endpoint,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Reranker API connection successful"
            else:
                return False, f"API returned status {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def test_chromadb_connection(self):
        """Test ChromaDB connection."""
        try:
            connection_type = self.config.get('connection_type', 'local')
            
            if connection_type == 'local':
                path = self.config.get('path', './data/chromadb')
                
                # Try to create the directory if it doesn't exist
                if not os.path.exists(path):
                    try:
                        os.makedirs(path, exist_ok=True)
                        return True, f"Local ChromaDB path created and accessible: {path}"
                    except Exception as e:
                        return False, f"Cannot create ChromaDB path {path}: {str(e)}"
                else:
                    return True, f"Local ChromaDB path accessible: {path}"
            else:
                # Test remote connection
                host = self.config.get('host', 'localhost')
                port = self.config.get('port', 8000)
                
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return True, f"ChromaDB server accessible at {host}:{port}"
                else:
                    return False, f"Cannot connect to ChromaDB server at {host}:{port}"
                    
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"


class KnowledgeBaseSettingsDialog(QDialog):
    """Main settings dialog for knowledge base configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("知识库设置")
        self.setMinimumSize(600, 500)
        
        # Current configurations
        self.kb_config = {}
        self.chromadb_config = {}
        self.embedding_config = {}
        self.reranker_config = {}
        
        # Connection testers
        self.connection_testers = {}
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # General settings tab
        self.general_tab = self.create_general_tab()
        self.tab_widget.addTab(self.general_tab, "常规设置")
        
        # ChromaDB settings tab
        self.chromadb_tab = self.create_chromadb_tab()
        self.tab_widget.addTab(self.chromadb_tab, "ChromaDB")
        
        # Embedding API tab
        self.embedding_tab = self.create_embedding_tab()
        self.tab_widget.addTab(self.embedding_tab, "Embedding API")
        
        # Reranker API tab
        self.reranker_tab = self.create_reranker_tab()
        self.tab_widget.addTab(self.reranker_tab, "Reranker API")
        
        # Buttons
        button_layout = QHBoxLayout()
        self.test_all_button = QPushButton("测试所有连接")
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        self.reset_button = QPushButton("重置")
        
        self.test_all_button.clicked.connect(self.test_all_connections)
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(self.test_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(self.tab_widget)
        layout.addLayout(button_layout)
    
    def create_general_tab(self):
        """Create general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Knowledge base enable/disable
        enable_group = QGroupBox("知识库功能")
        enable_layout = QVBoxLayout(enable_group)
        
        self.enable_kb_checkbox = QCheckBox("启用知识库功能")
        self.enable_kb_checkbox.stateChanged.connect(self.on_kb_enable_changed)
        
        # Status display
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Box)
        status_layout = QVBoxLayout(self.status_frame)
        
        self.status_label = QLabel("状态: 正在检查...")
        status_layout.addWidget(self.status_label)
        
        enable_layout.addWidget(self.enable_kb_checkbox)
        enable_layout.addWidget(self.status_frame)
        
        # General settings
        settings_group = QGroupBox("基本设置")
        settings_layout = QFormLayout(settings_group)
        
        # Storage path with browse button
        storage_path_layout = QHBoxLayout()
        self.storage_path_input = QLineEdit()
        self.storage_path_input.setPlaceholderText("./data/knowledge_base")
        self.storage_path_browse_button = QPushButton("浏览...")
        self.storage_path_browse_button.clicked.connect(self.browse_storage_path)
        storage_path_layout.addWidget(self.storage_path_input)
        storage_path_layout.addWidget(self.storage_path_browse_button)
        
        self.max_file_size_input = QSpinBox()
        self.max_file_size_input.setRange(1, 1000)
        self.max_file_size_input.setSuffix(" MB")
        self.max_file_size_input.setValue(100)
        
        self.chunk_size_input = QSpinBox()
        self.chunk_size_input.setRange(100, 5000)
        self.chunk_size_input.setValue(1000)
        
        self.chunk_overlap_input = QSpinBox()
        self.chunk_overlap_input.setRange(0, 1000)
        self.chunk_overlap_input.setValue(200)
        
        self.max_collections_input = QSpinBox()
        self.max_collections_input.setRange(1, 200)
        self.max_collections_input.setValue(50)
        
        settings_layout.addRow("存储路径:", storage_path_layout)
        settings_layout.addRow("最大文件大小:", self.max_file_size_input)
        settings_layout.addRow("文档块大小:", self.chunk_size_input)
        settings_layout.addRow("块重叠大小:", self.chunk_overlap_input)
        settings_layout.addRow("最大集合数:", self.max_collections_input)
        
        layout.addWidget(enable_group)
        layout.addWidget(settings_group)
        layout.addStretch()
        
        return tab    

    def create_chromadb_tab(self):
        """Create ChromaDB settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Connection type
        connection_group = QGroupBox("连接类型")
        connection_layout = QVBoxLayout(connection_group)
        
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItem("本地存储", "local")
        self.connection_type_combo.addItem("远程服务器", "remote")
        self.connection_type_combo.currentTextChanged.connect(self.on_connection_type_changed)
        
        connection_layout.addWidget(self.connection_type_combo)
        
        # Local settings
        self.local_settings_group = QGroupBox("本地设置")
        local_layout = QFormLayout(self.local_settings_group)
        
        # ChromaDB path with browse button
        chromadb_path_layout = QHBoxLayout()
        self.chromadb_path_input = QLineEdit()
        self.chromadb_path_input.setPlaceholderText("./data/chromadb")
        self.chromadb_path_browse_button = QPushButton("浏览...")
        self.chromadb_path_browse_button.clicked.connect(self.browse_chromadb_path)
        chromadb_path_layout.addWidget(self.chromadb_path_input)
        chromadb_path_layout.addWidget(self.chromadb_path_browse_button)
        
        local_layout.addRow("存储路径:", chromadb_path_layout)
        
        # Remote settings
        self.remote_settings_group = QGroupBox("远程设置")
        remote_layout = QFormLayout(self.remote_settings_group)
        
        self.chromadb_host_input = QLineEdit()
        self.chromadb_host_input.setPlaceholderText("localhost")
        
        self.chromadb_port_input = QSpinBox()
        self.chromadb_port_input.setRange(1, 65535)
        self.chromadb_port_input.setValue(8000)
        
        self.chromadb_auth_input = QLineEdit()
        self.chromadb_auth_input.setPlaceholderText("认证令牌（可选）")
        self.chromadb_auth_input.setEchoMode(QLineEdit.Password)
        
        self.chromadb_ssl_checkbox = QCheckBox("启用SSL")
        
        remote_layout.addRow("主机:", self.chromadb_host_input)
        remote_layout.addRow("端口:", self.chromadb_port_input)
        remote_layout.addRow("认证令牌:", self.chromadb_auth_input)
        remote_layout.addRow("", self.chromadb_ssl_checkbox)
        
        # Test connection
        test_layout = QHBoxLayout()
        self.test_chromadb_button = QPushButton("测试连接")
        self.chromadb_status_label = QLabel("未测试")
        
        self.test_chromadb_button.clicked.connect(lambda: self.test_connection("chromadb"))
        
        test_layout.addWidget(self.test_chromadb_button)
        test_layout.addWidget(self.chromadb_status_label)
        test_layout.addStretch()
        
        layout.addWidget(connection_group)
        layout.addWidget(self.local_settings_group)
        layout.addWidget(self.remote_settings_group)
        layout.addLayout(test_layout)
        layout.addStretch()
        
        return tab
    
    def create_embedding_tab(self):
        """Create embedding API settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API settings
        api_group = QGroupBox("Embedding API 配置")
        api_layout = QFormLayout(api_group)
        
        self.embedding_endpoint_input = QLineEdit()
        self.embedding_endpoint_input.setPlaceholderText("https://api.example.com/v1/embeddings")
        
        self.embedding_api_key_input = QLineEdit()
        self.embedding_api_key_input.setEchoMode(QLineEdit.Password)
        self.embedding_api_key_input.setPlaceholderText("API密钥")
        
        self.embedding_model_input = QLineEdit()
        self.embedding_model_input.setPlaceholderText("text-embedding-ada-002")
        
        self.embedding_timeout_input = QSpinBox()
        self.embedding_timeout_input.setRange(5, 300)
        self.embedding_timeout_input.setSuffix(" 秒")
        self.embedding_timeout_input.setValue(30)
        
        api_layout.addRow("API端点:", self.embedding_endpoint_input)
        api_layout.addRow("API密钥:", self.embedding_api_key_input)
        api_layout.addRow("模型名称:", self.embedding_model_input)
        api_layout.addRow("超时时间:", self.embedding_timeout_input)
        
        # Test connection
        test_layout = QHBoxLayout()
        self.test_embedding_button = QPushButton("测试连接")
        self.embedding_status_label = QLabel("未测试")
        
        self.test_embedding_button.clicked.connect(lambda: self.test_connection("embedding"))
        
        test_layout.addWidget(self.test_embedding_button)
        test_layout.addWidget(self.embedding_status_label)
        test_layout.addStretch()
        
        # Usage info
        info_group = QGroupBox("使用说明")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
Embedding API用于将文本转换为向量表示，是知识库搜索的核心功能。

支持的API格式:
• OpenAI兼容的embedding接口
• 自定义embedding服务

配置示例:
• 端点: https://api.openai.com/v1/embeddings
• 模型: text-embedding-ada-002
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(api_group)
        layout.addLayout(test_layout)
        layout.addWidget(info_group)
        layout.addStretch()
        
        return tab
    
    def create_reranker_tab(self):
        """Create reranker API settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API settings
        api_group = QGroupBox("Reranker API 配置")
        api_layout = QFormLayout(api_group)
        
        self.reranker_endpoint_input = QLineEdit()
        self.reranker_endpoint_input.setPlaceholderText("https://api.example.com/v1/rerank")
        
        self.reranker_api_key_input = QLineEdit()
        self.reranker_api_key_input.setEchoMode(QLineEdit.Password)
        self.reranker_api_key_input.setPlaceholderText("API密钥")
        
        self.reranker_model_input = QLineEdit()
        self.reranker_model_input.setPlaceholderText("rerank-multilingual-v2.0")
        
        self.reranker_timeout_input = QSpinBox()
        self.reranker_timeout_input.setRange(5, 300)
        self.reranker_timeout_input.setSuffix(" 秒")
        self.reranker_timeout_input.setValue(30)
        
        api_layout.addRow("API端点:", self.reranker_endpoint_input)
        api_layout.addRow("API密钥:", self.reranker_api_key_input)
        api_layout.addRow("模型名称:", self.reranker_model_input)
        api_layout.addRow("超时时间:", self.reranker_timeout_input)
        
        # Test connection
        test_layout = QHBoxLayout()
        self.test_reranker_button = QPushButton("测试连接")
        self.reranker_status_label = QLabel("未测试")
        
        self.test_reranker_button.clicked.connect(lambda: self.test_connection("reranker"))
        
        test_layout.addWidget(self.test_reranker_button)
        test_layout.addWidget(self.reranker_status_label)
        test_layout.addStretch()
        
        # Usage info
        info_group = QGroupBox("使用说明")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
Reranker API用于对搜索结果进行重新排序，提高搜索结果的相关性。

支持的API格式:
• vLLM兼容的rerank接口 (/v1/rerank)
• 自定义reranker服务

配置示例:
• 端点: https://api.example.com/v1/rerank
• 模型: rerank-multilingual-v2.0
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(api_group)
        layout.addLayout(test_layout)
        layout.addWidget(info_group)
        layout.addStretch()
        
        return tab
    
    def load_current_settings(self):
        """Load current settings from configuration."""
        if not CONFIG_AVAILABLE:
            return
        
        try:
            # Load knowledge base config
            self.kb_config = get_knowledge_base_config() or {}
            
            # General settings
            self.enable_kb_checkbox.setChecked(self.kb_config.get('enabled', False))
            self.storage_path_input.setText(self.kb_config.get('storage_path', './data/knowledge_base') or './data/knowledge_base')
            
            # Ensure all SpinBox values are integers, not None
            max_file_size = self.kb_config.get('max_file_size_mb', 100)
            self.max_file_size_input.setValue(max_file_size if max_file_size is not None else 100)
            
            chunk_size = self.kb_config.get('chunk_size', 1000)
            self.chunk_size_input.setValue(chunk_size if chunk_size is not None else 1000)
            
            chunk_overlap = self.kb_config.get('chunk_overlap', 200)
            self.chunk_overlap_input.setValue(chunk_overlap if chunk_overlap is not None else 200)
            
            max_collections = self.kb_config.get('max_collections', 50)
            self.max_collections_input.setValue(max_collections if max_collections is not None else 50)
            
            # ChromaDB config
            self.chromadb_config = get_chromadb_config() or {}
            connection_type = self.chromadb_config.get('connection_type', 'local')
            
            # Set connection type
            index = self.connection_type_combo.findData(connection_type)
            if index >= 0:
                self.connection_type_combo.setCurrentIndex(index)
            
            # Local settings
            self.chromadb_path_input.setText(self.chromadb_config.get('path', './data/chromadb'))
            
            # Remote settings
            self.chromadb_host_input.setText(self.chromadb_config.get('host', 'localhost') or 'localhost')
            port_value = self.chromadb_config.get('port', 8000)
            self.chromadb_port_input.setValue(port_value if port_value is not None else 8000)
            self.chromadb_auth_input.setText(self.chromadb_config.get('auth_token', '') or '')
            self.chromadb_ssl_checkbox.setChecked(self.chromadb_config.get('ssl_enabled', False))
            
            # Embedding config
            self.embedding_config = get_embedding_api_config() or {}
            self.embedding_endpoint_input.setText(self.embedding_config.get('endpoint', '') or '')
            self.embedding_api_key_input.setText(self.embedding_config.get('api_key', '') or '')
            self.embedding_model_input.setText(self.embedding_config.get('model', '') or '')
            
            embedding_timeout = self.embedding_config.get('timeout', 30)
            self.embedding_timeout_input.setValue(embedding_timeout if embedding_timeout is not None else 30)
            
            # Reranker config
            self.reranker_config = get_reranker_api_config() or {}
            self.reranker_endpoint_input.setText(self.reranker_config.get('endpoint', '') or '')
            self.reranker_api_key_input.setText(self.reranker_config.get('api_key', '') or '')
            self.reranker_model_input.setText(self.reranker_config.get('model', '') or '')
            
            reranker_timeout = self.reranker_config.get('timeout', 30)
            self.reranker_timeout_input.setValue(reranker_timeout if reranker_timeout is not None else 30)
            
            # Update UI state
            self.on_connection_type_changed()
            self.update_status()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载设置失败: {e}")
    
    def on_kb_enable_changed(self):
        """
        Handle knowledge base enable/disable change.
        使用健壮的状态检查方式，避免跨平台兼容性问题
        """
        print("🔄 [知识库设置] 启用知识库勾选框状态变化")
        
        # 使用健壮的复选框状态检查工具
        enabled = is_checkbox_checked(self.enable_kb_checkbox)
        print(f"📋 [知识库设置] 新状态: {'启用' if enabled else '禁用'}")
        
        # Enable/disable other tabs
        print("🔧 [知识库设置] 更新其他标签页的启用状态...")
        try:
            for i in range(1, self.tab_widget.count()):
                self.tab_widget.setTabEnabled(i, enabled)
                print(f"   - 标签页 {i}: {'启用' if enabled else '禁用'}")
        except Exception as e:
            print(f"⚠️ [知识库设置] 更新标签页状态失败: {e}")
        
        print("📊 [知识库设置] 更新状态显示...")
        try:
            self.update_status()
        except Exception as e:
            print(f"⚠️ [知识库设置] 更新状态显示失败: {e}")
        
        print("✅ [知识库设置] 勾选框状态变化处理完成")
    
    def on_connection_type_changed(self):
        """Handle connection type change."""
        connection_type = self.connection_type_combo.currentData()
        
        if connection_type == "local":
            self.local_settings_group.show()
            self.remote_settings_group.hide()
        else:
            self.local_settings_group.hide()
            self.remote_settings_group.show()
    
    def update_status(self):
        """Update knowledge base status display."""
        if not CONFIG_AVAILABLE:
            self.status_label.setText("状态: 配置功能不可用")
            return
        
        try:
            if ai_services.is_knowledge_base_available():
                status = ai_services.get_knowledge_base_status()
                if status:
                    enabled = status.get('enabled', False)
                    available = status.get('available', False)
                    collections = status.get('total_collections', 0)
                    documents = status.get('total_documents', 0)
                    
                    status_text = f"状态: {'已启用' if enabled else '已禁用'}"
                    if available:
                        status_text += f" | 集合: {collections} | 文档: {documents}"
                    else:
                        status_text += " | 不可用"
                    
                    self.status_label.setText(status_text)
                else:
                    self.status_label.setText("状态: 无法获取状态")
            else:
                self.status_label.setText("状态: 知识库功能不可用")
                
        except Exception as e:
            self.status_label.setText(f"状态: 错误 - {str(e)}")
    
    def test_connection(self, api_type: str):
        """Test connection for specific API."""
        if api_type in self.connection_testers and self.connection_testers[api_type].isRunning():
            QMessageBox.information(self, "提示", "连接测试正在进行中...")
            return
        
        # Get current configuration
        config = self.get_current_config(api_type)
        if not config:
            return
        
        # Update status
        status_labels = {
            "embedding": self.embedding_status_label,
            "reranker": self.reranker_status_label,
            "chromadb": self.chromadb_status_label
        }
        
        status_label = status_labels.get(api_type)
        if status_label:
            status_label.setText("测试中...")
        
        # Start test
        tester = APIConnectionTester(api_type, config)
        tester.test_completed.connect(self.on_test_completed)
        self.connection_testers[api_type] = tester
        tester.start()
    
    def test_all_connections(self):
        """Test all API connections."""
        # Show warning about API costs
        reply = QMessageBox.question(
            self, "确认测试", 
            "测试所有连接将调用Embedding和Rerank API，可能产生费用。\n\n确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        apis = ["chromadb", "embedding", "reranker"]
        
        for api_type in apis:
            if self.enable_kb_checkbox.isChecked():
                QTimer.singleShot(100 * apis.index(api_type), lambda at=api_type: self.test_connection(at))
    
    def on_test_completed(self, api_type: str, success: bool, message: str):
        """Handle test completion."""
        status_labels = {
            "embedding": self.embedding_status_label,
            "reranker": self.reranker_status_label,
            "chromadb": self.chromadb_status_label
        }
        
        status_label = status_labels.get(api_type)
        if status_label:
            if success:
                status_label.setText(f"✓ {message}")
                status_label.setStyleSheet("color: green;")
            else:
                status_label.setText(f"✗ {message}")
                status_label.setStyleSheet("color: red;")
    
    def get_current_config(self, api_type: str) -> Optional[Dict[str, Any]]:
        """Get current configuration for API type."""
        try:
            if api_type == "embedding":
                return {
                    'endpoint': self.embedding_endpoint_input.text().strip(),
                    'api_key': self.embedding_api_key_input.text().strip(),
                    'model': self.embedding_model_input.text().strip(),
                    'timeout': self.embedding_timeout_input.value()
                }
            elif api_type == "reranker":
                return {
                    'endpoint': self.reranker_endpoint_input.text().strip(),
                    'api_key': self.reranker_api_key_input.text().strip(),
                    'model': self.reranker_model_input.text().strip(),
                    'timeout': self.reranker_timeout_input.value()
                }
            elif api_type == "chromadb":
                connection_type = self.connection_type_combo.currentData()
                config = {'connection_type': connection_type}
                
                if connection_type == "local":
                    config['path'] = self.chromadb_path_input.text().strip()
                else:
                    config.update({
                        'host': self.chromadb_host_input.text().strip(),
                        'port': self.chromadb_port_input.value(),
                        'auth_token': self.chromadb_auth_input.text().strip(),
                        'ssl_enabled': self.chromadb_ssl_checkbox.isChecked()
                    })
                
                return config
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取{api_type}配置失败: {e}")
            return None
    
    def save_settings(self):
        """Save all settings."""
        print("💾 [知识库设置] 开始保存设置...")
        
        if not CONFIG_AVAILABLE:
            print("❌ [知识库设置] 配置功能不可用")
            QMessageBox.warning(self, "错误", "配置功能不可用")
            return
        
        try:
            print("📁 [知识库设置] 创建必要的目录...")
            # Create necessary directories before saving
            if not self.create_required_directories():
                print("❌ [知识库设置] 目录创建失败，保存中止")
                return
            
            # Save knowledge base config
            enabled_status = self.enable_kb_checkbox.isChecked()
            print(f"⚙️ [知识库设置] 准备保存知识库配置，启用状态: {enabled_status}")
            
            kb_config = {
                'enabled': enabled_status,
                'storage_path': self.storage_path_input.text().strip(),
                'max_file_size_mb': self.max_file_size_input.value(),
                'chunk_size': self.chunk_size_input.value(),
                'chunk_overlap': self.chunk_overlap_input.value(),
                'max_collections': self.max_collections_input.value(),
                'background_processing': True,
                'max_concurrent_tasks': 3
            }
            print(f"📝 [知识库设置] 知识库配置内容: {kb_config}")
            
            print("💾 [知识库设置] 调用 save_knowledge_base_config...")
            save_knowledge_base_config(kb_config)
            print("✅ [知识库设置] 知识库配置保存完成")
            
            # Save ChromaDB config
            print("🗄️ [知识库设置] 保存 ChromaDB 配置...")
            chromadb_config = self.get_current_config("chromadb")
            if chromadb_config:
                print(f"📝 [知识库设置] ChromaDB 配置内容: {chromadb_config}")
                save_chromadb_config(chromadb_config)
                print("✅ [知识库设置] ChromaDB 配置保存完成")
            
            # Save embedding config
            print("🔤 [知识库设置] 保存 Embedding API 配置...")
            embedding_config = self.get_current_config("embedding")
            if embedding_config:
                # 隐藏API密钥用于日志
                safe_config = embedding_config.copy()
                if 'api_key' in safe_config:
                    safe_config['api_key'] = '***隐藏***'
                print(f"📝 [知识库设置] Embedding 配置内容: {safe_config}")
                save_embedding_api_config(embedding_config)
                print("✅ [知识库设置] Embedding API 配置保存完成")
            
            # Save reranker config
            print("🔄 [知识库设置] 保存 Reranker API 配置...")
            reranker_config = self.get_current_config("reranker")
            if reranker_config:
                # 隐藏API密钥用于日志
                safe_config = reranker_config.copy()
                if 'api_key' in safe_config:
                    safe_config['api_key'] = '***隐藏***'
                print(f"📝 [知识库设置] Reranker 配置内容: {safe_config}")
                save_reranker_api_config(reranker_config)
                print("✅ [知识库设置] Reranker API 配置保存完成")
            
            print("🎉 [知识库设置] 所有设置保存成功！")
            
            # 重新加载配置使其立即生效
            print("🔄 [知识库设置] 重新加载配置...")
            try:
                if ai_services.reload_knowledge_base_config():
                    print("✅ [知识库设置] 配置已重新加载，立即生效")
                    QMessageBox.information(self, "成功", 
                        "设置已保存并立即生效。\n\n"
                        f"新的分块参数:\n"
                        f"• chunk_size: {kb_config['chunk_size']}\n"
                        f"• chunk_overlap: {kb_config['chunk_overlap']}")
                else:
                    print("⚠️ [知识库设置] 配置重载失败，需要重启程序")
                    QMessageBox.information(self, "成功", 
                        "设置已保存。\n\n"
                        "注意：部分配置需要重启程序才能生效。")
            except Exception as reload_error:
                print(f"⚠️ [知识库设置] 配置重载异常: {reload_error}")
                QMessageBox.information(self, "成功", 
                    "设置已保存。\n\n"
                    "注意：部分配置需要重启程序才能生效。")
            
            self.accept()
            
        except Exception as e:
            print(f"❌ [知识库设置] 保存设置时发生错误: {e}")
            import traceback
            print(f"🔍 [知识库设置] 错误详情: {traceback.format_exc()}")
            QMessageBox.warning(self, "错误", f"保存设置失败: {e}")
    
    def create_required_directories(self):
        """Create required directories for local storage."""
        try:
            directories_to_create = []
            
            # Knowledge base storage path
            if self.enable_kb_checkbox.isChecked():
                storage_path = self.storage_path_input.text().strip()
                if storage_path:
                    directories_to_create.append(("知识库存储", storage_path))
            
            # ChromaDB local path (if using local connection)
            connection_type = self.connection_type_combo.currentData()
            if connection_type == "local":
                chromadb_path = self.chromadb_path_input.text().strip()
                if chromadb_path:
                    directories_to_create.append(("ChromaDB存储", chromadb_path))
            
            # Create directories
            created_dirs = []
            for dir_name, dir_path in directories_to_create:
                if not os.path.exists(dir_path):
                    try:
                        os.makedirs(dir_path, exist_ok=True)
                        created_dirs.append(f"• {dir_name}: {dir_path}")
                        print(f"Created directory: {dir_path}")
                    except Exception as e:
                        QMessageBox.warning(
                            self, "目录创建失败", 
                            f"无法创建{dir_name}目录: {dir_path}\n错误: {e}"
                        )
                        return False
            
            # Show created directories info
            if created_dirs:
                QMessageBox.information(
                    self, "目录已创建", 
                    f"已自动创建以下目录:\n\n" + "\n".join(created_dirs)
                )
            
            return True
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建目录时发生错误: {e}")
            return False
    
    def browse_storage_path(self):
        """Browse for knowledge base storage path."""
        current_path = self.storage_path_input.text().strip()
        if not current_path:
            current_path = "./data/knowledge_base"
        
        # Use the parent directory if the current path doesn't exist
        if not os.path.exists(current_path):
            current_path = os.path.dirname(current_path) if os.path.dirname(current_path) else "."
        
        selected_path = QFileDialog.getExistingDirectory(
            self, 
            "选择知识库存储路径", 
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if selected_path:
            self.storage_path_input.setText(selected_path)
    
    def browse_chromadb_path(self):
        """Browse for ChromaDB storage path."""
        current_path = self.chromadb_path_input.text().strip()
        if not current_path:
            current_path = "./data/chromadb"
        
        # Use the parent directory if the current path doesn't exist
        if not os.path.exists(current_path):
            current_path = os.path.dirname(current_path) if os.path.dirname(current_path) else "."
        
        selected_path = QFileDialog.getExistingDirectory(
            self, 
            "选择ChromaDB存储路径", 
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if selected_path:
            self.chromadb_path_input.setText(selected_path)
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to defaults
            self.enable_kb_checkbox.setChecked(False)
            self.storage_path_input.setText("./data/knowledge_base")
            self.max_file_size_input.setValue(100)
            self.chunk_size_input.setValue(1000)
            self.chunk_overlap_input.setValue(200)
            self.max_collections_input.setValue(50)
            
            self.connection_type_combo.setCurrentIndex(0)
            self.chromadb_path_input.setText("./data/chromadb")
            self.chromadb_host_input.setText("localhost")
            self.chromadb_port_input.setValue(8000)
            self.chromadb_auth_input.setText("")
            self.chromadb_ssl_checkbox.setChecked(False)
            
            self.embedding_endpoint_input.setText("")
            self.embedding_api_key_input.setText("")
            self.embedding_model_input.setText("")
            self.embedding_timeout_input.setValue(30)
            
            self.reranker_endpoint_input.setText("")
            self.reranker_api_key_input.setText("")
            self.reranker_model_input.setText("")
            self.reranker_timeout_input.setValue(30)
            
            # Reset status labels
            self.embedding_status_label.setText("未测试")
            self.embedding_status_label.setStyleSheet("")
            self.reranker_status_label.setText("未测试")
            self.reranker_status_label.setStyleSheet("")
            self.chromadb_status_label.setText("未测试")
            self.chromadb_status_label.setStyleSheet("")
            
            self.on_connection_type_changed()
            self.update_status()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop any running connection tests
        for tester in self.connection_testers.values():
            if tester.isRunning():
                tester.terminate()
                tester.wait()
        
        event.accept()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = KnowledgeBaseSettingsDialog()
    dialog.show()
    sys.exit(app.exec())