from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.chat_models import ChatOllama
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)


from dotenv import load_dotenv
load_dotenv()



# llm = ChatOllama(
#     model="qwen2.5-coder:7b",
#     temperature=0
# )

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0
#     )


# llm_eval = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0
#     )


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)


llm_eval = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)
