from sqlalchemy import text
from app.db.database import engine
from app.state import state
from psycopg.errors import InsufficientPrivilege


# try:
#     from psycopg.errors import InsufficientPrivilege
# except ImportError:
#     try:
#         from psycopg2.errors import InsufficientPrivilege
#     except ImportError:
#         InsufficientPrivilege = None


def _check_permission_denied(error: Exception) -> bool:
    if InsufficientPrivilege is not None:
        if isinstance(getattr(error, "orig", None), InsufficientPrivilege) or isinstance(error, InsufficientPrivilege):
            return True
    err_str = str(error).lower()
    return "permission denied" in err_str or "insufficientprivilege" in err_str




def validate_sql_syntax(graph_state : state):
    print("\n========== ENTERED VALIDATE SQL SYNTAX ==========")
    sql = graph_state.sql
    
    try: 
        with engine.connect() as conn:
            conn.execute(text(f"EXPLAIN {sql}"))
            
        return {
            "sql_valid": True,
            "sql_valid_error": "",
            'permission_denied': False
        }
        
    except Exception as e:
        print('\n Sql Error')
        print(e)
        
        permission_denied = _check_permission_denied(e)
        
        return {
            'sql_valid': False,
            'sql_valid_error': str(e),
            'permission_denied': permission_denied
        }
        
        

def execute_sql(graph_state : state):
    print("\n========== ENTERED EXECUTE SQL ==========")
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
            'sql_execution_error': str(e),
            'permission_denied': _check_permission_denied(e)
        }

        
        

