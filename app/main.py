from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import graph_view as graph
from app.services.schema_service import get_metadata



schema = get_metadata()


app = FastAPI(
    title="Text-to-SQL API",
    description="Natural language to SQL system",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def root():
    return {
        "message": "Text-to-SQL API is running"
    }
    

@app.post("/query")
def query_database(request: QueryRequest):
    
    question = request.question

    result = graph.invoke({
        "question": question
    })

    return result

