"""History manager for GUI application.

Manages analysis history with SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoryManager:
    """Manages analysis history records."""

    def __init__(self, db_path: str | None = None):
        """Initialize history manager.

        Args:
            db_path: Path to SQLite database file.
                    Defaults to ~/.xhs_agent/history.db
        """
        if db_path is None:
            config_dir = Path.home() / ".xhs_agent"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(config_dir / "history.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT NOT NULL,
                result TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                metadata TEXT,
                updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at DESC)
        """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_query ON history(query)
        """
        )
        self.conn.commit()

        # Lightweight migration for older databases (add columns if missing).
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(history)").fetchall()}
        if "status" not in cols:
            self.conn.execute("ALTER TABLE history ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
        if "updated_at" not in cols:
            self.conn.execute("ALTER TABLE history ADD COLUMN updated_at TIMESTAMP")
        self.conn.commit()

    def save_record(
        self,
        query: str,
        result: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        *,
        status: str = "completed",
    ) -> int:
        """Save analysis record.

        Args:
            query: User query
            result: Analysis result dictionary
            metadata: Optional metadata (options, timestamps, etc.)

        Returns:
            Record ID
        """
        mode = result.get("mode", "hot")
        result_json = json.dumps(result, ensure_ascii=False)
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

        cursor = self.conn.execute(
            """
            INSERT INTO history (query, mode, result, status, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (query, mode, result_json, status, metadata_json, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

        return cursor.lastrowid

    def update_record(
        self,
        record_id: int,
        *,
        result: dict[str, Any] | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update an existing record (result/status/metadata)."""

        fields: list[str] = []
        params: list[Any] = []

        if result is not None:
            fields.append("result = ?")
            params.append(json.dumps(result, ensure_ascii=False))
            # Keep mode in sync if present.
            mode = result.get("mode") if isinstance(result, dict) else None
            if isinstance(mode, str) and mode:
                fields.append("mode = ?")
                params.append(mode)

        if status is not None:
            fields.append("status = ?")
            params.append(status)

        if metadata is not None:
            fields.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))

        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat(timespec="seconds"))

        if not fields:
            return False

        params.append(record_id)
        sql = f"UPDATE history SET {', '.join(fields)} WHERE id = ?"
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cur.rowcount > 0

    def get_records(
        self, limit: int = 50, offset: int = 0, mode: str | None = None
    ) -> list[dict[str, Any]]:
        """Get history records.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            mode: Optional filter by mode ('hot' or 'radar')

        Returns:
            List of record dictionaries
        """
        if mode:
            cursor = self.conn.execute(
                """
                SELECT id, query, mode, status, created_at
                FROM history
                WHERE mode = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (mode, limit, offset),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT id, query, mode, status, created_at
                FROM history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

        records = []
        for row in cursor.fetchall():
            records.append(
                {
                    "id": row["id"],
                    "query": row["query"],
                    "mode": row["mode"],
                    "status": row["status"] if "status" in row.keys() else "completed",
                    "created_at": row["created_at"],
                }
            )

        return records

    def get_record(self, record_id: int) -> dict[str, Any] | None:
        """Get single record by ID.

        Args:
            record_id: Record ID

        Returns:
            Record dictionary or None if not found
        """
        cursor = self.conn.execute(
            """
            SELECT id, query, mode, status, result, metadata, updated_at, created_at
            FROM history
            WHERE id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "query": row["query"],
            "mode": row["mode"],
            "status": row["status"] if "status" in row.keys() else "completed",
            "result": json.loads(row["result"]),
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else None,
            "created_at": row["created_at"],
        }

    def search_records(self, keyword: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search records by keyword.

        Args:
            keyword: Search keyword
            limit: Maximum number of records to return

        Returns:
            List of matching record dictionaries
        """
        cursor = self.conn.execute(
            """
            SELECT id, query, mode, status, created_at
            FROM history
            WHERE query LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (f"%{keyword}%", limit),
        )

        records = []
        for row in cursor.fetchall():
            records.append(
                {
                    "id": row["id"],
                    "query": row["query"],
                    "mode": row["mode"],
                    "status": row["status"] if "status" in row.keys() else "completed",
                    "created_at": row["created_at"],
                }
            )

        return records

    def delete_record(self, record_id: int) -> bool:
        """Delete record by ID.

        Args:
            record_id: Record ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.execute(
            """
            DELETE FROM history WHERE id = ?
        """,
            (record_id,),
        )
        self.conn.commit()

        return cursor.rowcount > 0

    def delete_all_records(self) -> int:
        """Delete all records.

        Returns:
            Number of records deleted
        """
        cursor = self.conn.execute("DELETE FROM history")
        self.conn.commit()

        return cursor.rowcount

    def get_statistics(self) -> dict[str, Any]:
        """Get history statistics.

        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN mode = 'hot' THEN 1 END) as hot_count,
                COUNT(CASE WHEN mode = 'radar' THEN 1 END) as radar_count,
                MIN(created_at) as first_record,
                MAX(created_at) as last_record
            FROM history
        """
        )

        row = cursor.fetchone()

        return {
            "total": row["total"],
            "hot_count": row["hot_count"],
            "radar_count": row["radar_count"],
            "first_record": row["first_record"],
            "last_record": row["last_record"],
        }

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
