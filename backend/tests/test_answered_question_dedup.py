from backend.app.infrastructure.knowledge.in_memory import InMemoryAnsweredQuestionRepository

TENANT_ID = "tenant-1"
BUSINESS_ID = "business-1"
AGENT_ID = "agent-1"


def _entries_for(repository: InMemoryAnsweredQuestionRepository) -> list:
    return repository._entries.get((TENANT_ID, BUSINESS_ID), [])


async def test_near_duplicate_question_updates_existing_entry_instead_of_adding_one() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Do you accept Delta Dental insurance?",
        answer="Yes, we accept Delta Dental PPO.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Is Delta Dental accepted here?",
        answer="Yes, we accept Delta Dental PPO and HMO.",
        embedding=[0.99, 0.01, 0.0],
        dedup_similarity_threshold=0.75,
    )

    entries = _entries_for(repository)
    assert len(entries) == 1
    assert entries[0].answered_question.question == "Is Delta Dental accepted here?"
    assert entries[0].answered_question.answer == "Yes, we accept Delta Dental PPO and HMO."


async def test_dissimilar_question_adds_a_new_entry() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="What time do you close on Saturdays?",
        answer="2pm.",
        embedding=[0.0, 1.0, 0.0],
        dedup_similarity_threshold=0.75,
    )

    entries = _entries_for(repository)
    assert len(entries) == 2


async def test_dedup_only_applies_within_the_same_agent() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id="agent-b",
        question="Is Delta Dental accepted here?",
        answer="Yes.",
        embedding=[0.99, 0.01, 0.0],
        dedup_similarity_threshold=0.75,
    )

    entries = _entries_for(repository)
    assert len(entries) == 2


async def test_dedup_refreshes_the_timestamp() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    first_created_at = _entries_for(repository)[0].answered_question.created_at

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Is Delta Dental accepted here?",
        answer="Yes, still.",
        embedding=[0.99, 0.01, 0.0],
        dedup_similarity_threshold=0.75,
    )
    second_created_at = _entries_for(repository)[0].answered_question.created_at

    assert second_created_at >= first_created_at


async def test_list_all_returns_newest_first() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=AGENT_ID,
        question="What time do you close on Saturdays?",
        answer="2pm.",
        embedding=[0.0, 1.0, 0.0],
        dedup_similarity_threshold=0.75,
    )

    answers = await repository.list_all(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id=None,
    )

    assert [answer.question for answer in answers] == [
        "What time do you close on Saturdays?",
        "Do you accept Delta Dental insurance?",
    ]


async def test_list_all_filters_by_agent_when_given() -> None:
    repository = InMemoryAnsweredQuestionRepository()

    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id="agent-a",
        question="Do you accept Delta Dental insurance?",
        answer="Yes.",
        embedding=[1.0, 0.0, 0.0],
        dedup_similarity_threshold=0.75,
    )
    await repository.save(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id="agent-b",
        question="What time do you close on Saturdays?",
        answer="2pm.",
        embedding=[0.0, 1.0, 0.0],
        dedup_similarity_threshold=0.75,
    )

    answers = await repository.list_all(
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        agent_id="agent-a",
    )

    assert len(answers) == 1
    assert answers[0].question == "Do you accept Delta Dental insurance?"
