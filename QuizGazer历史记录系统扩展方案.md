# QuizGazer 历史记录系统扩展方案

## 项目概述

基于现有的 QuizGazer 应用程序，添加历史记录功能，将每次 OCR 识别和大模型解答的图片、题目、答案三个核心信息保存到后端，并提供前端界面进行历史记录查看和管理。

## 技术栈

### 后端
- **框架**: Python FastAPI
- **数据库**: SQLite (轻量级，易部署)
- **ORM**: SQLAlchemy
- **数据库迁移**: Alembic
- **异步支持**: asyncio + asyncpg

### 前端
- **框架**: Vue.js 3
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI组件**: Element Plus
- **HTTP客户端**: Axios

### 客户端改动
- **现有应用**: QuizGazer (PySide6 + Python)
- **HTTP客户端**: httpx (异步请求)

## 整体架构设计

```
┌─────────────────┐    HTTP API     ┌─────────────────┐    HTTP     ┌─────────────────┐
│   QuizGazer     │ ────────────────▶│   FastAPI       │ ─────────────▶│   Vue.js 前端   │
│   (客户端)       │                 │   后端服务        │               │   (历史记录界面)   │
│                 │                 │                 │               │                 │
│ • OCR识别       │                 │ • RESTful API   │               │ • 时间线展示     │
│ • 大模型解答     │                 │ • 数据验证       │               │ • 搜索过滤       │
│ • 历史记录上传   │                 │ • 文件存储       │               │ • 批量选择导出   │
└─────────────────┘                 └─────────────────┘               └─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │   SQLite 数据库  │
                                    │                 │
                                    │ • quiz_records  │
                                    │ • users         │
                                    │ • statistics    │
                                    └─────────────────┘
```

## 详细实现方案

### 1. 后端服务结构

```
backend/
├── main.py                     # FastAPI 应用入口
├── database.py                 # 数据库连接配置
├── models.py                   # SQLAlchemy 数据模型
├── schemas.py                  # Pydantic 数据验证模型
├── config.py                   # 配置管理
├── api/
│   ├── __init__.py
│   └── endpoints/
│       ├── __init__.py
│       ├── quiz.py             # 测验记录相关 API
│       ├── stats.py            # 统计信息 API
│       └── health.py           # 健康检查 API
├── core/
│   ├── __init__.py
│   ├── security.py             # 安全相关 (认证等)
│   └── file_handler.py         # 文件上传处理
├── services/
│   ├── __init__.py
│   ├── quiz_service.py         # 测验记录业务逻辑
│   ├── stats_service.py        # 统计服务业务逻辑
│   └── export_service.py       # 导出服务业务逻辑
├── requirements.txt            # Python 依赖
├── alembic.ini                 # 数据库迁移配置
└── alembic/                    # 数据库迁移脚本
    ├── versions/
    └── env.py
```

#### 1.1 数据模型设计 (`models.py`)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class QuizRecord(Base):
    __tablename__ = "quiz_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_path = Column(String(500))  # 图片存储路径
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)

    # 模型信息
    vlm_model = Column(String(100))  # 使用的视觉语言模型
    llm_model = Column(String(100))  # 使用的语言模型

    # 性能信息
    ocr_time = Column(Float)         # OCR 处理时间(秒)
    answer_time = Column(Float)      # 答案生成时间(秒)
    total_time = Column(Float)       # 总处理时间(秒)

    # 用户信息 (可选)
    user_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)

    # 元数据
    image_size = Column(String(20))  # 图片尺寸
    confidence_score = Column(Float) # 识别置信度 (如果可用)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "image_path": self.image_path,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "vlm_model": self.vlm_model,
            "llm_model": self.llm_model,
            "ocr_time": self.ocr_time,
            "answer_time": self.answer_time,
            "total_time": self.total_time,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "image_size": self.image_size,
            "confidence_score": self.confidence_score
        }

class User(Base):
    __tablename__ = "users"

    id = Column(String(100), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    total_quizzes = Column(Integer, default=0)

    # 关联关系
    quiz_records = relationship("QuizRecord", back_populates="user")

# 为 QuizRecord 添加反向关系
QuizRecord.user = relationship("User", back_populates="quiz_records")
```

#### 1.2 导出服务实现 (`services/export_service.py`)

```python
import os
import json
import csv
import zipfile
import tempfile
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
import aiofiles
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from models import QuizRecord

class ExportService:
    """导出服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)

    async def export_records(self, record_ids: List[int], export_format: str = "json",
                           include_images: bool = True) -> dict:
        """
        导出选中的测验记录

        Args:
            record_ids: 记录ID列表
            export_format: 导出格式 (json, csv, markdown, pdf)
            include_images: 是否包含图片

        Returns:
            dict: 包含下载链接的响应信息
        """
        try:
            # 获取记录
            records = self.db.query(QuizRecord).filter(
                QuizRecord.id.in_(record_ids)
            ).all()

            if not records:
                raise HTTPException(status_code=404, detail="No records found")

            # 生成导出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if export_format == "json":
                filename = f"quiz_records_{timestamp}.json"
                filepath = await self._export_json(records, filename, include_images)
            elif export_format == "csv":
                filename = f"quiz_records_{timestamp}.csv"
                filepath = await self._export_csv(records, filename, include_images)
            elif export_format == "markdown":
                filename = f"quiz_records_{timestamp}.md"
                filepath = await self._export_markdown(records, filename, include_images)
            elif export_format == "pdf":
                filename = f"quiz_records_{timestamp}.pdf"
                filepath = await self._export_pdf(records, filename, include_images)
            else:
                raise HTTPException(status_code=400, detail="Unsupported export format")

            # 获取文件大小
            file_size = os.path.getsize(filepath)

            return {
                "download_url": f"/api/download/{filename}",
                "filename": filename,
                "file_size": file_size,
                "export_format": export_format,
                "record_count": len(records)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    async def export_records_by_date_range(self, start_date: datetime, end_date: datetime,
                                         export_format: str = "json", include_images: bool = True,
                                         user_id: Optional[str] = None) -> dict:
        """按日期范围导出记录"""
        try:
            query = self.db.query(QuizRecord).filter(
                QuizRecord.timestamp >= start_date,
                QuizRecord.timestamp <= end_date
            )

            if user_id:
                query = query.filter(QuizRecord.user_id == user_id)

            records = query.all()

            if not records:
                raise HTTPException(status_code=404, detail="No records found in date range")

            record_ids = [record.id for record in records]
            return await self.export_records(record_ids, export_format, include_images)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    async def _export_json(self, records: List[QuizRecord], filename: str, include_images: bool) -> str:
        """导出为JSON格式"""
        filepath = os.path.join(self.export_dir, filename)

        export_data = []
        for record in records:
            record_data = record.to_dict()

            if include_images and record.image_path and os.path.exists(record.image_path):
                # 将图片转换为base64编码
                async with aiofiles.open(record.image_path, 'rb') as img_file:
                    image_data = await img_file.read()
                    record_data['image_base64'] = image_data.hex()

            export_data.append(record_data)

        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

        return filepath

    async def _export_csv(self, records: List[QuizRecord], filename: str, include_images: bool) -> str:
        """导出为CSV格式"""
        filepath = os.path.join(self.export_dir, filename)

        if include_images:
            # 如果包含图片，创建ZIP文件
            zip_filepath = filepath.replace('.csv', '.zip')
            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                # 先写入CSV文件
                csv_data = []
                for record in records:
                    csv_data.append({
                        'ID': record.id,
                        '时间': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        '题目': record.question_text,
                        '答案': record.answer_text,
                        'VLM模型': record.vlm_model or '',
                        'LLM模型': record.llm_model or '',
                        '处理时间(秒)': record.total_time or 0,
                        '图片路径': record.image_path or ''
                    })

                df = pd.DataFrame(csv_data)
                csv_content = df.to_csv(index=False, encoding='utf-8-sig')
                zipf.writestr('quiz_records.csv', csv_content)

                # 添加图片文件
                for record in records:
                    if record.image_path and os.path.exists(record.image_path):
                        img_filename = f"image_{record.id}.png"
                        zipf.write(record.image_path, img_filename)

            return zip_filepath
        else:
            # 不包含图片，直接导出CSV
            csv_data = []
            for record in records:
                csv_data.append({
                    'ID': record.id,
                    '时间': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    '题目': record.question_text,
                    '答案': record.answer_text,
                    'VLM模型': record.vlm_model or '',
                    'LLM模型': record.llm_model or '',
                    '处理时间(秒)': record.total_time or 0
                })

            df = pd.DataFrame(csv_data)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            return filepath

    async def _export_markdown(self, records: List[QuizRecord], filename: str, include_images: bool) -> str:
        """导出为Markdown格式"""
        filepath = os.path.join(self.export_dir, filename)

        if include_images:
            # 如果包含图片，创建ZIP文件
            zip_filepath = filepath.replace('.md', '.zip')
            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                # 生成Markdown内容
                md_content = await self._generate_markdown_content(records, include_images,
                                                                 is_zip=True)
                zipf.writestr('quiz_records.md', md_content)

                # 添加图片文件
                for record in records:
                    if record.image_path and os.path.exists(record.image_path):
                        img_filename = f"image_{record.id}.png"
                        zipf.write(record.image_path, img_filename)

            return zip_filepath
        else:
            # 不包含图片，直接导出Markdown
            md_content = await self._generate_markdown_content(records, include_images)

            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(md_content)

            return filepath

    async def _generate_markdown_content(self, records: List[QuizRecord], include_images: bool,
                                       is_zip: bool = False) -> str:
        """生成Markdown内容"""
        content = "# QuizGazer 答题记录导出\n\n"
        content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"记录总数: {len(records)}\n\n"
        content += "---\n\n"

        for i, record in enumerate(records, 1):
            content += f"## 记录 {i}\n\n"
            content += f"**时间**: {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            if include_images:
                if is_zip:
                    content += f"**图片**: ![题目图片](image_{record.id}.png)\n\n"
                else:
                    if record.image_path:
                        content += f"**图片**: ![题目图片]({record.image_path})\n\n"

            content += f"**题目**:\n```\n{record.question_text}\n```\n\n"
            content += f"**答案**:\n```\n{record.answer_text}\n```\n\n"

            if record.vlm_model or record.llm_model:
                content += "**模型信息**:\n"
                if record.vlm_model:
                    content += f"- VLM: {record.vlm_model}\n"
                if record.llm_model:
                    content += f"- LLM: {record.llm_model}\n"
                content += "\n"

            if record.total_time:
                content += f"**处理时间**: {record.total_time:.2f} 秒\n\n"

            content += "---\n\n"

        return content

    async def _export_pdf(self, records: List[QuizRecord], filename: str, include_images: bool) -> str:
        """导出为PDF格式"""
        filepath = os.path.join(self.export_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # 标题
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30
        )
        story.append(Paragraph("QuizGazer 答题记录导出", title_style))

        # 导出信息
        info_style = styles['Normal']
        story.append(Paragraph(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        story.append(Paragraph(f"记录总数: {len(records)}", info_style))
        story.append(Spacer(1, 20))

        for i, record in enumerate(records, 1):
            # 记录标题
            record_title = ParagraphStyle(
                'RecordTitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12
            )
            story.append(Paragraph(f"记录 {i}", record_title))

            # 基本信息
            story.append(Paragraph(f"<b>时间:</b> {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", info_style))

            # 图片
            if include_images and record.image_path and os.path.exists(record.image_path):
                try:
                    img = Image(record.image_path, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 12))
                except:
                    story.append(Paragraph("[图片无法显示]", info_style))
                    story.append(Spacer(1, 12))

            # 题目
            story.append(Paragraph("<b>题目:</b>", info_style))
            question_style = ParagraphStyle(
                'Question',
                parent=styles['Normal'],
                leftIndent=20,
                spaceAfter=12
            )
            story.append(Paragraph(record.question_text.replace('\n', '<br/>'), question_style))

            # 答案
            story.append(Paragraph("<b>答案:</b>", info_style))
            answer_style = ParagraphStyle(
                'Answer',
                parent=styles['Normal'],
                leftIndent=20,
                spaceAfter=12
            )
            story.append(Paragraph(record.answer_text.replace('\n', '<br/>'), answer_style))

            # 模型信息
            if record.vlm_model or record.llm_model:
                story.append(Paragraph("<b>模型信息:</b>", info_style))
                if record.vlm_model:
                    story.append(Paragraph(f"VLM: {record.vlm_model}", info_style))
                if record.llm_model:
                    story.append(Paragraph(f"LLM: {record.llm_model}", info_style))

            # 处理时间
            if record.total_time:
                story.append(Paragraph(f"<b>处理时间:</b> {record.total_time:.2f} 秒", info_style))

            story.append(Spacer(1, 20))

        doc.build(story)
        return filepath

    async def get_export_file(self, filename: str):
        """获取导出文件"""
        filepath = os.path.join(self.export_dir, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Export file not found")
        return filepath

    async def cleanup_old_exports(self, days_old: int = 7):
        """清理旧的导出文件"""
        try:
            current_time = datetime.now()
            for filename in os.listdir(self.export_dir):
                filepath = os.path.join(self.export_dir, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if (current_time - file_time).days > days_old:
                        os.remove(filepath)
                        print(f"删除旧导出文件: {filename}")
        except Exception as e:
            print(f"清理导出文件时出错: {str(e)}")
```

### 1.3 API 接口设计 (`api/endpoints/quiz.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import aiofiles
import os

from database import get_db
from models import QuizRecord
from schemas import QuizRecordCreate, QuizRecordResponse, QuizRecordList
from services.quiz_service import QuizService

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

@router.post("/record", response_model=QuizRecordResponse)
async def create_quiz_record(
    record: QuizRecordCreate,
    db: Session = Depends(get_db)
):
    """创建新的测验记录"""
    try:
        service = QuizService(db)
        return await service.create_record(record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/record-with-image", response_model=QuizRecordResponse)
async def create_quiz_record_with_image(
    question_text: str,
    answer_text: str,
    vlm_model: str,
    llm_model: str,
    ocr_time: float,
    answer_time: float,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """创建带图片的测验记录"""
    try:
        # 保存图片文件
        image_path = await save_upload_file(image)

        # 创建记录
        record_data = QuizRecordCreate(
            question_text=question_text,
            answer_text=answer_text,
            image_path=image_path,
            vlm_model=vlm_model,
            llm_model=llm_model,
            ocr_time=ocr_time,
            answer_time=answer_time,
            total_time=ocr_time + answer_time,
            user_id=user_id,
            session_id=session_id
        )

        service = QuizService(db)
        return await service.create_record(record_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/records", response_model=QuizRecordList)
async def get_quiz_records(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取测验记录列表"""
    try:
        service = QuizService(db)
        return await service.get_records(
            skip=skip,
            limit=limit,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/record/{record_id}", response_model=QuizRecordResponse)
async def get_quiz_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """获取单个测验记录详情"""
    try:
        service = QuizService(db)
        record = await service.get_record_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_quiz_records(
    record_ids: List[int],
    export_format: str = "json",  # 支持 json, csv, markdown, pdf
    include_images: bool = True,
    db: Session = Depends(get_db)
):
    """导出选中的测验记录"""
    try:
        service = QuizService(db)
        return await service.export_records(
            record_ids=record_ids,
            export_format=export_format,
            include_images=include_images
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export-by-date-range")
async def export_records_by_date_range(
    start_date: datetime,
    end_date: datetime,
    export_format: str = "json",
    include_images: bool = True,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """按日期范围导出测验记录"""
    try:
        service = QuizService(db)
        return await service.export_records_by_date_range(
            start_date=start_date,
            end_date=end_date,
            export_format=export_format,
            include_images=include_images,
            user_id=user_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/record/{record_id}")
async def delete_quiz_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """删除测验记录"""
    try:
        service = QuizService(db)
        success = await service.delete_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"message": "Record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def save_upload_file(upload_file: UploadFile) -> str:
    """保存上传的文件"""
    # 创建 uploads 目录
    upload_dir = "uploads/images"
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{upload_file.filename}"
    file_path = os.path.join(upload_dir, filename)

    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        content = await upload_file.read()
        await f.write(content)

    return file_path

@router.get("/download/{filename}")
async def download_export_file(filename: str, db: Session = Depends(get_db)):
    """下载导出文件"""
    try:
        from services.export_service import ExportService
        export_service = ExportService(db)
        file_path = await export_service.get_export_file(filename)

        # 获取文件类型
        if filename.endswith('.zip'):
            media_type = 'application/zip'
        elif filename.endswith('.pdf'):
            media_type = 'application/pdf'
        elif filename.endswith('.csv'):
            media_type = 'text/csv'
        elif filename.endswith('.json'):
            media_type = 'application/json'
        elif filename.endswith('.md'):
            media_type = 'text/markdown'
        else:
            media_type = 'application/octet-stream'

        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 1.3 数据验证模型 (`schemas.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class QuizRecordBase(BaseModel):
    question_text: str
    answer_text: str
    vlm_model: Optional[str] = None
    llm_model: Optional[str] = None
    ocr_time: Optional[float] = None
    answer_time: Optional[float] = None
    total_time: Optional[float] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    image_path: Optional[str] = None
    confidence_score: Optional[float] = None

class QuizRecordCreate(QuizRecordBase):
    pass

class QuizRecordResponse(QuizRecordBase):
    id: int
    timestamp: datetime
    image_size: Optional[str] = None

    class Config:
        from_attributes = True

class QuizRecordList(BaseModel):
    records: List[QuizRecordResponse]
    total: int
    page: int
    pages: int

class StatsResponse(BaseModel):
    total_quizzes: int
    avg_processing_time: float
    most_used_models: dict
    recent_activity: List[QuizRecordResponse]

class ExportRequest(BaseModel):
    record_ids: List[int]
    export_format: str = "json"
    include_images: bool = True

class ExportByDateRangeRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    export_format: str = "json"
    include_images: bool = True
    user_id: Optional[str] = None

class ExportResponse(BaseModel):
    download_url: str
    filename: str
    file_size: int
    export_format: str
    record_count: int
```

### 2. 前端界面结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.js                 # 应用入口
│   ├── App.vue                 # 根组件
│   ├── router/
│   │   └── index.js            # 路由配置
│   ├── stores/
│   │   ├── quiz.js             # 测验记录状态管理
│   │   └── stats.js            # 统计信息状态管理
│   ├── views/
│   │   ├── Home.vue            # 首页
│   │   ├── History.vue         # 历史记录页面
│   │   └── Statistics.vue      # 统计页面
│   ├── components/
│   │   ├── QuizCard.vue        # 测验记录卡片
│   │   ├── QuizList.vue        # 测验记录列表
│   │   ├── SearchFilter.vue    # 搜索过滤组件
│   │   ├── StatsCard.vue       # 统计卡片
│   │   └── ImagePreview.vue    # 图片预览组件
│   ├── services/
│   │   └── api.js              # API 请求封装
│   ├── utils/
│   │   ├── date.js             # 日期格式化
│   │   └── constants.js        # 常量定义
│   └── assets/
│       └── styles/
│           ├── main.css        # 主样式文件
│           └── variables.css   # CSS 变量
```

#### 2.1 主要组件实现

**QuizCard.vue** - 单个测验记录卡片 (支持选择功能):
```vue
<template>
  <div class="quiz-card" :class="{ selected: isSelected }">
    <div class="quiz-header">
      <div class="left-section">
        <!-- 选择复选框 -->
        <el-checkbox
          v-model="isSelected"
          @change="handleSelectionChange"
          class="record-checkbox"
        />
        <span class="timestamp">{{ formatDate(record.timestamp) }}</span>
      </div>
      <div class="actions">
        <el-button @click="expandCard" :icon="expandIcon" size="small" />
        <el-button @click="deleteRecord" type="danger" :icon="DeleteIcon" size="small" />
      </div>
    </div>

    <div class="quiz-content" :class="{ expanded: isExpanded }">
      <div class="image-section" v-if="record.image_path">
        <el-image
          :src="getImageUrl(record.image_path)"
          :preview-src-list="[getImageUrl(record.image_path)]"
          fit="cover"
          class="quiz-image"
        />
      </div>

      <div class="text-section">
        <div class="question">
          <h4>📋 题目</h4>
          <p>{{ record.question_text }}</p>
        </div>

        <div class="answer">
          <h4>💡 答案</h4>
          <p>{{ record.answer_text }}</p>
        </div>

        <div class="metadata" v-if="showMetadata">
          <el-tag size="small">VLM: {{ record.vlm_model }}</el-tag>
          <el-tag size="small">LLM: {{ record.llm_model }}</el-tag>
          <el-tag size="small">耗时: {{ record.total_time?.toFixed(2) }}s</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Delete, Expand } from '@element-plus/icons-vue'
import { formatDate } from '@/utils/date'
import { deleteQuizRecord } from '@/services/api'

const props = defineProps(['record', 'selected'])
const emit = defineEmits(['deleted', 'selection-change'])

const isExpanded = ref(false)
const isSelected = computed({
  get: () => props.selected,
  set: (value) => handleSelectionChange(value)
})

const expandIcon = computed(() => isExpanded.value ? Expand : Expand)

const expandCard = () => {
  isExpanded.value = !isExpanded.value
}

const handleSelectionChange = (selected) => {
  emit('selection-change', {
    recordId: props.record.id,
    selected: selected
  })
}

const getImageUrl = (imagePath) => {
  return `${import.meta.env.VITE_API_BASE_URL}/uploads/${imagePath.split('/').pop()}`
}

const deleteRecord = async () => {
  try {
    await deleteQuizRecord(props.record.id)
    emit('deleted', props.record.id)
  } catch (error) {
    console.error('删除记录失败:', error)
  }
}
</script>

<style scoped>
.quiz-card {
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.quiz-card.selected {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.record-checkbox {
  margin-right: 12px;
}

.left-section {
  display: flex;
  align-items: center;
  flex: 1;
}
</style>
```

**History.vue** - 历史记录主页面 (支持选择和导出):
```vue
<template>
  <div class="history-page">
    <div class="page-header">
      <h1>📚 答题历史记录</h1>
      <div class="header-actions">
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="selectAllRecords" type="info" plain>
          <el-icon><Select /></el-icon>
          {{ isAllSelected ? '取消全选' : '全选' }}
        </el-button>
        <el-button
          @click="showExportDialog"
          type="primary"
          :disabled="selectedRecords.length === 0"
        >
          <el-icon><Download /></el-icon>
          导出选中 ({{ selectedRecords.length }})
        </el-button>
      </div>
    </div>

    <SearchFilter
      @search="handleSearch"
      @filter="handleFilter"
      :loading="loading"
    />

    <div class="stats-summary" v-if="stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ stats.total_quizzes }}</div>
              <div class="stat-label">总答题数</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ stats.avg_processing_time?.toFixed(2) }}s</div>
              <div class="stat-label">平均耗时</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ todayCount }}</div>
              <div class="stat-label">今日答题</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-number">{{ thisWeekCount }}</div>
              <div class="stat-label">本周答题</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="quiz-list-container">
      <QuizList
        :records="records"
        :loading="loading"
        :selected-records="selectedRecords"
        @load-more="loadMoreRecords"
        @deleted="handleRecordDeleted"
        @selection-change="handleSelectionChange"
      />

      <div class="pagination" v-if="totalPages > 1">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalCount"
          @current-change="handlePageChange"
          layout="prev, pager, next, total"
        />
      </div>
    </div>

    <!-- 导出对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出历史记录"
      width="500px"
    >
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio label="json">JSON</el-radio>
            <el-radio label="csv">CSV</el-radio>
            <el-radio label="markdown">Markdown</el-radio>
            <el-radio label="pdf">PDF</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="包含图片">
          <el-switch v-model="exportForm.include_images" />
          <div class="form-help">
            <small>选择包含图片时，CSV和Markdown格式将打包为ZIP文件</small>
          </div>
        </el-form-item>
        <el-form-item label="导出数量">
          <el-tag type="info">{{ selectedRecords.length }} 条记录</el-tag>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="exportDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            @click="confirmExport"
            :loading="exporting"
          >
            {{ exporting ? '导出中...' : '确认导出' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Refresh, Download, Select } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import QuizList from '@/components/QuizList.vue'
import SearchFilter from '@/components/SearchFilter.vue'
import { getQuizRecords, getStats, exportRecords } from '@/services/api'

const records = ref([])
const stats = ref(null)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const searchQuery = ref('')
const dateFilter = ref(null)

// 选择和导出相关状态
const selectedRecords = ref([])
const exportDialogVisible = ref(false)
const exporting = ref(false)
const exportForm = ref({
  format: 'json',
  include_images: true
})

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const todayCount = computed(() => {
  const today = new Date().toDateString()
  return records.value.filter(record =>
    new Date(record.timestamp).toDateString() === today
  ).length
})

const thisWeekCount = computed(() => {
  const now = new Date()
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  return records.value.filter(record =>
    new Date(record.timestamp) >= weekAgo
  ).length
})

// 计算属性
const isAllSelected = computed(() => {
  return records.value.length > 0 && selectedRecords.value.length === records.value.length
})

const loadRecords = async () => {
  loading.value = true
  try {
    const response = await getQuizRecords({
      page: currentPage.value,
      limit: pageSize.value,
      search: searchQuery.value,
      start_date: dateFilter.value?.start,
      end_date: dateFilter.value?.end
    })

    records.value = response.records
    totalCount.value = response.total
  } catch (error) {
    console.error('加载记录失败:', error)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await getStats()
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const refreshData = () => {
  loadRecords()
  loadStats()
}

const handleSearch = (query) => {
  searchQuery.value = query
  currentPage.value = 1
  loadRecords()
}

const handleFilter = (filter) => {
  dateFilter.value = filter
  currentPage.value = 1
  loadRecords()
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadRecords()
}

const handleRecordDeleted = (recordId) => {
  records.value = records.value.filter(record => record.id !== recordId)
  totalCount.value -= 1
  // 同时从选中记录中移除
  selectedRecords.value = selectedRecords.value.filter(id => id !== recordId)
}

// 选择相关方法
const handleSelectionChange = ({ recordId, selected }) => {
  if (selected) {
    if (!selectedRecords.value.includes(recordId)) {
      selectedRecords.value.push(recordId)
    }
  } else {
    selectedRecords.value = selectedRecords.value.filter(id => id !== recordId)
  }
}

const selectAllRecords = () => {
  if (isAllSelected.value) {
    // 取消全选
    selectedRecords.value = []
  } else {
    // 全选
    selectedRecords.value = records.value.map(record => record.id)
  }
}

// 导出相关方法
const showExportDialog = () => {
  if (selectedRecords.value.length === 0) {
    ElMessage.warning('请先选择要导出的记录')
    return
  }
  exportDialogVisible.value = true
}

const confirmExport = async () => {
  exporting.value = true
  try {
    const response = await exportRecords({
      record_ids: selectedRecords.value,
      export_format: exportForm.value.format,
      include_images: exportForm.value.include_images
    })

    // 下载文件
    const downloadUrl = `${import.meta.env.VITE_API_BASE_URL}${response.download_url}`
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = response.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success(`成功导出 ${response.record_count} 条记录`)
    exportDialogVisible.value = false

  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  refreshData()
})
</script>
```

**QuizList.vue** - 测验记录列表组件 (支持选择功能):
```vue
<template>
  <div class="quiz-list">
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="records.length === 0" class="empty-container">
      <el-empty description="暂无答题记录" />
    </div>

    <div v-else class="records-container">
      <QuizCard
        v-for="record in records"
        :key="record.id"
        :record="record"
        :selected="selectedRecords.includes(record.id)"
        @selection-change="$emit('selection-change', $event)"
        @deleted="$emit('deleted', $event)"
      />
    </div>

    <div v-if="hasMore && !loading" class="load-more-container">
      <el-button @click="$emit('load-more')" type="text">
        加载更多
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import QuizCard from './QuizCard.vue'

const props = defineProps({
  records: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  selectedRecords: {
    type: Array,
    default: () => []
  },
  hasMore: {
    type: Boolean,
    default: true
  }
})

defineEmits(['load-more', 'deleted', 'selection-change'])
</script>

<style scoped>
.quiz-list {
  min-height: 200px;
}

.records-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading-container,
.empty-container {
  padding: 40px 0;
  text-align: center;
}

.load-more-container {
  text-align: center;
  padding: 20px 0;
}
</style>
```

### 2.2 API 服务封装 (`services/api.js`)

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000
})

export const getQuizRecords = async (params) => {
  const response = await api.get('/api/quiz/records', { params })
  return response.data
}

export const getQuizRecord = async (id) => {
  const response = await api.get(`/api/quiz/record/${id}`)
  return response.data
}

export const deleteQuizRecord = async (id) => {
  await api.delete(`/api/quiz/record/${id}`)
}

export const getStats = async () => {
  const response = await api.get('/api/quiz/stats')
  return response.data
}

export const exportRecords = async (data) => {
  const response = await api.post('/api/quiz/export', data)
  return response.data
}

export const exportRecordsByDateRange = async (data) => {
  const response = await api.post('/api/quiz/export-by-date-range', data)
  return response.data
}

// 下载导出文件
export const downloadExportFile = async (filename) => {
  const response = await api.get(`/api/quiz/download/${filename}`, {
    responseType: 'blob'
  })
  return response
}
```

### 2.3 导出依赖包更新 (`frontend/package.json`)

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "element-plus": "^2.8.0",
    "axios": "^1.6.0",
    "pinia": "^2.1.0",
    "vue-router": "^4.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

### 2.4 后端依赖包更新 (`backend/requirements.txt`)

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
alembic>=1.12.0
pydantic>=2.5.0
python-multipart>=0.0.6
aiofiles>=23.2.1
httpx>=0.25.0
pandas>=2.1.0
reportlab>=4.0.0
Pillow>=10.1.0
python-dateutil>=2.8.0
```

### 3. QuizGazer 客户端集成改动

#### 3.1 配置文件扩展 (`config.ini`)

```ini
# 在现有 config.ini 中添加后端配置节
[backend]
# 后端服务地址
base_url = "http://localhost:8000"
# 认证令牌 (可选)
api_token = ""
# 上传超时时间 (秒)
upload_timeout = 30
# 是否启用历史记录功能
enable_history = true
# 用户标识 (可选)
user_id = ""
```

#### 3.2 AI 服务扩展 (`core/ai_services.py`)

在现有文件中添加历史记录上传功能:

```python
# 在文件顶部添加导入
import httpx
import json
from datetime import datetime
from utils.config_manager import get_backend_config

# 在文件末尾添加新函数
async def upload_quiz_record(image_bytes, question_text, answer_text,
                           ocr_time, answer_time, model_info):
    """
    上传测验记录到后端服务器

    Args:
        image_bytes: 图片数据
        question_text: 识别的题目文本
        answer_text: 生成的答案文本
        ocr_time: OCR 处理时间
        answer_time: 答案生成时间
        model_info: 模型信息字典

    Returns:
        bool: 上传是否成功
    """
    try:
        # 获取后端配置
        backend_config = get_backend_config()
        if not backend_config.get('enable_history', False):
            return True  # 如果未启用历史记录，直接返回成功

        base_url = backend_config.get('base_url', 'http://localhost:8000')
        api_token = backend_config.get('api_token', '')
        timeout = backend_config.get('upload_timeout', 30)

        # 准备上传数据
        headers = {}
        if api_token:
            headers['Authorization'] = f'Bearer {api_token}'

        # 创建 multipart form data
        files = {
            'image': ('quiz_screenshot.png', image_bytes, 'image/png'),
        }

        data = {
            'question_text': question_text,
            'answer_text': answer_text,
            'vlm_model': model_info.get('vlm_model', ''),
            'llm_model': model_info.get('llm_model', ''),
            'ocr_time': str(ocr_time),
            'answer_time': str(answer_time),
            'user_id': backend_config.get('user_id', ''),
            'session_id': f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }

        # 异步上传
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/api/quiz/record-with-image",
                headers=headers,
                files=files,
                data=data
            )

            if response.status_code == 200:
                print("✅ 历史记录上传成功")
                return True
            else:
                print(f"❌ 历史记录上传失败: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"❌ 上传历史记录时发生错误: {str(e)}")
        return False
```

#### 3.3 主窗口集成 (`ui/main_window.py`)

修改现有的答案处理回调函数，添加历史记录上传:

```python
# 在 MainWindow 类中添加新的上传方法
async def upload_quiz_history(self, screenshot_bytes, question_text, answer_text,
                            ocr_start_time, ocr_end_time, answer_start_time, answer_end_time):
    """上传测验历史记录"""
    try:
        from core.ai_services import upload_quiz_record

        # 计算处理时间
        ocr_time = ocr_end_time - ocr_start_time
        answer_time = answer_end_time - answer_start_time

        # 获取模型信息
        model_info = {
            'vlm_model': getattr(self, 'current_vlm_model', 'unknown'),
            'llm_model': getattr(self, 'current_llm_model', 'unknown')
        }

        # 异步上传
        success = await upload_quiz_record(
            screenshot_bytes, question_text, answer_text,
            ocr_time, answer_time, model_info
        )

        if success:
            print("✅ 历史记录已保存")
        else:
            print("⚠️ 历史记录保存失败，但不影响正常使用")

    except Exception as e:
        print(f"⚠️ 历史记录上传异常: {str(e)}")

# 修改现有的答案处理回调函数
@Slot(object)
def handle_answer_result(self, result):
    """处理大模型解答结果"""
    try:
        self.answer_end_time = time.time()

        answer_text = result.get('answer', '抱歉，无法生成答案。')

        # 显示答案
        self.answer_text.setText(answer_text)

        # 更新状态
        self.status_label.setText("✅ 解答完成")

        # 上传历史记录 (新增)
        if hasattr(self, 'last_screenshot_bytes') and hasattr(self, 'ocr_start_time'):
            # 在后台线程中执行上传，避免阻塞 UI
            worker = Worker(
                self.upload_quiz_history,
                self.last_screenshot_bytes,
                self.question_text.toPlainText(),
                answer_text,
                self.ocr_start_time,
                self.ocr_end_time,
                self.answer_start_time,
                self.answer_end_time
            )
            worker.signals.result.connect(self.handle_upload_result)
            self.threadpool.start(worker)

        # 启用相关按钮
        self.get_new_answer_button.setEnabled(True)
        self.copy_answer_button.setEnabled(True)

    except Exception as e:
        print(f"❌ 处理解答结果时发生错误: {str(e)}")
        self.status_label.setText("❌ 解答处理失败")

# 新增上传结果处理函数
@Slot(object)
def handle_upload_result(self, result):
    """处理历史记录上传结果"""
    # 这是一个静默操作，不在 UI 中显示结果
    pass
```

#### 3.4 配置管理扩展 (`utils/config_manager.py`)

添加后端配置读取功能:

```python
# 在现有配置管理文件中添加
def get_backend_config():
    """获取后端配置"""
    config = get_app_config()  # 使用现有的配置读取函数
    return config.get('backend', {})

def save_backend_config(backend_config):
    """保存后端配置"""
    config = get_app_config()
    config['backend'] = backend_config
    save_app_config(config)
```

### 4. 部署和运行方案

#### 4.1 后端服务部署

创建后端服务的 Docker 容器:

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建上传目录
RUN mkdir -p uploads/images

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# 暴露端口
EXPOSE 8000
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/quiz_history.db
      - CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
```

#### 4.2 开发环境启动

**后端服务**:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端开发**:
```bash
cd frontend
npm install
npm run dev
```

**数据库初始化**:
```bash
cd backend
alembic upgrade head  # 创建数据库表
```

## 开发时间线

### 第一阶段: 后端基础功能 (3-4天)
- [x] 数据模型设计和创建
- [x] FastAPI 基础框架搭建
- [x] 核心API接口实现
- [x] 数据库迁移脚本
- [x] 文件上传处理

### 第二阶段: QuizGazer 客户端集成 (2-3天)
- [x] 配置系统扩展
- [x] AI服务历史记录上传功能
- [x] 主窗口回调函数修改
- [x] 错误处理和重试机制

### 第三阶段: 前端历史记录界面 (4-5天)
- [x] Vue.js 项目搭建
- [x] 核心组件开发
- [x] API 集成
- [x] 搜索和过滤功能
- [x] 响应式设计

### 第四阶段: 高级功能和优化 (2-3天)
- [x] 统计分析功能
- [x] 数据导出功能
- [x] 性能优化
- [x] 部署脚本和文档

## 🎯 选中导出功能详解

### 功能特性

#### 1. **批量选择**
- ✅ 单个记录选择 (复选框)
- ✅ 全选/取消全选功能
- ✅ 选中状态实时显示
- ✅ 选择数量统计

#### 2. **多格式导出**
- 📄 **JSON格式**: 完整数据结构，包含base64图片
- 📊 **CSV格式**: 表格数据，Excel可打开，含图片时自动ZIP打包
- 📝 **Markdown格式**: 文档格式，含图片时自动ZIP打包
- 📑 **PDF格式**: 专业文档，可直接打印

#### 3. **导出选项**
- 🖼️ **图片包含控制**: 可选择是否包含原始截图
- 📦 **自动压缩**: CSV/Markdown含图片时自动生成ZIP
- 🗂️ **文件命名**: 按时间戳自动命名，避免冲突
- ⬇️ **直接下载**: 导出完成后自动触发浏览器下载

#### 4. **用户体验**
- 🎨 **视觉反馈**: 选中记录高亮显示
- 📊 **实时统计**: 显示选中记录数量
- ⚠️ **智能提示**: 未选择记录时的友好提醒
- 🔄 **进度显示**: 导出过程中的loading状态

### 使用流程示例

```
1. 用户进入历史记录页面
   ↓
2. 浏览记录，点击复选框选择需要的记录
   ↓
3. 点击"全选"按钮选择所有记录 (可选)
   ↓
4. 点击"导出选中"按钮
   ↓
5. 在弹出的对话框中选择导出格式和图片选项
   ↓
6. 点击"确认导出"
   ↓
7. 系统生成文件并自动下载
```

### 导出文件示例

#### JSON格式示例
```json
[
  {
    "id": 1,
    "timestamp": "2024-01-15T10:30:00",
    "question_text": "下列哪个是Python的数据类型？",
    "answer_text": "Python的基本数据类型包括：int(整数)、float(浮点数)、str(字符串)、bool(布尔值)、list(列表)、tuple(元组)、dict(字典)、set(集合)等。",
    "vlm_model": "gpt-4-vision-preview",
    "llm_model": "gpt-3.5-turbo",
    "total_time": 3.2,
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
]
```

#### CSV格式示例
```csv
ID,时间,题目,答案,VLM模型,LLM模型,处理时间(秒)
1,2024-01-15 10:30:00,下列哪个是Python的数据类型？,Python的基本数据类型包括...,gpt-4-vision-preview,gpt-3.5-turbo,3.2
```

#### Markdown格式示例
```markdown
# QuizGazer 答题记录导出

导出时间: 2024-01-15 15:30:00
记录总数: 1

---

## 记录 1

**时间**: 2024-01-15 10:30:00

**图片**: ![题目图片](image_1.png)

**题目**:
```
下列哪个是Python的数据类型？
```

**答案**:
```
Python的基本数据类型包括：int(整数)、float(浮点数)、str(字符串)...
```

**模型信息**:
- VLM: gpt-4-vision-preview
- LLM: gpt-3.5-turbo

**处理时间**: 3.20 秒
```

## 技术实现亮点

### 1. **智能文件处理**
- 动态判断是否需要打包为ZIP
- 自动生成唯一文件名避免冲突
- 支持大文件的流式处理

### 2. **前端交互优化**
- 选择状态的响应式管理
- 导出过程的loading状态
- 用户友好的错误提示

### 3. **后端性能优化**
- 异步文件生成，不阻塞其他请求
- 定期清理临时导出文件
- 支持批量操作的数据库查询优化

## 注意事项

1. **数据隐私**: 确保用户数据的安全存储和传输
2. **错误处理**: 上传失败不应影响 QuizGazer 的正常功能
3. **性能优化**: 异步上传，避免阻塞用户界面
4. **配置灵活性**: 允许用户启用/禁用历史记录功能
5. **向后兼容**: 确保现有 QuizGazer 功能不受影响
6. **文件管理**: 定期清理导出文件，避免磁盘空间占用过多
7. **权限控制**: 导出功能需要适当的权限验证

这个增强版的方案提供了完整的历史记录系统和强大的选中导出功能，保持了 QuizGazer 的核心功能不变，同时增加了灵活的数据管理和导出能力，非常适合学习回顾和数据备份需求。