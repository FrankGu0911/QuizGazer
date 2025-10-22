"""
测验记录 API 端点
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, desc, select, func
from typing import Optional
from datetime import datetime
import os
import aiofiles

from database import get_async_db
from models import QuizRecord
from schemas import QuizRecordCreate, QuizRecordResponse, QuizRecordList

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/record-with-image", response_model=QuizRecordResponse)
async def create_quiz_record_with_image(
    question_text: str = Form(...),
    answer_text: str = Form(...),
    vlm_model: str = Form(...),
    llm_model: str = Form(...),
    ocr_time: float = Form(...),
    answer_time: float = Form(...),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db)
):
    """创建带图片的测验记录"""
    try:
        # 保存图片
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        file_path = os.path.join("uploads/images", filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await image.read()
            await f.write(content)
        
        # 创建记录
        record = QuizRecord(
            question_text=question_text,
            answer_text=answer_text,
            image_path=file_path,
            vlm_model=vlm_model,
            llm_model=llm_model,
            ocr_time=ocr_time,
            answer_time=answer_time,
            total_time=ocr_time + answer_time,
            user_id=user_id,
            session_id=session_id
        )
        
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        # 广播新记录给所有WebSocket连接
        try:
            from api.endpoints.websocket import manager
            await manager.broadcast({
                "type": "new_record",
                "data": record.to_dict()
            })
        except Exception as e:
            print(f"WebSocket广播失败: {e}")
        
        return record
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records", response_model=QuizRecordList)
async def get_quiz_records(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """获取测验记录列表"""
    try:
        # 构建查询
        query = select(QuizRecord)
        
        # 用户过滤
        if user_id:
            query = query.where(QuizRecord.user_id == user_id)
        
        # 搜索过滤
        if search:
            query = query.where(
                or_(
                    QuizRecord.question_text.contains(search),
                    QuizRecord.answer_text.contains(search)
                )
            )
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        paginated_query = query.order_by(desc(QuizRecord.timestamp)).offset(skip).limit(limit)
        result = await db.execute(paginated_query)
        records = result.scalars().all()
        
        # 计算页数
        pages = (total + limit - 1) // limit
        page = (skip // limit) + 1
        
        return QuizRecordList(
            records=records,
            total=total,
            page=page,
            pages=pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/record/{record_id}", response_model=QuizRecordResponse)
async def get_quiz_record(
    record_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个测验记录"""
    query = select(QuizRecord).where(QuizRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/record/{record_id}")
async def delete_quiz_record(
    record_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """删除测验记录"""
    query = select(QuizRecord).where(QuizRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # 删除图片文件
    if record.image_path and os.path.exists(record.image_path):
        try:
            os.remove(record.image_path)
        except:
            pass
    
    await db.delete(record)
    await db.commit()
    
    return {"message": "Record deleted successfully"}
