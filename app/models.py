# models.py

from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

Base = declarative_base()


class Task(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # Text does not require length
    status = Column(Enum('in_progress', 'completed',
                    name='task_status'), default='in_progress')
    priority = Column(Enum('low', 'medium', 'high',
                      name='task_priority'), default='medium')
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # Add created_at
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)  # Add updated_at
