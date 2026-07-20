FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
COPY README.md .

RUN mkdir -p /app/data && chown -R app:app /app

USER app

CMD ["python", "-m", "src.bot.main"]
