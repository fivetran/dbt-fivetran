from dbt.adapters.duckdb.credentials import DuckDBCredentials, Secret
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class FivetranCredentials(DuckDBCredentials):
    polaris_uri: str = ""
    polaris_credentials: str = ""
    polaris_scope: str = ""
    polaris_catalog: str = ""

    @property
    def type(self):
        return "fivetran"

    @property
    def unique_field(self):
        return "fivetran"

    def _connection_keys(self):
        return super()._connection_keys() + ("polaris_uri", "polaris_credentials", "polaris_scope", "polaris_catalog")

    @classmethod
    def __pre_deserialize__(cls, data: Dict[Any, Any]) -> Dict[Any, Any]:
        data = cls.translate_aliases(data)

        if "path" in data:
            raise ValueError("Remove `path` from profiles.yml")

        if "database" not in data:
            raise ValueError("`database` parameter missing in profiles.yml")

        return data