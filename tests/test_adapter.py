
import pytest
from unittest.mock import Mock
from dbt.adapters.fivetran import FivetranAdapter


## How to run:
## $ pytest --log-cli-level=DEBUG


class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


def mock_fetcher(cls, schema: str, table: str):
    return f"{schema}.{table}"

@pytest.fixture
def adapter():
    config = Mock()
    config.credentials.polaris_catalog = "database"
    mp_context = Mock()
    return FivetranAdapter(config, mp_context)


def test_handle_source(adapter):
    transformed_sql = adapter.handle_source("metrics", "data_points", mock_fetcher)
    assert transformed_sql == "select * from iceberg_scan('metrics.data_points')"
