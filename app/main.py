import logging
from fastapi import FastAPI, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app import models, crud, schemas
from app.database import engine, get_db
from app.utils import get_pagination_links, get_hateoas_links
from starlette.responses import JSONResponse
import datetime
import time
import asyncio

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Middleware to log requests before and after


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")

    # Log before the request is processed
    start_time = time.perf_counter()

    # Call the next process in the pipeline
    response = await call_next(request)

    # Log after the request is processed
    process_time = time.perf_counter() - start_time
    logger.info(
        f"Response status: {response.status_code} | Time: {process_time:.4f}s")

    return response

# Define lifespan as an async generator


async def lifespan(app: FastAPI):
    # Startup logic
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    yield  # End of startup phase

# Set the lifespan handler
app.lifespan = lifespan


@app.post("/tasks/", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(request: Request, task: schemas.TaskCreate, db: AsyncSession = Depends(get_db)):
    db_task = await crud.create_task(db=db, task=task)

    response_data = schemas.TaskResponse(
        task_id=db_task.task_id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        priority=db_task.priority,
        due_date=db_task.due_date,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        links=get_hateoas_links(task_id=db_task.task_id)
    )

    headers = {"Location": f"{request.url}/{db_task.task_id}"}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response_data.dict(), headers=headers)


@app.get("/tasks/", response_model=schemas.PaginatedTaskResponse)
async def list_tasks(
    request: Request,
    page: int = 1,
    size: int = 10,
    user_id: int = None,  # Optional query parameter
    db: Session = Depends(get_db)
):
    # Call the synchronous CRUD function with the user_id filter
    tasks, total = await crud.get_tasks(db, page, size, user_id)
    items = [
        schemas.TaskResponse(
            task_id=task.task_id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            links=get_hateoas_links(task_id=task.task_id)
        ) for task in tasks
    ]

    links = get_pagination_links(
        request=request, page=page, size=size, total=total
    )
    return {"items": items, "total": total, "page": page, "size": size, "links": links}


@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
async def read_task(task_id: int, db: AsyncSession = Depends(get_db)):
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    response_data = schemas.TaskResponse(
        task_id=db_task.task_id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        priority=db_task.priority,
        due_date=db_task.due_date,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        links=get_hateoas_links(task_id=db_task.task_id)
    )

    return response_data


@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
async def update_task(
    task_id: int,
    request: Request,
    task: schemas.TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Fetch the task to be updated
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task fields based on the incoming data
    # Only include fields explicitly set in the request
    update_data = task.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)

    db_task.updated_at = datetime.datetime.utcnow()  # Update the timestamp

    # Commit the changes to the database
    await db.commit()
    await db.refresh(db_task)  # Refresh to get the updated data

    # Prepare response data
    response_data = schemas.TaskResponse(
        task_id=db_task.task_id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        priority=db_task.priority,
        due_date=db_task.due_date,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        links=get_hateoas_links(task_id=db_task.task_id)
    )

    # Set the headers for HATEOAS links
    headers = {"Location": f"{request.url}"}

    return JSONResponse(status_code=status.HTTP_200_OK, content=response_data.dict(), headers=headers)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(db_task)
    await db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
