from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import graph_view as graph
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command


# schema = get_metadata()


app = FastAPI(
    title="Text-to-SQL API",
    description="Natural language to SQL system",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str
    clarification_answer: str | None = None
    conversation_id: str
    resume: bool = False



@app.get("/")
def root():
    return {
        "message": "Text-to-SQL API is running"
    }
    

@app.post("/query")
def query_database(request: QueryRequest):
    config = {
        'configurable': {
            'thread_id': request.conversation_id
        }
    }

    if request.resume:
        resumed_value = request.clarification_answer or request.question
        result = graph.invoke(
            Command(resume=resumed_value),
            config=config,
        )
    else:
        result = graph.invoke(
            {
                "question": request.question,
                'messages': [HumanMessage(content=request.question)],
            },
            config=config,
        )

    print(f'Result: {result}')

    if 'answer' in result and result.get('answer'):
        return {
            'messages': [AIMessage(content=result['answer'])],
            'answer': result['answer'],
        }

    if result.get('clarification_question'):
        return {
            'messages': result.get('messages', []),
            'clarification_question': result['clarification_question'],
            'answer': '',
            'requires_clarification': True,
        }

    return {
        'messages': result.get('messages', []),
        'answer': '',
        'requires_clarification': False,
    }

