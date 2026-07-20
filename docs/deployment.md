# Server Deployment

This bot runs with Telegram long polling. It does not need an opened inbound port,
domain, nginx, or webhook. The server only needs outbound HTTPS access to Telegram
and Bybit.

## Requirements

- Linux VPS
- Docker Engine
- Docker Compose plugin
- Git

## First Deploy

Clone the project on the server:

```bash
git clone <repo-url> BinFinBot
cd BinFinBot
```

Create a server `.env` file:

```bash
cp .env.example .env
nano .env
```

Fill only secrets and local runtime settings:

```text
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
DATABASE_PATH=/app/data/bot.sqlite3
```

Start the bot:

```bash
docker compose up -d --build
```

Check logs:

```bash
docker compose logs -f bot
```

Open Telegram and send:

```text
/start
```

## Useful Commands

Stop:

```bash
docker compose down
```

Restart:

```bash
docker compose restart bot
```

Show status:

```bash
docker compose ps
```

Run tests inside the container image:

```bash
docker compose run --rm bot python -m unittest
```

## Update Deploy

Pull changes and rebuild:

```bash
git pull
docker compose up -d --build
docker compose logs -f bot
```

## Data

SQLite is stored on the server in:

```text
./data/bot.sqlite3
```

This file is ignored by git and mounted into the container as:

```text
/app/data/bot.sqlite3
```

Backup example:

```bash
cp data/bot.sqlite3 "data/bot.sqlite3.$(date +%Y%m%d_%H%M%S).bak"
```

## Network Checks

If the bot cannot connect, check Telegram and Bybit access from the server:

```bash
docker compose run --rm bot python -c "import socket; print(socket.getaddrinfo('api.telegram.org', 443))"
docker compose run --rm bot python scripts/check_bybit_market_data.py --limit 5 --timeframe 5m --ohlcv-limit 20
```

## Notes

- Do not commit `.env`.
- Do not commit `data/bot.sqlite3`.
- The bot does not expose HTTP ports.
- `restart: unless-stopped` keeps the bot running after crashes or server reboot.
