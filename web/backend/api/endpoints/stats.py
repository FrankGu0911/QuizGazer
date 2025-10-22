"""
统计信息 API 端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta

from database import get_async_db
from models import QuizRecord
from schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_async_db)):
    """获取统计信息"""
    # 总数
    total_query = select(func.count(QuizRecord.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    # 平均处理时间
    avg_query = select(func.avg(QuizRecord.total_time))
    avg_result = await db.execute(avg_query)
    avg_time = avg_result.scalar() or 0.0
    
    # 最常用的模型
    vlm_query = select(QuizRecord.vlm_model, func.count(QuizRecord.vlm_model)).group_by(QuizRecord.vlm_model)
    vlm_result = await db.execute(vlm_query)
    vlm_counts = vlm_result.all()
    
    llm_query = select(QuizRecord.llm_model, func.count(QuizRecord.llm_model)).group_by(QuizRecord.llm_model)
    llm_result = await db.execute(llm_query)
    llm_counts = llm_result.all()
    
    most_used_models = {
        "vlm": dict(vlm_counts),
        "llm": dict(llm_counts)
    }
    
    # 今日数量
    today = datetime.now().date()
    today_query = select(func.count(QuizRecord.id)).where(
        func.date(QuizRecord.timestamp) == today
    )
    today_result = await db.execute(today_query)
    today_count = today_result.scalar()
    
    # 本周数量
    week_ago = datetime.now() - timedelta(days=7)
    week_query = select(func.count(QuizRecord.id)).where(
        QuizRecord.timestamp >= week_ago
    )
    week_result = await db.execute(week_query)
    week_count = week_result.scalar()
    
    return StatsResponse(
        total_quizzes=total,
        avg_processing_time=avg_time,
        most_used_models=most_used_models,
        today_count=today_count,
        this_week_count=week_count
    )
