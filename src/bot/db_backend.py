POSTGRES_URL_PREFIXES = ("postgresql://", "postgres://")


def is_postgres_database_url(database_url: str) -> bool:
    return database_url.startswith(POSTGRES_URL_PREFIXES)


async def connect_postgres(database_url: str):
    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Postgres DATABASE_URL requires asyncpg. Install project requirements."
        ) from exc

    return await asyncpg.connect(database_url)
