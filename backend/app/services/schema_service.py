from sqlalchemy import MetaData, text, String, Text
from app.db.database import engine


def get_metadata() -> str:
    metadata = MetaData()
    metadata.reflect(bind=engine)

    schema = ""
    # Filter out LangGraph internal checkpoint tables
    domain_tables = [
        t for t in metadata.sorted_tables 
        if not t.name.startswith("checkpoint")
    ]

    try:
        with engine.connect() as conn:
            for table in domain_tables:
                schema += f"\nTable: {table.name}\n"

                for column in table.columns:
                    col_info = f"  - {column.name} ({column.type})"

                    # For string/varchar/text columns, fetch distinct sample values for schema linking
                    if isinstance(column.type, (String, Text)):
                        try:
                            sample_query = text(
                                f'SELECT DISTINCT "{column.name}" '
                                f'FROM "{table.name}" '
                                f'WHERE "{column.name}" IS NOT NULL '
                                f'LIMIT 6'
                            )
                            rows = conn.execute(sample_query).fetchall()
                            samples = [str(r[0]) for r in rows if r[0] is not None]
                            if samples:
                                formatted_samples = ", ".join(repr(s) for s in samples[:6])
                                col_info += f"  -- sample values: [{formatted_samples}]"
                        except Exception:
                            pass

                    schema += col_info + "\n"
    except Exception as e:
        # Fallback if connection fails during reflection
        for table in domain_tables:
            schema += f"\nTable: {table.name}\n"
            for column in table.columns:
                schema += f"  - {column.name} ({column.type})\n"

    return schema
