from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import graph_view as graph
from app.services.schema_service import get_metadata
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command





schema = get_metadata()


app = FastAPI(
    title="Text-to-SQL API",
    description="Natural language to SQL system",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str
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
           'configurable':{
               'thread_id': request.conversation_id
           }
       }       
       
       if request.resume:
           
           result = graph.invoke(
               Command(resume = request.question),
               config = config
           )
        
       else:
           
            result = graph.invoke({
               "question": request.question,
               'messages': [HumanMessage(content = request.question)]   
               },
                config = config            
                           )
    
       print(f'Result: {result}')
    
    
       return {
        'messages': [AIMessage(content = result['answer'])],
        'answer' : result['answer']
    }

