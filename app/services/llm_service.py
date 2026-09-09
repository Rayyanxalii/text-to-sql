from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.chat_models import ChatOllama

from dotenv import load_dotenv
load_dotenv()



llm = ChatOllama(
    model="qwen2.5-coder:7b",
    temperature=0
)


llm_eval = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
    )