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
            "error": ""
        }
        
    except Exception as e:
        print('\n Sql Error')
        print(e)
        
        return{
            'sql_valid': False,
            'error': str(e)
        }
        
        

def execute_sql(graph_state : state):
    
    sql = graph_state.sql
    
    try: 
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            rows = result.fetchall()
        
        return {
            'db_result' : rows,
            'sql_execution_error': None
        }
    
    except Exception as e:
        print('Error occured during sql execution. Error: {e}')
        return {
                    'db_result' : None,
                    'sql_execution_error' : str(e)
                }
        
        

