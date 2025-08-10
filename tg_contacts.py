import asyncio
import csv
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

import typer
from rich import print as rprint
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    ChannelParticipantsAdmins,
    ChannelParticipantsSearch,
    Message,
    User,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

app = typer.Typer(add_completion=False, help="Парсер контактов Telegram (обсуждения каналов и чаты)")


@dataclass
class Filters:
    months: int = 6
    last_seen_days: int = 7
    exclude_admins: bool = True
    include_message: bool = False


def build_client(session_name: str, api_id: int, api_hash: str) -> TelegramClient:
    sessions_dir = os.path.join(os.path.dirname(__file__), "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    session_path = os.path.join(sessions_dir, session_name)
    return TelegramClient(session_path, api_id, api_hash)


def to_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def cutoff_dt(months: int) -> datetime:
    return to_utc_now() - timedelta(days=30 * months)


def is_user_recently_active(user: User, last_seen_days: int) -> bool:
    if user.bot or getattr(user, "deleted", False):
        return False
    status = getattr(user, "status", None)
    if status is None:
        return False
    if isinstance(status, UserStatusOnline):
        return True
    if isinstance(status, UserStatusOffline):
        last = status.was_online
        if last is None:
            return False
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (to_utc_now() - last) <= timedelta(days=last_seen_days)
    if isinstance(status, (UserStatusRecently, UserStatusLastWeek)):
        return True
    if isinstance(status, UserStatusLastMonth):
        return last_seen_days >= 30
    return False


async def safe_sleep(base_delay: float) -> None:
    jitter = random.uniform(0, base_delay)
    await asyncio.sleep(base_delay + jitter)


async def handle_flood_wait(exc: Exception) -> None:
    if isinstance(exc, errors.FloodWaitError):
        wait_s = max(exc.seconds, 1)
        rprint(f"[yellow]FloodWait: ждём {wait_s} сек…[/yellow]")
        await asyncio.sleep(wait_s + 1)


def export_csv(rows: List[Dict[str, str]], out_path: str) -> None:
    if not rows:
        rprint("[yellow]Нет данных для экспорта[/yellow]")
        return
    fieldnames = list(rows[0].keys())
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    rprint(f"[green]Сохранено:[/green] {out_path} ({len(rows)} строк)")


async def gather_user_rows(
    client: TelegramClient,
    user_ids: Iterable[int],
    admin_ids: Set[int],
    filt: Filters,
    last_message_by_user: Optional[Dict[int, str]] = None,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for uid in user_ids:
        try:
            full = await client(GetFullUserRequest(uid))
        except Exception as e:
            await handle_flood_wait(e)
            rprint(f"[red]Не удалось получить пользователя {uid}:[/red] {e}")
            continue
        user: User = getattr(full, "user", None) or getattr(full, "users", [None])[0]
        about: str = getattr(getattr(full, "full_user", None), "about", "") or ""
        if user is None:
            continue
        if not is_user_recently_active(user, filt.last_seen_days):
            continue
        if filt.exclude_admins and user.id in admin_ids:
            continue
        username = f"@{user.username}" if getattr(user, "username", None) else ""
        name_parts = [p for p in [user.first_name, user.last_name] if p]
        name = " ".join(name_parts)
        phone = getattr(user, "phone", None) or ""
        row = {
            "username": username,
            "name": name,
            "bio": about.replace("\r", " ").replace("\n", " ").strip(),
            "user_id": str(user.id),
            "phone": phone,
            "profile_link": f"https://t.me/{user.username}" if user.username else "",
        }
        if filt.include_message and last_message_by_user is not None:
            row["last_message"] = last_message_by_user.get(user.id, "")
        rows.append(row)
        await safe_sleep(0.05)
    return rows


async def collect_admin_ids(client: TelegramClient, chat) -> Set[int]:
    try:
        admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins)
        return {u.id for u in admins}
    except Exception:
        return set()


async def collect_active_user_ids_from_messages(
    client: TelegramClient,
    chat,
    months: int,
    include_text: bool = False,
) -> Tuple[Set[int], Optional[Dict[int, str]]]:
    cutoff = cutoff_dt(months)
    user_ids: Set[int] = set()
    last_message_by_user: Optional[Dict[int, str]] = {} if include_text else None

    async for msg in client.iter_messages(chat, reverse=True):
        if isinstance(msg, Message):
            msg_dt = msg.date
            if msg_dt and msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
            if msg_dt and msg_dt < cutoff:
                continue
            if msg.sender_id:
                user_ids.add(msg.sender_id)
                if include_text and last_message_by_user is not None and msg.message:
                    last_message_by_user[msg.sender_id] = msg.message
        await safe_sleep(0.0)
    return user_ids, last_message_by_user


async def parse_discussion(
    client: TelegramClient,
    channel_link: str,
    filt: Filters,
    base_delay: float,
) -> List[Dict[str, str]]:
    entity = await client.get_entity(channel_link)
    full = await client(GetFullChannelRequest(entity))

    linked_chat_id = getattr(full.full_chat, "linked_chat_id", None)
    discussion = None
    if linked_chat_id:
        discussion = await client.get_entity(linked_chat_id)
        rprint(f"Обсуждение: [bold]{getattr(discussion, 'title', str(linked_chat_id))}[/bold]")
    else:
        rprint("[yellow]У канала нет linked_chat_id. Пробуем собрать комментаторов из последних постов…[/yellow]")

    user_ids: Set[int] = set()
    last_message_by_user: Optional[Dict[int, str]] = {} if filt.include_message else None

    if discussion is not None:
        ids, last_map = await collect_active_user_ids_from_messages(
            client, discussion, filt.months, include_text=filt.include_message
        )
        user_ids |= ids
        if filt.include_message and last_message_by_user is not None and last_map is not None:
            last_message_by_user.update(last_map)
    else:
        cutoff = cutoff_dt(filt.months)
        async for post in client.iter_messages(entity, reverse=True, limit=400):
            if not getattr(post, "replies", None) or not post.replies.replies:
                continue
            # replies to this post live in the discussion thread
            try:
                async for cm in client.iter_messages(entity, reply_to=post.id, reverse=True):
                    cm_dt = cm.date
                    if cm_dt and cm_dt.tzinfo is None:
                        cm_dt = cm_dt.replace(tzinfo=timezone.utc)
                    if cm_dt and cm_dt < cutoff:
                        continue
                    if cm.sender_id:
                        user_ids.add(cm.sender_id)
                        if filt.include_message and last_message_by_user is not None and cm.message:
                            last_message_by_user[cm.sender_id] = cm.message
                    await safe_sleep(0.0)
            except Exception as e:
                await handle_flood_wait(e)
                rprint(f"[yellow]Ошибка при чтении комментариев к посту {post.id}: {e}[/yellow]")
            await safe_sleep(base_delay)

    admin_ids: Set[int] = set()
    if filt.exclude_admins and discussion is not None:
        admin_ids = await collect_admin_ids(client, discussion)

    rows = await gather_user_rows(client, user_ids, admin_ids, filt, last_message_by_user)
    return rows


async def parse_chat(
    client: TelegramClient,
    chat_link: str,
    filt: Filters,
    base_delay: float,
) -> List[Dict[str, str]]:
    chat = await client.get_entity(chat_link)
    rprint(f"Чат: [bold]{getattr(chat, 'title', str(chat))}[/bold]")

    # Попытка получить ВСЕХ участников (fallback циклом при ошибке)
    participants: List[User] = []
    try:
        participants = await client.get_participants(chat, aggressive=True)
    except Exception as e:
        rprint(f"[yellow]get_participants не удался ({e}). Пробуем постранично…[/yellow]")
        offset = 0
        limit = 100
        while True:
            part = await client(
                GetParticipantsRequest(chat, ChannelParticipantsSearch("") , offset, limit, hash=0)
            )
            if not part.users:
                break
            participants.extend(part.users)
            offset += len(part.users)
            await safe_sleep(base_delay)

    ids_active, last_map = await collect_active_user_ids_from_messages(
        client, chat, filt.months, include_text=filt.include_message
    )

    admin_ids: Set[int] = set()
    if filt.exclude_admins:
        admin_ids = await collect_admin_ids(client, chat)

    # Фильтруем участников: писал за период + активность
    filtered_ids: List[int] = [u.id for u in participants if u.id in ids_active]
    rows = await gather_user_rows(client, filtered_ids, admin_ids, filt, last_map)
    return rows


@app.command()
def login(
    api_id: int = typer.Option(..., help="api_id с my.telegram.org"),
    api_hash: str = typer.Option(..., help="api_hash с my.telegram.org"),
    session: str = typer.Option("session_parser", help="Имя сессии (файл в sessions/)"),
):
    """Создать/обновить сессию входа (телефон, код, 2FA при необходимости)."""
    async def _run():
        client = build_client(session, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            phone = typer.prompt("Телефон в международном формате", type=str)
            await client.send_code_request(phone)
            code = typer.prompt("Код из Telegram/SMS", type=str)
            try:
                await client.sign_in(phone=phone, code=code)
            except errors.SessionPasswordNeededError:
                pwd = typer.prompt("Пароль 2FA", hide_input=True)
                await client.sign_in(password=pwd)
        me = await client.get_me()
        rprint(f"[green]OK[/green] Вошли как: {me.first_name} (@{getattr(me, 'username', '')})")
        await client.disconnect()

    asyncio.run(_run())


@app.command("parse-open")
def parse_open(
    channel: str = typer.Argument(..., help="Ссылка на открытый канал (https://t.me/...)"),
    months: int = typer.Option(6, help="За сколько месяцев учитывать сообщения"),
    last_seen_days: int = typer.Option(7, help="Онлайн не позже чем N дней назад"),
    exclude_admins: bool = typer.Option(True, help="Исключать админов"),
    include_message: bool = typer.Option(False, help="Добавлять последнее сообщение"),
    delay: float = typer.Option(0.5, help="Базовая задержка между запросами, сек"),
    out: str = typer.Option("out.csv", help="Путь к CSV-файлу результата"),
    session: str = typer.Option("session_parser", help="Имя сессии"),
    api_id: Optional[int] = typer.Option(None, help="api_id, если не сохранена сессия"),
    api_hash: Optional[str] = typer.Option(None, help="api_hash, если не сохранена сессия"),
):
    async def _run():
        nonlocal api_id, api_hash
        if api_id is None or api_hash is None:
            rprint("[blue]Использую существующую сессию. api_id/api_hash требуются только при login.[/blue]")
        client = build_client(session, api_id or 0, api_hash or "")
        await client.start()
        filt = Filters(months=months, last_seen_days=last_seen_days, exclude_admins=exclude_admins, include_message=include_message)
        try:
            rows = await parse_discussion(client, channel, filt, delay)
        finally:
            await client.disconnect()
        export_csv(rows, out)

    asyncio.run(_run())


@app.command("parse-chat")
def parse_chat_cmd(
    chat: str = typer.Argument(..., help="Ссылка на чат/группу (https://t.me/...)"),
    months: int = typer.Option(6, help="За сколько месяцев учитывать сообщения"),
    last_seen_days: int = typer.Option(7, help="Онлайн не позже чем N дней назад"),
    exclude_admins: bool = typer.Option(True, help="Исключать админов"),
    include_message: bool = typer.Option(False, help="Добавлять последнее сообщение"),
    delay: float = typer.Option(0.5, help="Базовая задержка между запросами, сек"),
    out: str = typer.Option("out.csv", help="Путь к CSV-файлу результата"),
    session: str = typer.Option("session_parser", help="Имя сессии"),
    api_id: Optional[int] = typer.Option(None, help="api_id, если не сохранена сессия"),
    api_hash: Optional[str] = typer.Option(None, help="api_hash, если не сохранена сессия"),
):
    async def _run():
        nonlocal api_id, api_hash
        client = build_client(session, api_id or 0, api_hash or "")
        await client.start()
        filt = Filters(months=months, last_seen_days=last_seen_days, exclude_admins=exclude_admins, include_message=include_message)
        try:
            rows = await parse_chat(client, chat, filt, delay)
        finally:
            await client.disconnect()
        export_csv(rows, out)

    asyncio.run(_run())


if __name__ == "__main__":
    app()