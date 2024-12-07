# app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate
from typing import List
from datetime import datetime


async def create_task(db: AsyncSession, task: TaskCreate):
    db_task = Task(**task.dict())
    db_task.created_at = datetime.utcnow()  # Set created_at
    db_task.updated_at = datetime.utcnow()  # Set updated_at
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


async def get_tasks(db: AsyncSession, page: int, size: int, user_id: int = None) -> (List[Task], int):
    query = select(Task)

    # Apply the filter if user_id is provided
    if user_id:
        query = query.where(Task.user_id == user_id)

    # Get total count with the filter applied
    total = await db.scalar(select(func.count(Task.task_id)).where(Task.user_id == user_id) if user_id else select(func.count(Task.task_id)))

    # Execute query with pagination
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    tasks = result.scalars().all()

    return tasks, total


async def get_task(db: AsyncSession, task_id: int):
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    return result.scalars().first()


async def delete_task(db: AsyncSession, task_id: int):
    task = await get_task(db, task_id)
    await db.delete(task)
    await db.commit()
    return task
