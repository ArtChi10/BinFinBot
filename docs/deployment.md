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

Fill secrets and Postgres settings:

```text
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
POSTGRES_DB=binfinbot
POSTGRES_USER=binfinbot
POSTGRES_PASSWORD=use_a_long_random_password
```

`DATABASE_URL` is assembled by `docker-compose.yml` for the bot container.
Use a URL-safe password for `POSTGRES_PASSWORD` or URL-encode special characters.

Start Postgres and the bot:

```bash
docker compose up -d --build
```

Check logs:

```bash
docker compose logs -f bot
```

Check Postgres logs:

```bash
docker compose logs -f postgres
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

Restart the full stack:

```bash
docker compose restart
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

Postgres data is stored in the Docker volume:

```text
binfinbot_postgres_data
```

Backup example:

```bash
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  > "binfinbot_$(date +%Y%m%d_%H%M%S).sql"
```

Restore example:

```bash
cat backup.sql | docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB"
```

## Network Checks

If the bot cannot connect, check Telegram and Bybit access from the server:

```bash
docker compose run --rm bot python -c "import socket; print(socket.getaddrinfo('api.telegram.org', 443))"
docker compose run --rm bot python scripts/check_bybit_market_data.py --limit 5 --timeframe 5m --ohlcv-limit 20
```

Check that the bot can reach Postgres:

```bash
docker compose run --rm bot python -c "from src.bot.config import load_config; print(load_config().database_url)"
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## Notes

- Do not commit `.env`.
- The bot does not expose HTTP ports.
- `restart: unless-stopped` keeps the bot running after crashes or server reboot.
- Local development can still use `DATABASE_PATH=bot.sqlite3` without Postgres.
