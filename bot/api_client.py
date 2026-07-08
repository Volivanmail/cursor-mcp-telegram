import logging
from os import getenv
from urllib.parse import urlencode, urljoin

import aiohttp

API_BASE_URL = getenv("API_BASE_URL", "http://api:8000")


async def fetch_json(method: str, path: str, payload: dict | None = None) -> dict | list:
    url = urljoin(API_BASE_URL.rstrip("/") + "/", path.lstrip("/"))
    logging.info("API request: %s %s", method, url)
    async with aiohttp.ClientSession() as session:
        async with session.request(method=method, url=url, json=payload) as response:
            response.raise_for_status()
            return await response.json()


async def get_tasks(user_id: str) -> list[dict]:
    query = urlencode({"user_id": user_id})
    data = await fetch_json("GET", f"/api/tasks?{query}")
    return data if isinstance(data, list) else []


async def create_task(title: str, user_id: str) -> dict:
    result = await fetch_json("POST", "/api/tasks", {"title": title, "user_id": user_id})
    return result if isinstance(result, dict) else {}


async def toggle_task(task_id: int) -> dict:
    result = await fetch_json("PATCH", f"/api/tasks/{task_id}/toggle")
    return result if isinstance(result, dict) else {}


async def delete_task(task_id: int) -> dict:
    result = await fetch_json("DELETE", f"/api/tasks/{task_id}")
    return result if isinstance(result, dict) else {}
