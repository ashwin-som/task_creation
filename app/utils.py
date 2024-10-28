# app/utils.py
from fastapi import Request
from typing import List


def get_pagination_links(request: Request, page: int, size: int, total: int):
    base_url = str(request.url).split("?")[0]
    links = {
        "self": f"{base_url}?page={page}&size={size}",
        "first": f"{base_url}?page=1&size={size}",
        "last": f"{base_url}?page={(total + size - 1) // size}&size={size}",
    }
    if page > 1:
        links["prev"] = f"{base_url}?page={page - 1}&size={size}"
    if page * size < total:
        links["next"] = f"{base_url}?page={page + 1}&size={size}"
    return links


def get_hateoas_links(task_id: int):
    return {
        "self": f"/tasks/{task_id}",
        "update": f"/tasks/{task_id}",
        "delete": f"/tasks/{task_id}"
    }
