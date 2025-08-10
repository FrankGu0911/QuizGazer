"""
Test script for Knowledge Base UI components.
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ui.knowledge_base_panel import KnowledgeBasePanel, CollectionManagementDialog, DocumentUploadDialog


class TestMainWindow(QMainWindow):
    """Test window for knowledge base UI components."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Knowledge Base UI Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add knowledge base panel
        self.kb_panel = KnowledgeBasePanel()
        layout.addWidget(self.kb_panel)


def test_knowledge_base_panel():
    """Test the knowledge base panel."""
    app = QApplication(sys.argv)
    
    window = TestMainWindow()
    window.show()
    
    sys.exit(app.exec())


def test_collection_management_dialog():
    """Test the collection management dialog."""
    app = QApplication(sys.argv)
    
    dialog = CollectionManagementDialog()
    dialog.show()
    
    sys.exit(app.exec())


def test_document_upload_dialog():
    """Test the document upload dialog."""
    app = QApplication(sys.argv)
    
    # Create some mock collections for testing
    from unittest.mock import Mock
    
    mock_collections = [
        Mock(id="coll_1", name="Test Collection 1"),
        Mock(id="coll_2", name="Test Collection 2")
    ]
    
    dialog = DocumentUploadDialog(mock_collections)
    dialog.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Knowledge Base UI components")
    parser.add_argument("--component", choices=["panel", "management", "upload"], 
                       default="panel", help="Component to test")
    
    args = parser.parse_args()
    
    if args.component == "panel":
        test_knowledge_base_panel()
    elif args.component == "management":
        test_collection_management_dialog()
    elif args.component == "upload":
        test_document_upload_dialog()
    else:
        print("Unknown component")
        sys.exit(1)