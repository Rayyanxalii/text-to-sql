import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("READONLY_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("READONLY_DATABASE_URL is not configured")


engine = create_engine(DATABASE_URL)
