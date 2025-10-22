"""
Pydantic 数据验证模型
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class QuizRecordBase(BaseModel):
    """测验记录基础模型"""
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
    """创建测验记录"""
    pass


class QuizRecordResponse(QuizRecordBase):
    """测验记录响应"""
    id: int
    timestamp: datetime
    image_size: Optional[str] = None

    class Config:
        from_attributes = True


class QuizRecordList(BaseModel):
    """测验记录列表"""
    records: List[QuizRecordResponse]
    total: int
    page: int
    pages: int


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_quizzes: int
    avg_processing_time: float
    most_used_models: dict
    today_count: int
    this_week_count: int


class ExportRequest(BaseModel):
    """导出请求"""
    record_ids: List[int]
    export_format: str = "json"
    include_images: bool = True
