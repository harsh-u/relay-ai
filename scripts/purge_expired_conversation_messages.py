"""Delete conversation transcripts older than the configured retention
window (`conversation_message_ttl_hours` in Settings, default 48h).

Every read against conversation_messages is scoped to one active
conversation and looks back at most ~20 messages - nothing needs a
message once its conversation has gone cold. Running this periodically
bounds the table's growth and limits how long caller transcripts sit in
the database, instead of keeping every call forever.

Not run automatically - there's no job scheduler in this project yet.
Run it on whatever cadence fits (e.g. hourly), via cron or a Kubernetes
CronJob:

    uv run python scripts/purge_expired_conversation_messages.py
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.config.settings import get_settings
from backend.app.infrastructure.conversation.postgres import PostgresConversationStore


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    cutoff = datetime.now(UTC) - timedelta(hours=settings.conversation_message_ttl_hours)

    async with session_factory() as session:
        deleted = await PostgresConversationStore(session).purge_expired(older_than=cutoff)
        await session.commit()

    print(f"Deleted {deleted} conversation message(s) older than {cutoff.isoformat()}.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
