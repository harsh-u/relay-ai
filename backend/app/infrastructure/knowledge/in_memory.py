from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.domain.embedding.similarity import cosine_similarity
from backend.app.domain.knowledge.answered_question import AnsweredQuestion
from backend.app.domain.knowledge.repository import AnsweredQuestionRepository


@dataclass(slots=True)
class _Entry:
    agent_id: str
    answered_question: AnsweredQuestion
    embedding: list[float]
    source_conversation_id: str | None = None


class InMemoryAnsweredQuestionRepository(AnsweredQuestionRepository):
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], list[_Entry]] = {}

    async def save(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str,
        question: str,
        answer: str,
        embedding: list[float],
        dedup_similarity_threshold: float,
        conversation_id: str | None,
    ) -> None:
        entries = self._entries.setdefault((tenant_id, business_id), [])

        for entry in entries:
            if entry.agent_id != agent_id:
                continue

            if cosine_similarity(embedding, entry.embedding) >= dedup_similarity_threshold:
                entry.answered_question = AnsweredQuestion(
                    agent_id=agent_id,
                    question=question,
                    answer=answer,
                    created_at=datetime.now(UTC),
                )
                entry.embedding = embedding
                entry.source_conversation_id = conversation_id
                return

        entries.append(
            _Entry(
                agent_id=agent_id,
                answered_question=AnsweredQuestion(
                    agent_id=agent_id,
                    question=question,
                    answer=answer,
                    created_at=datetime.now(UTC),
                ),
                embedding=embedding,
                source_conversation_id=conversation_id,
            )
        )

    async def find_most_similar(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
        embedding: list[float],
        min_created_at: datetime,
        exclude_conversation_id: str | None,
    ) -> tuple[AnsweredQuestion, float] | None:
        entries = self._entries.get((tenant_id, business_id), [])

        best: tuple[AnsweredQuestion, float] | None = None

        for entry in entries:
            if agent_id is not None and entry.agent_id != agent_id:
                continue

            if entry.answered_question.created_at < min_created_at:
                continue

            if (
                exclude_conversation_id is not None
                and entry.source_conversation_id == exclude_conversation_id
            ):
                continue

            similarity = cosine_similarity(embedding, entry.embedding)

            if best is None or similarity > best[1]:
                best = (entry.answered_question, similarity)

        return best

    async def clear(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
    ) -> int:
        key = (tenant_id, business_id)
        entries = self._entries.get(key, [])

        if agent_id is None:
            deleted = len(entries)
            self._entries[key] = []
            return deleted

        remaining = [entry for entry in entries if entry.agent_id != agent_id]
        deleted = len(entries) - len(remaining)
        self._entries[key] = remaining

        return deleted

    async def list_all(
        self,
        tenant_id: str,
        business_id: str,
        agent_id: str | None,
    ) -> list[AnsweredQuestion]:
        entries = self._entries.get((tenant_id, business_id), [])

        matching = [
            entry.answered_question
            for entry in entries
            if agent_id is None or entry.agent_id == agent_id
        ]

        return sorted(matching, key=lambda question: question.created_at, reverse=True)
