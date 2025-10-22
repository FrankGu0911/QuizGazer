"""
数据模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from database import Base


class QuizRecord(Base):
    """测验记录模型"""
    __tablename__ = "quiz_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_path = Column(String(500))
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    
    # 模型信息
    vlm_model = Column(String(100))
    llm_model = Column(String(100))
    
    # 性能信息
    ocr_time = Column(Float)
    answer_time = Column(Float)
    total_time = Column(Float)
    
    # 用户信息
    user_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    
    # 元数据
    image_size = Column(String(20))
    confidence_score = Column(Float)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
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
