from app.main import QueryRequest, app
from langgraph.types import Command


def test_query_request_accepts_clarification_answer():
    payload = {
        "question": "What was the total revenue?",
        "clarification_answer": "Use the sales table for 2024 only.",
        "conversation_id": "thread-1",
        "resume": True,
    }

    request = QueryRequest(**payload)

    assert request.question == "What was the total revenue?"
    assert request.clarification_answer == "Use the sales table for 2024 only."
    assert request.resume is True


def test_resume_uses_clarification_answer_not_original_question(monkeypatch):
    captured = {}

    def fake_invoke(command_or_state, config=None):
        captured["command"] = command_or_state
        captured["config"] = config
        return {"answer": "ok"}

    import app.main as main_module

    monkeypatch.setattr(main_module, "graph", type("G", (), {"invoke": staticmethod(fake_invoke)})())

    request = QueryRequest(
        question="What was the total revenue?",
        clarification_answer="Use the sales table for 2024 only.",
        conversation_id="thread-1",
        resume=True,
    )

    result = main_module.query_database(request)

    assert result["answer"] == "ok"
    assert isinstance(captured["command"], Command)
    assert captured["command"].resume == "Use the sales table for 2024 only."
    assert captured["config"]["configurable"]["thread_id"] == "thread-1"
