from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from fastapi.encoders import jsonable_encoder


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "in_progress"
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    user_id: int


class TaskUpdate(TaskBase):
    title: Optional[str] = None


class TaskResponse(TaskBase):
    task_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    links: Optional[Dict[str, str]]  # Make links optional

    class Config:
        from_attributes = True

    def dict(self, *args, **kwargs):
        response_dict = super().model_dump_json(*args, **kwargs)
        return response_dict


class PaginatedTaskResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    size: int
    links: Dict[str, str]
