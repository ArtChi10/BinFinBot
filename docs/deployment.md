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

Create a deploy directory on the server:

```bash
mkdir -p ~/BinFinBot
```

GitHub Actions will upload the source archive and create `.env` from GitHub
Secrets during deploy.

## GitHub Secrets

Create these secrets in GitHub:

```text
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
DEPLOY_PATH
TELEGRAM_BOT_TOKEN
POSTGRES_PASSWORD
```

Optional secrets:

```text
DEPLOY_PORT
POSTGRES_DB
POSTGRES_USER
```

Recommended values:

```text
DEPLOY_HOST=your.server.ip
DEPLOY_USER=deploy
DEPLOY_PORT=22
DEPLOY_PATH=/home/deploy/BinFinBot
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
POSTGRES_DB=binfinbot
POSTGRES_USER=binfinbot
POSTGRES_PASSWORD=use_a_long_random_password
```

`DATABASE_URL` is assembled by `docker-compose.yml` for the bot container.
Use a URL-safe password for `POSTGRES_PASSWORD` or URL-encode special characters.

## SSH Key

Create a deploy key on your local machine:

```bash
ssh-keygen -t ed25519 -C "binfinbot-deploy" -f binfinbot_deploy_key
```

Add the public key to the server user:

```bash
cat binfinbot_deploy_key.pub
```

Put that line into:

```text
/home/deploy/.ssh/authorized_keys
```

Add the private key content to GitHub Secret:

```text
DEPLOY_SSH_KEY
```

## Manual Start

Manual start is useful for first server validation. After GitHub Actions has
deployed the files once, run:

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

Push to `main`. GitHub Actions will run CI and then deploy by SSH:

```text
CI: ruff, compileall, unittest
CD: upload source, write .env, docker compose up -d --build
```

Manual update remains possible with `docker compose up -d --build` inside
`DEPLOY_PATH`.

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
