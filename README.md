# TG Contacts Parser (CLI)

Утилита для сбора контактов из обсуждений открытых каналов и из чатов Telegram с фильтрами и экспортом в CSV.

## Установка

1. Установите Python 3.10+.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

## Быстрый старт

1. Получите `api_id` и `api_hash` на `https://my.telegram.org` → API Development Tools.
2. Создайте сессию (один раз):

```bash
python tg_contacts.py login --api-id 123456 --api-hash YOUR_API_HASH --session session_parser
```

3. Парсинг обсуждений открытого канала:

```bash
python tg_contacts.py parse-open https://t.me/your_channel \
  --months 6 --last-seen-days 7 --exclude-admins \
  --out out.csv --session session_parser
```

4. Парсинг чата/группы (публичной или приватной — если у сессии есть доступ):

```bash
python tg_contacts.py parse-chat https://t.me/your_chat \
  --months 6 --last-seen-days 7 --exclude-admins \
  --out out_chat.csv --session session_parser
```

## Ключевые опции

- `--months` — за сколько месяцев учитывать сообщения (по умолчанию 6)
- `--last-seen-days` — был онлайн не позже N дней (по умолчанию 7)
- `--exclude-admins/--include-admins` — исключать администраторов (по умолчанию исключать)
- `--include-message/--no-include-message` — добавлять последнее сообщение пользователя (по умолчанию выключено)
- `--delay` — базовая задержка между запросами (по умолчанию 0.5 сек)
- `--out` — путь к CSV (UTF-8 BOM для Excel)

## Примечания и подводные камни

- Telegram может выдавать `FloodWait`/ограничения. Скрипт автоматически ждёт нужное время и продолжает.
- Для каналов без явного `linked_chat_id` скрипт попробует собрать авторов из комментариев к последним постам.
- Телефоны пользователей доступны редко (политика приватности). Поле может быть пустым.
- Новые/«свежие» аккаунты чаще ловят баны при агрессивном парсинге. Держите задержки и запускайте задания ночью.
- Сессия хранится в файле `sessions/<session>.session` рядом со скриптом.

## Если pip ругается на system packages

В некоторых окружениях нельзя ставить пакеты глобально. Используйте облегчённый список зависимостей:

```bash
python3 -m pip install --user -r requirements-tg.txt --break-system-packages
```

Запускайте скрипт так:

```bash
python3 tg_contacts.py --help
```