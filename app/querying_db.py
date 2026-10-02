from sqlalchemy import text
from app.db.database import engine
from app.state import state


def validate_sql_syntax(graph_state : state):
    sql = graph_state.sql
    
    try: 
        with engine.connect() as conn:
            conn.execute(text(f"EXPLAIN {sql}"))
            
        
        return {
            "sql_valid": True,
            "sql_valid_error": ""
        }
        
    except Exception as e:
        print('\n Sql Error')
        print(e)
        
        return{
            'sql_valid': False,
            'sql_valid_error': str(e)
        }
        
        

def execute_sql(graph_state : state):
    
    sql = graph_state.sql
    
    try: 
        with engine.begin() as conn:
            result = conn.execute(text(sql))
            
            if result.returns_rows:
                rows = result.fetchall()
                db_result = [tuple(row) for row in rows]
            else:
                db_result = [("status", "success", "rows_affected", result.rowcount)]
        
        return {
            'db_result': db_result,
            'sql_execution_error': None
        }
    
    except Exception as e:
        print(f'Error occurred during sql execution. Error: {e}')
        return {
            'db_result': None,
            'sql_execution_error': str(e)
        }

        
        

