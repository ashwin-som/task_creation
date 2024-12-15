import logging
import time
from sqlalchemy.orm import Session
import datetime
from app.config import settings
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.background import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, crud, schemas
from app.database import engine, get_db
from app.utils import get_pagination_links, get_hateoas_links
from starlette.responses import JSONResponse
import asyncio
import redis.asyncio as aioredis
import json
from fastapi.testclient import TestClient

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Middleware to log requests before and after


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    logger.info(
        f"Response status: {response.status_code} | Time: {process_time:.4f}s")
    return response

# Define lifespan as an async generator


async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield  # End of startup phase

app.lifespan = lifespan

# In-memory store for tracking pending tasks
pending_tasks = {}


@app.post("/tasks/async-create", status_code=status.HTTP_202_ACCEPTED)
async def async_create_task(
    request: Request,
    task: schemas.TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Asynchronously create a task and return a 202 Accepted response.
    """
    placeholder_task_id = f"temp-{int(time.time() * 1000)}"
    logger.info(f"Task creation accepted: {placeholder_task_id}")
    pending_tasks[placeholder_task_id] = "processing"

    async def create_task_in_background():
        db_task = await crud.create_task(db=db, task=task)
        logger.info(f"Task successfully created: {db_task.task_id}")
        # Remove placeholder and map to actual task ID if needed
        pending_tasks.pop(placeholder_task_id, None)

    # Add the task to background processing
    background_tasks.add_task(create_task_in_background)

    # Respond with 202 and placeholder ID
    headers = {"Location": f"{request.url}/{placeholder_task_id}"}
    response_data = {
        "message": "Task creation in progress",
        "task_id": placeholder_task_id
    }

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response_data, headers=headers)


@app.get("/tasks", response_model=schemas.PaginatedTaskResponse)
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
async def read_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get task details or handle pending tasks.
    """
    # Check if the task is in progress
    if task_id.startswith("temp-"):
        if task_id in pending_tasks:
            return {
                "task_id": task_id,
                "status": "processing",
                "message": "The task is still being created. Please check back later."
            }
        else:
            raise HTTPException(
                status_code=404, detail="Task not found or already processed.")

    # Fetch the task from the database
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Construct response for completed task
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
    #print('ipdated_data:',update_data)
    '''for key, value in update_data.items():
        if value is not None:
            setattr(db_task, key, value)'''
    db_task.title = task.title if task.title is not None else db_task.title
    db_task.description = task.description if task.description is not None else db_task.description
    db_task.status = "completed"  # Set the task status to completed
    db_task.priority = task.priority if task.priority is not None else db_task.priority
    db_task.due_date = task.due_date if task.due_date is not None else db_task.due_date
    db_task.updated_at = datetime.datetime.utcnow()  # Update the timestamp
    # Commit the changes to the database
    await db.commit()
    #await db.refresh(db_task)  # Refresh to get the updated data
    headers = {"Location": f"{request.url}"}
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Task update accepted."}, headers=headers)

@app.post("/tasks", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
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


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(db_task)
    await db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

async def process_tasks():
    redis_connection = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    while True:
        try: 
            task_data = await redis_connection.brpop("task_queue")
            task = json.loads(task_data[1])
            task_data = task['task_data']
            task_id = task['task_id']
            print(f"Executing task: {task}")

            client = TestClient(app)
            response = client.put(f"/tasks/{task_id}",json=task_data)
            
            print(f"Task update completed")
            return status.HTTP_200_OK
        except Exception as e:
            raise HTTPException(
                status_code=404, detail="Something went wrong")




@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_tasks())
