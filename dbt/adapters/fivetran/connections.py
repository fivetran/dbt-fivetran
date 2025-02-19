from typing import Any

from dbt.adapters.contracts.connection import Connection
from dbt.adapters.duckdb import DuckDBConnectionManager

from dbt.adapters.events.logging import AdapterLogger
from dbt_common.exceptions import DbtInternalError

logger = AdapterLogger("Fivetran")


class FivetranConnectionManager(DuckDBConnectionManager):
    TYPE = "fivetran"

    def open(cls, connection: Connection) -> Connection:
        super().open(connection)
        connection.handle.cursor().execute("SET TimeZone = 'UTC'; SET checkpoint_threshold='4GB'")

    def execute_for_cursor(self, sql: str) -> Any:
        sql = self._add_query_comment(sql)
        _, cursor = self.add_query(sql, True)
        return cursor
