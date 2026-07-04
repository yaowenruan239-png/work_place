from __future__ import annotations

from typing import Any

import mysql.connector
from mysql.connector import Error

from python_client.config import MYSQL_CONFIG


def get_conn():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as exc:
        raise RuntimeError(f"Failed to connect to MySQL: {exc}") from exc


def execute(sql: str, params: tuple[Any, ...] | dict[str, Any] | None = None) -> int:
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return int(cursor.lastrowid or 0)
    except Error as exc:
        if conn is not None:
            conn.rollback()
        raise RuntimeError(f"Failed to execute SQL: {exc}") from exc
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


def fetch_all(sql: str, params: tuple[Any, ...] | dict[str, Any] | None = None) -> list[dict[str, Any]]:
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Error as exc:
        raise RuntimeError(f"Failed to fetch SQL results: {exc}") from exc
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()
