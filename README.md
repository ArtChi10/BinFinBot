# Crypto Screener Telegram Bot

Telegram-бот для MVP криптовалютного скринера. Проект умеет загружать настройки из `.env`, хранить их в SQLite, управлять ими через Telegram и отправлять уведомления, если Bybit-свечи проходят фильтр по росту объема и RSI.

## Назначение

Проект готовит основу для бота, который будет искать криптовалютные пары по простым условиям скринера: биржа, таймфрейм, изменение объема, диапазон RSI и включенные уведомления.

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Настройка окружения

Создайте локальный `.env` на основе `.env.example`:

```text
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DATABASE_PATH=bot.sqlite3
DATABASE_URL=
POSTGRES_DB=binfinbot
POSTGRES_USER=binfinbot
POSTGRES_PASSWORD=change_me
```

Реальные токены нельзя хранить в репозитории. Файл `.env` добавлен в `.gitignore`.

## Запуск

```powershell
python -m src.bot.main
```

Локально бот может использовать SQLite по пути `DATABASE_PATH`. Если задан `DATABASE_URL`, бот использует Postgres. При запуске бот автоматически создает таблицы `user_settings`, `user_popular_pair_selections`, `user_custom_pairs` и `signal_cooldowns`.

После запуска бот регистрирует команды Telegram:

```text
/menu
/settings
/status
/pairs
/addpair
/removepair
/help
```

Команда `/start` открывает постоянное меню с кнопками `Настройки`, `Статус`, `Помощь`.

## Серверный запуск

Для VPS подготовлен Docker Compose деплой:

```bash
docker compose up -d --build
docker compose logs -f bot
```

Compose поднимает Postgres и передает боту `DATABASE_URL`.

Подробная инструкция: [docs/deployment.md](docs/deployment.md).

## CI/CD

GitHub Actions workflow `.github/workflows/ci-cd.yml` запускает:

- `ruff check .`;
- `python -m compileall src tests`;
- `python -m unittest`;
- deploy на сервер по SSH после успешного push в `main`.

Для CD нужны GitHub Secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`, `TELEGRAM_BOT_TOKEN`, `POSTGRES_PASSWORD`. Опционально: `DEPLOY_PORT`, `POSTGRES_DB`, `POSTGRES_USER`.

## MVP

Текущий MVP включает:

- загрузку конфигурации из `.env`;
- автоматическую инициализацию SQLite;
- таблицу `user_settings`;
- таблицу `user_popular_pair_selections`;
- таблицу `user_custom_pairs`;
- таблицу `signal_cooldowns`;
- команду `/start`, которая создает настройки пользователя по умолчанию;
- команду `/menu`, которая открывает главное меню;
- команду `/settings`, которая показывает текущие настройки;
- команды `/status`, `/pairs`, `/addpair`, `/removepair` и `/help`;
- постоянную клавиатуру `Настройки`, `Статус`, `Помощь`;
- inline-кнопки для изменения настроек пользователя;
- фоновый мониторинг топ-150 Bybit spot `/USDT` пар;
- чеклист популярных 30 Bybit spot `/USDT` пар;
- пользовательский список произвольных Bybit spot-пар, например `ETH/BTC` или `BTC/USDC`;
- Telegram-уведомления при совпадении условий;
- cooldown по паре на длину выбранного таймфрейма.

MVP сейчас работает только с Bybit.

## Доступные настройки

Через `/settings` можно изменить:

- таймфрейм: `5m`, `15m`, `30m`;
- список пар: `Топ-150 по объему`, `Популярные 30` или `Мои пары`;
- галки внутри `Популярные 30`, чтобы мониторить только нужные пары;
- произвольные пары в режиме `Мои пары`;
- RSI-диапазон: `30–50`, `40–60`, `50–70`, `60–80`, `70–90`;
- минимальный рост объема: `0.1%`, `0.25%`, `0.5%`, `1%`, `3%`, `5%`, `10%`;
- уведомления: включены или выключены.

Режим `Топ-150 по объему` обновляет список пар раз в час по 24h quote volume Bybit. Режим `Популярные 30` открывает чеклист крупных USDT-пар: `BTC`, `ETH`, `SOL`, `XRP`, `BNB`, `DOGE`, `ADA`, `AVAX`, `LINK`, `TRX`, `TON`, `SUI`, `LTC`, `BCH`, `DOT`, `UNI`, `AAVE`, `NEAR`, `ETC`, `FIL`, `ATOM`, `ARB`, `OP`, `INJ`, `WLD`, `PEPE`, `SHIB`, `BONK`, `MNT`, `ONDO`. По умолчанию все 30 отмечены, но пользователь может снять лишние галки, выбрать все или снять все.

Режим `Мои пары` нужен для произвольных Bybit spot-пар, не только к USDT. Добавление:

```text
/addpair ETH/BTC
/addpair BTC/USDC
```

Удаление:

```text
/removepair ETH/BTC
```

Бот принимает пары с явным разделителем: `ETH/BTC`, `ETH-BTC`, `ETH BTC`. Если отдельная выбранная пара временно недоступна на Bybit spot, бот пропустит ее и продолжит мониторинг остальных.

## Проверка Bybit market data

Проект содержит smoke-скрипт для проверки реальных данных Bybit через `ccxt`. Telegram token для этой проверки не нужен.

```powershell
python scripts\check_bybit_market_data.py --limit 10 --timeframe 15m --ohlcv-limit 50
```

Скрипт получает топ spot `/USDT` пар Bybit по 24h quote volume, выводит список пар, берет первую пару и запрашивает для нее OHLCV-свечи. На этом этапе данные не сохраняются в SQLite и торговые сигналы в Telegram не отправляются.

## Signal engine

Слой `src.analysis` рассчитывает изменение объема, RSI и итоговое решение по сигналу на уже полученных OHLCV-свечах. Он не зависит от Telegram, SQLite и Bybit API, поэтому тестируется на синтетических данных без доступа к бирже.

Условия MVP-сигнала:

- рост объема последней свечи относительно предыдущей не ниже пользовательского порога;
- RSI по close-ценам находится внутри пользовательского диапазона;
- `volume_change_percent = 0.5` означает минимальный рост объема на `0.5%`.

Проверка:

```powershell
python -m unittest
```

## Telegram signal notifications

После запуска `python -m src.bot.main` бот поднимает фоновый монитор:

- берет пользователей с включенными уведомлениями;
- обновляет топ-150 Bybit spot `/USDT` пар раз в час, если выбран режим `Топ-150 по объему`;
- использует только отмеченные пары, если выбран режим `Популярные 30`;
- использует пользовательский список, если выбран режим `Мои пары`;
- каждые 60 секунд получает OHLCV по выбранным пользователями таймфреймам;
- отбрасывает текущую незакрытую свечу;
- проверяет `volume_change_percent` и RSI;
- отправляет Telegram-сообщение при совпадении условий;
- не отправляет повторный сигнал по той же паре чаще одного раза за выбранный таймфрейм.

Для ручного теста уведомлений лучше временно выбрать мягкие настройки:

```text
Таймфрейм: 5m
Минимальный рост объема: 0.1% или 0.25%
RSI: 40–90
Уведомления: включены
```

Чем шире RSI-диапазон и ниже порог объема, тем выше шанс быстро увидеть тестовое уведомление. Пороги `0.1%` и `0.25%` добавлены именно для smoke-тестирования и могут давать много шума. Это не торговая рекомендация, а способ проверить работу цепочки `Bybit -> signal engine -> Telegram`.

## Настройки по умолчанию

```text
exchange: bybit
pair_universe: top_150
timeframe: 15m
volume_change_percent: 0.5
rsi_min: 60
rsi_max: 80
notifications_enabled: true
```

Важно: значение `0.5` для `volume_change_percent` означает `0.5%`, а не `50%`.
