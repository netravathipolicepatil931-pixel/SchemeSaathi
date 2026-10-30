
import json
from typing import Any

from supabase import Client, create_client

from backend.config import settings
from backend.database import get_db_connection


class SQLiteExecuteResult:
    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []


class SQLiteTableQuery:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_columns: str | list[str] | None = "*"
        self.filters: list[tuple[str, Any]] = []
        self.order_by: tuple[str, str] | None = None
        self.limit_value: int | None = None
        self.delete_mode = False
        self.upsert_payload: dict[str, Any] | None = None
        self.on_conflict: str | None = None

    def select(self, *columns: str):
        if not columns:
            self.select_columns = "*"
        elif len(columns) == 1 and isinstance(columns[0], str) and "," in columns[0]:
            self.select_columns = columns[0]
        else:
            self.select_columns = [column for column in columns if column]
        return self

    def eq(self, column: str, value: Any):
        self.filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False):
        self.order_by = (column, "DESC" if desc else "ASC")
        return self

    def limit(self, limit: int):
        self.limit_value = int(limit)
        return self

    def delete(self):
        self.delete_mode = True
        return self

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None):
        self.upsert_payload = payload
        self.on_conflict = on_conflict
        return self

    def _coerce_value(self, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("[", "{")):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
        return value

    def execute(self) -> SQLiteExecuteResult:
        conn = get_db_connection()
        try:
            if self.upsert_payload is not None:
                payload = self.upsert_payload
                columns = list(payload.keys())
                placeholders = ", ".join("?" for _ in columns)
                columns_sql = ", ".join(f'"{column}"' for column in columns)
                if self.on_conflict:
                    conflict_columns = [part.strip() for part in self.on_conflict.split(",") if part.strip()]
                    conflict_sql = ", ".join(f'"{column}"' for column in conflict_columns)
                    update_sql = ", ".join(f'"{column}" = excluded."{column}"' for column in columns)
                    sql = (
                        f'INSERT INTO "{self.table_name}" ({columns_sql}) VALUES ({placeholders}) '
                        f'ON CONFLICT({conflict_sql}) DO UPDATE SET {update_sql}'
                    )
                else:
                    sql = f'INSERT OR REPLACE INTO "{self.table_name}" ({columns_sql}) VALUES ({placeholders})'
                values = []
                for column in columns:
                    value = payload[column]
                    if isinstance(value, (list, dict, tuple)):
                        value = json.dumps(value, ensure_ascii=False)
                    values.append(value)
                conn.execute(sql, values)
                conn.commit()
                return SQLiteExecuteResult([])

            sql, params = self._build_select_sql_and_params()
            rows = conn.execute(sql, params).fetchall()
            if self.delete_mode:
                deleted = [dict(row) for row in rows]
                delete_sql, delete_params = self._build_delete_sql_and_params()
                conn.execute(delete_sql, delete_params)
                conn.commit()
                return SQLiteExecuteResult(deleted)

            data = []
            for row in rows:
                item = {key: self._coerce_value(value) for key, value in dict(row).items()}
                data.append(item)
            return SQLiteExecuteResult(data)
        finally:
            conn.close()

    def _build_select_sql_and_params(self) -> tuple[str, list[Any]]:
        if self.select_columns == "*":
            selected = "*"
        elif isinstance(self.select_columns, str):
            selected = self.select_columns
        else:
            selected = ", ".join(f'"{column}"' for column in self.select_columns)

        sql = f'SELECT {selected} FROM "{self.table_name}"'
        params: list[Any] = []
        if self.filters:
            sql += " WHERE " + " AND ".join(f'"{column}" = ?' for column, _ in self.filters)
            params = [value for _, value in self.filters]
        if self.order_by:
            column, direction = self.order_by
            sql += f' ORDER BY "{column}" {direction}'
        if self.limit_value is not None:
            sql += " LIMIT ?"
            params.append(int(self.limit_value))
        return sql, params

    def _build_delete_sql_and_params(self) -> tuple[str, list[Any]]:
        sql = f'DELETE FROM "{self.table_name}"'
        params: list[Any] = []
        if self.filters:
            sql += " WHERE " + " AND ".join(f'"{column}" = ?' for column, _ in self.filters)
            params = [value for _, value in self.filters]
        return sql, params


class SQLiteClient:
    def table(self, table_name: str) -> SQLiteTableQuery:
        return SQLiteTableQuery(table_name)


def get_supabase_client() -> Client:
    """Client for publicly readable government schemes."""

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_KEY is missing from .env"
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_key
    )


def get_supabase_admin_client() -> Client:
    """Privileged client for trusted backend operations only."""

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_SECRET_KEY is missing from .env"
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key
    )


class SupabaseClientProxy:
    def __init__(self, factory):
        self._factory = factory
        self._client: Client | SQLiteClient | None = None

    def __getattr__(self, name: str) -> Any:
        if self._client is None:
            try:
                self._client = self._factory()
            except ValueError:
                self._client = SQLiteClient()
        return getattr(self._client, name)


supabase = SupabaseClientProxy(get_supabase_client)
supabase_admin = SupabaseClientProxy(get_supabase_admin_client)
