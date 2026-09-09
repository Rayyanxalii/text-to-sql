from sqlalchemy import MetaData
from app.db.database import engine


metadata = MetaData()

# Read the existing database schema
metadata.reflect(bind=engine)

meta_data = []



# getting info about the database tables

def get_metadata():

    metadata = MetaData()
    metadata.reflect(bind=engine)

    schema = ""

    for table in metadata.sorted_tables:

        schema += f"\nTable: {table.name}\n"

        for column in table.columns:
            schema += f"  - {column.name} ({column.type})\n"

    return schema


