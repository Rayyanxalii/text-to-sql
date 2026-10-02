from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.main import QueryRequest, app
from langgraph.types import Command


def test_query_request_accepts_clarification_answer_without_resume_flag():
    payload = {
        "clarification_answer": "Use the sales table for 2024 only.",
        "conversation_id": "thread-1",
    }

    request = QueryRequest(**payload)

    assert request.question is None
    assert request.clarification_answer == "Use the sales table for 2024 only."


def test_resume_uses_clarification_answer_not_original_question(monkeypatch):
    captured = {}

    def fake_get_state(config):
        captured["state_config"] = config
        return SimpleNamespace(tasks=[SimpleNamespace(interrupts=["pending"])])

    def fake_invoke(command_or_state, config=None):
        captured["command"] = command_or_state
        captured["config"] = config
        return {"answer": "ok"}

    import app.main as main_module

    monkeypatch.setattr(
        main_module,
        "graph",
        type(
            "G",
            (),
            {
                "get_state": staticmethod(fake_get_state),
                "invoke": staticmethod(fake_invoke),
            },
        )(),
    )

    request = QueryRequest(
        clarification_answer="Use the sales table for 2024 only.",
        conversation_id="thread-1",
    )

    result = main_module.query_database(request)

    assert result["answer"] == "ok"
    assert isinstance(captured["command"], Command)
    assert captured["command"].resume == "Use the sales table for 2024 only."
    assert captured["config"]["configurable"]["thread_id"] == "thread-1"
    assert captured["state_config"] == captured["config"]


def test_fresh_question_starts_graph_when_no_interrupt_is_pending(monkeypatch):
    captured = {}

    def fake_get_state(config):
        return SimpleNamespace(tasks=[])

    def fake_invoke(command_or_state, config=None):
        captured["input"] = command_or_state
        return {"answer": "ok"}

    import app.main as main_module

    monkeypatch.setattr(
        main_module,
        "graph",
        type(
            "G",
            (),
            {
                "get_state": staticmethod(fake_get_state),
                "invoke": staticmethod(fake_invoke),
            },
        )(),
    )

    result = main_module.query_database(
        QueryRequest(question="What was the total revenue?", conversation_id="thread-1")
    )

    assert result["answer"] == "ok"
    assert captured["input"]["question"] == "What was the total revenue?"


def test_resume_requires_clarification_answer_when_interrupt_is_pending(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(
        main_module,
        "graph",
        type(
            "G",
            (),
            {
                "get_state": staticmethod(
                    lambda config: SimpleNamespace(
                        tasks=[SimpleNamespace(interrupts=["pending"])]
                    )
                ),
            },
        )(),
    )

    with pytest.raises(HTTPException) as error:
        main_module.query_database(
            QueryRequest(question="A new question", conversation_id="thread-1")
        )

    assert error.value.status_code == 422


def test_clarification_answer_is_rejected_when_no_interrupt_is_pending(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(
        main_module,
        "graph",
        type(
            "G",
            (),
            {
                "get_state": staticmethod(lambda config: SimpleNamespace(tasks=[])),
            },
        )(),
    )

    with pytest.raises(HTTPException) as error:
        main_module.query_database(
            QueryRequest(
                clarification_answer="Use 2024",
                conversation_id="thread-1",
            )
        )

    assert error.value.status_code == 409


def test_interrupt_result_is_returned_as_clarification_request(monkeypatch):
    import app.main as main_module

    def fake_invoke(command_or_state, config=None):
        return {
            "__interrupt__": [
                SimpleNamespace(value="Which year should I use?")
            ],
            "messages": [],
        }

    monkeypatch.setattr(
        main_module,
        "graph",
        type(
            "G",
            (),
            {
                "get_state": staticmethod(lambda config: SimpleNamespace(tasks=[])),
                "invoke": staticmethod(fake_invoke),
            },
        )(),
    )

    result = main_module.query_database(
        QueryRequest(question="Show revenue", conversation_id="thread-1")
    )

    assert result["requires_clarification"] is True
    assert result["clarification_question"] == "Which year should I use?"
