import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                headers TEXT NOT NULL,
                query_params TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                content_type TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'received'
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_created_at ON webhook_events(created_at DESC)"
        )


def save_event(
    db_path: str,
    method: str,
    path: str,
    headers: Dict[str, str],
    query_params: Dict[str, Any],
    client_ip: str,
    content_type: str,
    body: str,
) -> Dict[str, Any]:
    event_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO webhook_events (
                id, created_at, method, path, headers, query_params, client_ip, content_type, body, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                created_at,
                method.upper(),
                path,
                json.dumps(headers),
                json.dumps(query_params),
                client_ip,
                content_type,
                body,
                "received",
            ),
        )

    return {
        "id": event_id,
        "created_at": created_at,
        "method": method.upper(),
        "path": path,
        "headers": headers,
        "query_params": query_params,
        "client_ip": client_ip,
        "content_type": content_type,
        "body": body,
        "status": "received",
    }


def list_events(db_path: str, limit: int = 100, search: Optional[str] = None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM webhook_events"
    params: List[Any] = []

    if search:
        query += " WHERE body LIKE ? OR path LIKE ? OR headers LIKE ?"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "method": row["method"],
                "path": row["path"],
                "headers": json.loads(row["headers"]),
                "query_params": json.loads(row["query_params"]),
                "client_ip": row["client_ip"],
                "content_type": row["content_type"],
                "body": row["body"],
                "status": row["status"],
            }
        )
    return result


def get_event(db_path: str, event_id: str) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM webhook_events WHERE id = ?", (event_id,)).fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "method": row["method"],
        "path": row["path"],
        "headers": json.loads(row["headers"]),
        "query_params": json.loads(row["query_params"]),
        "client_ip": row["client_ip"],
        "content_type": row["content_type"],
        "body": row["body"],
        "status": row["status"],
    }


def delete_event(db_path: str, event_id: str) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM webhook_events WHERE id = ?", (event_id,))
        return cur.rowcount > 0


def clear_events(db_path: str) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM webhook_events")
        return cur.rowcount
