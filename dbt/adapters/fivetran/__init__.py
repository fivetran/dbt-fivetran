
from dbt.adapters.fivetran.adapter import FivetranAdapter
from dbt.adapters.fivetran.adapter import FivetranAdapter
from dbt.adapters.fivetran.credentials import FivetranCredentials
from dbt.adapters.base import AdapterPlugin
from dbt.include import fivetran

Plugin = AdapterPlugin(
    adapter=FivetranAdapter,  # type: ignore
    credentials=FivetranCredentials,
    include_path=fivetran.PACKAGE_PATH
)
