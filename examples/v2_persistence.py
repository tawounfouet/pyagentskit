"""Minimal offline PyAgentsKit V2 persistence example."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from pyagentskit.adapters.persistence import SQLiteUnitOfWork
from pyagentskit.domain import Artifact, Conversation, IntegrationEvent, Session


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pyagentskit-v2-persistence-") as temporary:
        database = Path(temporary) / "state.sqlite3"
        uow = SQLiteUnitOfWork(database)

        session = Session()
        conversation = Conversation(session_id=session.id)
        artifact = Artifact(name="result.json")
        event = IntegrationEvent(
            name="conversation.created",
            aggregate_type="Conversation",
            aggregate_id=str(conversation.id),
        )

        async with uow:
            await uow.sessions.add(session)
            await uow.conversations.add(conversation)
            await uow.artifacts.add(artifact)
            await uow.outbox.append(event)
            await uow.commit()

        restored = await uow.conversations.get(conversation.id)
        claimed = await uow.outbox.claim_batch(worker_id="example-publisher")

        assert restored == conversation
        assert claimed and claimed[0].event.event_id == event.event_id

        print("Persistence V2 transaction committed.")
        print(f"session={session.id}")
        print(f"conversation={conversation.id}")
        print(f"artifact={artifact.id}")
        print(f"outbox_event={event.event_id}")

        await uow.close()


if __name__ == "__main__":
    asyncio.run(main())
