import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent.parent / "database" / "troubleshooting.db")

SEARCH_COLUMNS = [
    "FAILURE_MODE",
    "SYMPTOMS",
    "PROBABLE_CAUSE",
    "ROOT_CAUSE",
    "CONNECTOR",
    "WIRE"
]

def search_cases(query: str, limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #split into keywords
    keywords = query.lower().split()

    #build dynamic WHERE clause
    where_clauses = []
    params = []

    for kw in keywords:
        kw_like = f"%{kw}%"
        
        sub_clauses = []
        for col in SEARCH_COLUMNS:
            sub_clauses.append(f"LOWER({col}) LIKE ?")
            params.append(kw_like)

        where_clauses.append("(" + " OR ".join(sub_clauses) + ")")

    final_query = f"""
    SELECT *
    FROM troubleshooting_cases
    WHERE {" AND ".join(where_clauses)}
    LIMIT ?
    """

    params.append(limit)

    cursor.execute(final_query, params)
    results = cursor.fetchall()

    conn.close()
    return results

