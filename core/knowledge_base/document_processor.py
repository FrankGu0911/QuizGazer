"""
Document Processor - Handles document parsing, text extraction, and chunking strategies.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import csv
import json
import io

try:
    import PyPDF2
    import pdfplumber
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import pandas as pd
    from pdf2image import convert_from_path, convert_from_bytes
    from PIL import Image
except ImportError as e:
    PyPDF2 = None
    pdfplumber = None
    RecursiveCharacterTextSplitter = None
    pd = None
    convert_from_path = None
    convert_from_bytes = None
    Image = None
    print(f"Warning: Some dependencies not installed: {e}")

try:
    from .models import DocumentChunk, DocumentType
except ImportError:
    from models import DocumentChunk, DocumentType

# Import VLM service for OCR
try:
    import sys
    import os
    # Add the parent directory to the path to import ai_services
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))))
    from core.ai_services import get_question_from_image
except ImportError:
    get_question_from_image = None
    print("Warning: VLM service not available for OCR")


class DocumentProcessor:
    """Handles document parsing, text extraction, and chunking strategies."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the Document Processor.

        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger(__name__)

        # Initialize text splitter for knowledge documents
        if RecursiveCharacterTextSplitter:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
        else:
            self.text_splitter = None
            self.logger.warning("RecursiveCharacterTextSplitter not available")

    def process_document(self, file_path: str, doc_type: DocumentType, document_id: str = None) -> List[DocumentChunk]:
        """
        Process a document and return chunks.

        Args:
            file_path: Path to the document file
            doc_type: Type of document (knowledge or question_bank)
            document_id: Unique identifier for the document

        Returns:
            List of DocumentChunk objects
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        if not document_id:
            document_id = str(uuid.uuid4())

        try:
            if doc_type == DocumentType.KNOWLEDGE_DOCUMENT:
                return self.process_knowledge_document(file_path, document_id)
            elif doc_type == DocumentType.QUESTION_BANK:
                return self.process_question_bank(file_path, document_id)
            else:
                raise ValueError(f"Unsupported document type: {doc_type}")

        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            raise

    def process_knowledge_document(self, file_path: str, document_id: str) -> List[DocumentChunk]:
        """
        Process knowledge documents (PDF/Markdown) with recursive character splitting.

        Args:
            file_path: Path to the knowledge document
            document_id: Unique identifier for the document

        Returns:
            List of DocumentChunk objects
        """
        file_extension = Path(file_path).suffix.lower()

        # Extract text based on file type
        if file_extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_extension in ['.md', '.markdown']:
            text = self._extract_text_from_markdown(file_path)
        elif file_extension == '.txt':
            text = self._extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

        if not text.strip():
            raise ValueError(f"No text content found in {file_path}")

        # Split text into chunks
        if self.text_splitter:
            text_chunks = self.text_splitter.split_text(text)
        else:
            # Fallback simple splitting if langchain not available
            text_chunks = self._simple_text_split(text)

        # Create DocumentChunk objects
        chunks = []
        filename = os.path.basename(file_path)

        for i, chunk_text in enumerate(text_chunks):
            if chunk_text.strip():  # Skip empty chunks
                chunk = DocumentChunk(
                    id=f"{document_id}_chunk_{i}",
                    document_id=document_id,
                    content=chunk_text.strip(),
                    metadata={
                        "source_file": filename,
                        "document_type": "knowledge",
                        "chunk_index": i,
                        "file_extension": file_extension,
                        "total_chunks": len(text_chunks)
                    },
                    chunk_index=i
                )
                chunks.append(chunk)

        self.logger.info(
            f"Processed knowledge document {filename}: {len(chunks)} chunks")
        return chunks

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF files with OCR support for image-based PDFs.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        text = ""

        try:
            # First, try standard text extraction
            if pdfplumber:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

            # Fallback to PyPDF2 if pdfplumber fails or is not available
            elif PyPDF2:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

            else:
                raise ImportError(
                    "Neither pdfplumber nor PyPDF2 is available for PDF processing")

            # Check if we got sufficient text or if OCR is needed
            if self._is_image_heavy_pdf(text, file_path):
                self.logger.info(
                    f"PDF appears to be image-heavy, attempting OCR extraction: {file_path}")
                ocr_text = self.perform_ocr_extraction(file_path)
                if ocr_text.strip():
                    # Combine extracted text with OCR text
                    text = (text + "\n" + ocr_text).strip()
                    self.logger.info(
                        f"OCR extraction successful, combined text length: {len(text)}")
                else:
                    self.logger.warning(
                        f"OCR extraction failed or returned empty text for {file_path}")

        except Exception as e:
            self.logger.error(
                f"Failed to extract text from PDF {file_path}: {e}")
            raise

        return text.strip()

    def _is_image_heavy_pdf(self, extracted_text: str, file_path: str) -> bool:
        """
        Determine if a PDF is image-heavy and needs OCR processing.

        Args:
            extracted_text: Text extracted using standard methods
            file_path: Path to the PDF file

        Returns:
            True if OCR processing is recommended
        """
        # If we got very little text, it's likely image-heavy
        if len(extracted_text.strip()) < 100:
            return True

        # Check text density - if text is very sparse, might be image-heavy
        try:
            if pdfplumber:
                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    if total_pages > 0:
                        avg_text_per_page = len(extracted_text) / total_pages
                        # If average text per page is very low, likely image-heavy
                        if avg_text_per_page < 50:
                            return True
        except Exception as e:
            self.logger.warning(f"Failed to analyze PDF structure: {e}")

        # Check for common OCR indicators in text
        lines = extracted_text.split('\n')
        short_lines = sum(1 for line in lines if len(
            line.strip()) < 10 and len(line.strip()) > 0)
        if len(lines) > 0 and short_lines / len(lines) > 0.5:
            return True

        return False

    def perform_ocr_extraction(self, file_path: str) -> str:
        """
        Perform OCR extraction using VLM service.

        Args:
            file_path: Path to the PDF file to process

        Returns:
            Extracted text from OCR
        """
        if not get_question_from_image:
            self.logger.warning(
                "VLM service not available, skipping OCR extraction")
            return ""

        if not convert_from_path:
            self.logger.warning(
                "pdf2image not available, skipping OCR extraction")
            return ""

        extracted_texts = []

        try:
            # Convert PDF pages to images
            self.logger.info(f"Converting PDF to images for OCR: {file_path}")
            images = convert_from_path(file_path, dpi=200, fmt='PNG')

            self.logger.info(f"Processing {len(images)} pages with OCR")

            for page_num, image in enumerate(images, 1):
                try:
                    # Convert PIL Image to bytes
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()

                    # Use VLM service to extract text from image
                    self.logger.debug(
                        f"Processing page {page_num} with VLM service")
                    ocr_result = get_question_from_image(img_bytes)

                    if ocr_result and not ocr_result.startswith("Error:"):
                        # The VLM service returns JSON, we need to extract text content
                        page_text = self._extract_text_from_vlm_response(
                            ocr_result)
                        if page_text.strip():
                            extracted_texts.append(
                                f"[Page {page_num}]\n{page_text}")
                            self.logger.debug(
                                f"Successfully extracted text from page {page_num}")
                        else:
                            self.logger.warning(
                                f"No text extracted from page {page_num}")
                    else:
                        self.logger.warning(
                            f"OCR failed for page {page_num}: {ocr_result}")

                except Exception as e:
                    self.logger.error(
                        f"Failed to process page {page_num} with OCR: {e}")
                    continue

            # Combine all extracted texts
            combined_text = "\n\n".join(extracted_texts)
            self.logger.info(
                f"OCR extraction completed: {len(extracted_texts)} pages processed, {len(combined_text)} characters extracted")

            return combined_text

        except Exception as e:
            self.logger.error(f"OCR extraction failed for {file_path}: {e}")
            return ""

    def _extract_text_from_vlm_response(self, vlm_response: str) -> str:
        """
        Extract text content from VLM service response.

        Args:
            vlm_response: JSON response from VLM service

        Returns:
            Extracted text content
        """
        try:
            # The VLM service returns JSON with question data
            data = json.loads(vlm_response)

            if isinstance(data, list):
                texts = []
                for item in data:
                    if isinstance(item, dict):
                        # Extract question text
                        question_text = item.get('question_text', '')
                        if question_text:
                            texts.append(question_text)

                        # Extract code block if present
                        code_block = item.get('code_block')
                        if code_block and code_block != 'null':
                            texts.append(f"Code:\n{code_block}")

                        # Extract options if present
                        options = item.get('options', [])
                        if options:
                            texts.append("Options:\n" + "\n".join(options))

                return "\n\n".join(texts)

            else:
                # If it's not a list, try to extract any text content
                return str(data)

        except json.JSONDecodeError:
            # If it's not JSON, treat as plain text
            return vlm_response
        except Exception as e:
            self.logger.warning(f"Failed to parse VLM response: {e}")
            return vlm_response

    def _extract_text_from_markdown(self, file_path: str) -> str:
        """Extract text from Markdown files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Failed to read Markdown file {file_path}: {e}")
            raise

    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Failed to read text file {file_path}: {e}")
            raise

    def _simple_text_split(self, text: str) -> List[str]:
        """
        Simple text splitting fallback when langchain is not available.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at a sentence or paragraph boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + self.chunk_size - self.chunk_overlap, end)

        return chunks

    def process_question_bank(self, file_path: str, document_id: str) -> List[DocumentChunk]:
        """
        Process question bank CSV files with row-based processing.

        Args:
            file_path: Path to the CSV file
            document_id: Unique identifier for the document

        Returns:
            List of DocumentChunk objects
        """
        # Validate CSV format first
        validation_result = self.validate_csv_format(file_path)
        if not validation_result["is_valid"]:
            raise ValueError(
                f"Invalid CSV format: {validation_result['errors']}")

        chunks = []
        filename = os.path.basename(file_path)

        try:
            if pd is not None:
                # Use pandas for better CSV handling
                df = pd.read_csv(file_path)

                for index, row in df.iterrows():
                    # Create content combining question, options, and answer
                    content_parts = [f"Question: {row['question']}"]

                    if 'options' in df.columns and pd.notna(row['options']) and row['options'].strip():
                        content_parts.append(f"Options: {row['options']}")

                    # Use 'answer' column if available, otherwise 'correct_answer'
                    answer_col = 'answer' if 'answer' in df.columns else 'correct_answer'
                    content_parts.append(
                        f"Correct Answer: {row[answer_col]}")

                    content = "\n".join(content_parts)

                    # Create metadata
                    metadata = {
                        "source_file": filename,
                        "document_type": "question_bank",
                        "question_id": f"q_{index + 1}",
                        "chunk_index": index,
                        "row_number": index + 1
                    }

                    # Add optional metadata if available
                    for col in ['difficulty', 'topic', 'category']:
                        if col in df.columns and pd.notna(row[col]):
                            metadata[col] = row[col]

                    chunk = DocumentChunk(
                        id=f"{document_id}_q_{index}",
                        document_id=document_id,
                        content=content,
                        metadata=metadata,
                        chunk_index=index
                    )
                    chunks.append(chunk)

            else:
                # Fallback to standard csv module
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)

                    for index, row in enumerate(reader):
                        content_parts = [f"Question: {row['question']}"]

                        if row.get('options', '').strip():
                            content_parts.append(f"Options: {row['options']}")

                        # Use 'answer' column if available, otherwise 'correct_answer'
                        answer_value = row.get('answer', row.get('correct_answer', ''))
                        content_parts.append(
                            f"Correct Answer: {answer_value}")

                        content = "\n".join(content_parts)

                        metadata = {
                            "source_file": filename,
                            "document_type": "question_bank",
                            "question_id": f"q_{index + 1}",
                            "chunk_index": index,
                            "row_number": index + 1
                        }

                        # Add optional metadata
                        for col in ['difficulty', 'topic', 'category']:
                            if col in row and row[col].strip():
                                metadata[col] = row[col]

                        chunk = DocumentChunk(
                            id=f"{document_id}_q_{index}",
                            document_id=document_id,
                            content=content,
                            metadata=metadata,
                            chunk_index=index
                        )
                        chunks.append(chunk)

        except Exception as e:
            self.logger.error(
                f"Failed to process question bank {file_path}: {e}")
            raise

        self.logger.info(
            f"Processed question bank {filename}: {len(chunks)} questions")
        return chunks

    def validate_csv_format(self, file_path: str) -> Dict[str, Any]:
        """
        Validate CSV format for question banks.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "row_count": 0,
            "columns": []
        }

        try:
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                result["errors"].append("File does not exist")
                return result

            # Try to read the CSV file
            if pd is not None:
                try:
                    df = pd.read_csv(file_path)
                    result["row_count"] = len(df)
                    result["columns"] = list(df.columns)

                    # Check required columns (support both 'answer' and 'correct_answer')
                    required_question = 'question' in df.columns
                    has_answer = 'answer' in df.columns or 'correct_answer' in df.columns
                    
                    missing_columns = []
                    if not required_question:
                        missing_columns.append('question')
                    if not has_answer:
                        missing_columns.append('answer (or correct_answer)')

                    if missing_columns:
                        result["errors"].append(
                            f"Missing required columns: {missing_columns}")
                        return result

                    # Check for empty required fields
                    if 'question' in df.columns:
                        empty_count = df['question'].isna().sum() + (df['question'] == '').sum()
                        if empty_count > 0:
                            result["errors"].append(f"Column 'question' has {empty_count} empty values")
                    
                    # Check answer column (either 'answer' or 'correct_answer')
                    answer_col = 'answer' if 'answer' in df.columns else 'correct_answer'
                    if answer_col in df.columns:
                        empty_count = df[answer_col].isna().sum() + (df[answer_col] == '').sum()
                        if empty_count > 0:
                            result["errors"].append(f"Column '{answer_col}' has {empty_count} empty values")

                    # Check optional columns
                    optional_columns = ['options',
                                        'difficulty', 'topic', 'category']
                    for col in optional_columns:
                        if col not in df.columns:
                            result["warnings"].append(
                                f"Optional column '{col}' not found")

                    # If no errors, mark as valid
                    if not result["errors"]:
                        result["is_valid"] = True

                except Exception as e:
                    result["errors"].append(
                        f"Failed to read CSV with pandas: {e}")

            else:
                # Fallback to standard csv module
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        result["columns"] = reader.fieldnames or []

                        # Check required columns (support both 'answer' and 'correct_answer')
                        columns = result["columns"]
                        required_question = 'question' in columns
                        has_answer = 'answer' in columns or 'correct_answer' in columns
                        
                        missing_columns = []
                        if not required_question:
                            missing_columns.append('question')
                        if not has_answer:
                            missing_columns.append('answer (or correct_answer)')

                        if missing_columns:
                            result["errors"].append(
                                f"Missing required columns: {missing_columns}")
                            return result

                        # Count rows and check for empty values
                        row_count = 0
                        empty_questions = 0
                        empty_answers = 0

                        for row in reader:
                            row_count += 1
                            if not row.get('question', '').strip():
                                empty_questions += 1
                            # Check answer column (either 'answer' or 'correct_answer')
                            answer_value = row.get('answer', row.get('correct_answer', ''))
                            if not answer_value.strip():
                                empty_answers += 1

                        result["row_count"] = row_count

                        if empty_questions > 0:
                            result["errors"].append(
                                f"Found {empty_questions} empty questions")
                        if empty_answers > 0:
                            result["errors"].append(
                                f"Found {empty_answers} empty answers")

                        # If no errors, mark as valid
                        if not result["errors"]:
                            result["is_valid"] = True

                except Exception as e:
                    result["errors"].append(f"Failed to read CSV: {e}")

        except Exception as e:
            result["errors"].append(f"Validation failed: {e}")

        return result

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get supported file formats for each document type.

        Returns:
            Dictionary mapping document types to supported extensions
        """
        return {
            "knowledge": [".pdf", ".md", ".markdown", ".txt"],
            "question_bank": [".csv"]
        }
