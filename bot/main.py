import asyncio
import json
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from api_client import create_task, delete_task, fetch_json, get_tasks, toggle_task
from keyboards import main_menu, task_actions
from states import TaskForm

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

TOKEN = getenv("BOT_TOKEN")
DASHBOARD_URL = getenv("DASHBOARD_URL", "http://localhost:8000/dashboard")
dp = Dispatcher()


def format_api_reply(method: str, path: str, data: dict | list) -> str:
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return (
        "✅ <b>Бот → API</b>\n"
        f"<code>{method} {path}</code>\n\n"
        "📦 <b>Ответ API:</b>\n"
        f"<pre>{body}</pre>\n\n"
        f"👀 Dashboard: {DASHBOARD_URL}"
    )


def format_tasks(tasks: list[dict]) -> str:
    if not tasks:
        return "📭 У тебя пока нет задач.\nНажми «➕ Добавить задачу»."

    lines = ["📋 <b>Твои задачи:</b>", ""]
    for task in tasks:
        mark = "✅" if task.get("done") else "🟡"
        lines.append(f"{mark} <b>#{task['id']}</b> {task['title']}")
    lines.append("\nИспользуй кнопки под задачей для управления.")
    return "\n".join(lines)


async def send_tasks(message: Message, user_id: str) -> None:
    tasks = await get_tasks(user_id)
    await message.answer(format_tasks(tasks), parse_mode=ParseMode.HTML)

    for task in tasks[:5]:
        status = "выполнена" if task.get("done") else "в работе"
        await message.answer(
            f"#{task['id']} — {task['title']} ({status})",
            reply_markup=task_actions(task["id"]),
        )


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Это <b>Task Tracker</b>.\n\n"
        "Бот работает через FastAPI и сохраняет задачи в SQLite.\n"
        "Открой dashboard в браузере:\n"
        f"{DASHBOARD_URL}\n\n"
        "Используй кнопки меню ниже 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Как демонстрировать проект:</b>\n"
        f"1. Открой {DASHBOARD_URL}\n"
        "2. Нажми «➕ Добавить задачу»\n"
        "3. Введи текст задачи\n"
        "4. На dashboard увидишь HTTP-запрос и новую задачу\n\n"
        "<b>Команды:</b>\n"
        "/tasks — список задач\n"
        "/add — добавить задачу\n"
        "/status — статус API",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("tasks"))
@dp.message(F.text == "📋 Мои задачи")
async def cmd_tasks(message: Message) -> None:
    user_id = str(message.from_user.id)
    await send_tasks(message, user_id)


@dp.message(Command("add"))
@dp.message(F.text == "➕ Добавить задачу")
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(TaskForm.waiting_title)
    await message.answer("Введи название задачи (до 200 символов):")


@dp.message(TaskForm.waiting_title)
async def process_task_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Текст не может быть пустым. Попробуй ещё раз:")
        return

    user_id = str(message.from_user.id)
    task = await create_task(title=title, user_id=user_id)
    await state.clear()

    await message.answer(
        format_api_reply("POST", "/api/tasks", task),
        parse_mode=ParseMode.HTML,
    )
    await message.answer(
        f"🎉 Задача <b>#{task.get('id')}</b> сохранена!",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


@dp.message(Command("status"))
@dp.message(F.text == "📊 Статус API")
async def cmd_status(message: Message) -> None:
    stats = await fetch_json("GET", "/api/stats")
    await message.answer(
        format_api_reply("GET", "/api/stats", stats),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data.startswith("toggle:"))
async def on_toggle(callback: CallbackQuery) -> None:
    task_id = int(callback.data.split(":", 1)[1])
    task = await toggle_task(task_id)
    await callback.answer("Статус обновлён")
    await callback.message.answer(
        format_api_reply("PATCH", f"/api/tasks/{task_id}/toggle", task),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data.startswith("delete:"))
async def on_delete(callback: CallbackQuery) -> None:
    task_id = int(callback.data.split(":", 1)[1])
    result = await delete_task(task_id)
    await callback.answer("Задача удалена")
    await callback.message.answer(
        format_api_reply("DELETE", f"/api/tasks/{task_id}", result),
        parse_mode=ParseMode.HTML,
    )


@dp.message(F.text)
async def fallback(message: Message) -> None:
    await message.answer("Используй кнопки меню или /help", reply_markup=main_menu())


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
