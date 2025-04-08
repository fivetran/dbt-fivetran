
import os
import pyarrow as pa
import pyiceberg
from dbt.adapters.contracts.relation import RelationType

from dbt.adapters.duckdb import DuckDBAdapter
from dbt.adapters.fivetran.connections import FivetranConnectionManager
from dbt.adapters.base import BaseRelation
from dbt.adapters.base.meta import available
from multiprocessing.context import SpawnContext

from io import UnsupportedOperation
from typing import List

from pyiceberg.catalog import load_catalog


import logging
logger = logging.getLogger(__name__)

# logging.basicConfig(level=logging.DEBUG)
# boto3.set_stream_logger('boto3', level=logging.DEBUG)
# boto3.set_stream_logger('botocore', level=logging.DEBUG)


# DuckDB to Iceberg type mappings
TYPE_MAPPINGS = {
    'bool': pa.bool_(),
    'boolean': pa.bool_(),
    'tinyint': pa.int8(),
    'smallint': pa.int16(),
    'integer': pa.int32(),
    'bigint': pa.int64(),
    'number': pa.int64(),  # Assuming 'number' corresponds to int64
    'utinyint': pa.uint8(),
    'usmallint': pa.uint16(),
    'uinteger': pa.uint32(),
    'ubigint': pa.uint64(),
    'float': pa.float32(),
    'double': pa.float64(),
    'varchar': pa.string(),
    'string': pa.string(),
    'text': pa.string(),
    'char': pa.string(),
    'date': pa.date32(),
    'time': pa.time64('us'),
    'datetime': pa.timestamp('us'),
    'timestamp': pa.timestamp('us'),
    'json': pa.string(),
    'timestamp with time zone': pa.timestamp('us', tz='UTC'),
    'blob': pa.binary(),
    'hugeint': pa.decimal128(38, 0),  # Assuming 38 digits precision for hugeint
    'uuid': pa.string()  # PyArrow doesn't have a native UUID type
}

DEBUG=False
DEFAULT_BATCH_SIZE = 250_000
TBL_NAME_CONF_RESLV = "_ft2349287"

def dbg_print(msg: str):
    if DEBUG:
        print(msg)

class FivetranAdapter(DuckDBAdapter):
    adapter_type = "fivetran"

    Relation = BaseRelation
    ConnectionManager = FivetranConnectionManager
    connections: FivetranConnectionManager

    def __init__(self, config, mp_context: SpawnContext) -> None:
        super().__init__(config, mp_context)

        global DEBUG        
        try:
            from dbt.flags import get_flags
            flags = get_flags()
            if hasattr(flags, 'VARS'):
                DEBUG = flags.VARS.get('ft_adapter_debug', False)
            else:
                DEBUG = False
        except (ImportError, AttributeError):
            DEBUG = False

        self.database = config.credentials.database
        if getattr(config, 'clean_targets', None):
            if 'target' in config.clean_targets:
                db_folder = os.path.join(os.getcwd(), 'target')
            else:
                db_folder = os.getcwd()
        else:
            db_folder = None

        if db_folder:
            config.credentials.path = os.path.join(db_folder, f"{self.database}.local.db")

        catalog_uri = config.credentials.polaris_uri[:-1] if config.credentials.polaris_uri.endswith("/") \
                                                          else config.credentials.polaris_uri
        self.catalog = load_catalog("polaris_rest",
            **{
                "uri": catalog_uri,
                "credential": config.credentials.polaris_credentials,
                "scope": config.credentials.polaris_scope,
                "warehouse": config.credentials.polaris_catalog,
                "oauth2-server-uri": f"{catalog_uri}/v1/oauth/tokens"
            }
        )
        # This will work as long as the datalake is not empty, and it shouldn't be if we are
        # going to be running dbt models on it! If this assumption turns out to be false at
        # some point, we can probably use catalog.properties.token to fetch /v1/config and
        # read the s3 root path from there (this isn't available as part of pyiceberg.catalog): 
        # {"defaults":{"default-base-location":"s3://emrah-s3-data-lake"},"overrides":{"prefix":"my_catalog"}}
        self.catalog_base_loc = os.path.dirname(self.catalog.load_namespace_properties(
                                        self.catalog.list_namespaces()[0])['location'])

        super().__init__(config, mp_context)

    def create_schema(self, relation: BaseRelation) -> None:
        dbg_print(f"CREATE SCHEMA: {relation} | {relation.schema}")

        self.catalog.create_namespace_if_not_exists(relation.schema)
        super().create_schema(relation)

    def list_schemas(self, database):
        database = database.replace('"', '')
        dbg_print(f"LIST SCHEMAS: {database}")
        return super().list_schemas(database)

    def _get_local_views(self, schema_relation: BaseRelation) -> List[BaseRelation]:
        kwargs = {"schema_relation": schema_relation}
        results = self.execute_macro("list_relations_without_caching", kwargs=kwargs)
        relations = []
        quote_policy = {"database": True, "schema": True, "identifier": True}
        for _database, name, _schema, _type in results:
            try:
                _type = self.Relation.get_relation_type(_type)
            except ValueError:
                _type = self.Relation.External
            relations.append(
                BaseRelation.create(
                    database=_database,
                    schema=_schema,
                    identifier=name,
                    quote_policy=quote_policy,
                    type=_type,
                )
            )
        return relations

    def list_relations_without_caching(self, relation: BaseRelation) -> List[BaseRelation]:
        dbg_print(f"LIST RELATIONS: {relation.database} {relation.schema} {relation.identifier}")

        quote_policy = {"database": True, "schema": True, "identifier": True}
        # Get views from local db if any
        relations = self._get_local_views(relation)
        # Get tables from polaris catalog
        try:
            for table in self.catalog.list_tables(relation.schema):
                relation = BaseRelation.create(
                    database=relation.database,
                    schema=table[0],
                    identifier=table[1],
                    quote_policy=quote_policy,
                    type=RelationType.Table)

                if relation not in relations:
                    relations.append(relation)
        except:
            pass

        return relations

    @staticmethod
    def _relation_to_identifier(relation: BaseRelation) -> str:
        return f"{relation.schema}.{relation.identifier}"

    @available
    def create_table_as(self, temporary: bool, relation: BaseRelation, sql: str):
        dbg_print(f"CREATE TABLE AS: {temporary} {relation.schema} {relation.identifier}")

        if temporary:
            raise UnsupportedOperation("Temporary tables are not supported")

        connection = self.acquire_connection()
        self.connections.open(connection)
        cursor = self.connections.execute_for_cursor(f"describe select * from ({sql})")
        column_names = []
        schema_cols = []
        for desc in cursor.fetchall():
            col_name = desc[0]
            col_type = desc[1]
            column_names.append(col_name)
            schema_cols.append((col_name, TYPE_MAPPINGS[col_type.lower()]))
        schema = pa.schema(schema_cols)
        dbg_print(f" .... schema: {schema}")

        table_identifier = self._relation_to_identifier(relation)
        dbg_print(f" .... table_identifier: {table_identifier}")
        if self.catalog.table_exists(table_identifier):
            dbg_print(f" .... table already exists, dropping: {table_identifier}")
            self._drop_table(relation, True)

        location = f"{self.catalog_base_loc}/{relation.schema}/{relation.identifier}"
        create_table_args = {
                "identifier": table_identifier,
                "schema": schema,
                "location": location,
                "properties": {
                    "write.parquet.compression-codec": "snappy"
                }}

        try:
            table = self.catalog.create_table(**create_table_args)
        except Exception as e:
            if "because it conflicts with existing table or namespace at location" in str(e):
                dbg_print(" ... Table location name conflict detected")
                create_table_args['location'] = f"{self.catalog_base_loc}/{relation.schema}/{relation.identifier}_{TBL_NAME_CONF_RESLV}"
                table = self.catalog.create_table(**create_table_args)
            else:
                raise e

        dbg_print(f"  .... table created: {table} {table_identifier} @ {location}")

        cursor = self.connections.execute_for_cursor(sql)
        batch_reader = cursor.fetch_record_batch(rows_per_batch=DEFAULT_BATCH_SIZE)
        while True:
            try:
                batch = batch_reader.read_next_batch()
            except StopIteration:
                break

            pa_table = pa.Table.from_batches([batch], schema=schema)
            table.append(pa_table)

        table.refresh()
        dbg_print(f"  .... data appended to table")

        # Create a view for the table so it is easy to query from duckdb
        self._create_db_view_from_iceberg(table_identifier, table)

    def _get_iceberg_table(self, schema: str, table: str) -> pyiceberg.table.Table:
        dbg_print(f"__GET_ICEBERG_TABLE {schema} {table}")
        ent = f"{schema}.{table}"
        if self.catalog.table_exists(ent):
            table = self.catalog.load_table(ent)
            return table
        return None

    def _create_db_schema(self, schema):
        try:
            self.connections.execute(f'CREATE SCHEMA "{schema}"')
            self.commit_if_has_connection()
            dbg_print(f" created db schema: {schema}")
        except Exception as e:
            if "already exists" not in str(e):
                raise e

    def _create_db_view_from_iceberg(self, identifier: str, table: pyiceberg.table.Table):
        dbg_print(f"__CREATE_DB_VIEW_FROM_ICEBERG {identifier} {table.metadata_location}")

        self._drop_db_view_if_exists(identifier)

        location = table.metadata_location

        iii = location.index("metadata")
        scope = location[:iii]
        secret_name = identifier.replace('.', '_')
        # TODO?: REGION '{self.secrets.secret_kwargs['region']}'
        secret_sql = f'''CREATE OR REPLACE PERSISTENT SECRET "{secret_name}" (
            TYPE S3,
            KEY_ID '{table.io.properties["s3.access-key-id"]}',
            SECRET '{table.io.properties["s3.secret-access-key"]}',
            SESSION_TOKEN '{table.io.properties["s3.session-token"]}',
            SCOPE '{scope}'
        )'''
        self.connections.execute(secret_sql)

        schema, table = identifier.split('.')
        sql = f'CREATE VIEW "{self.database}"."{schema}"."{table}" AS (SELECT * FROM iceberg_scan("{location}"))'
        dbg_print(f" .... sql: {sql}")
        self.connections.execute(sql)
        self.commit_if_has_connection()
        dbg_print(f" created db view: {identifier} {location}")

    def _rename_db_view(self, from_view: str, to_view: str):
        from_ = from_view.split('.')
        to_ = to_view.split('.')
        sql = f'ALTER VIEW "{self.database}"."{from_[0]}"."{from_[1]}" RENAME TO "{to_[1]}"'
        dbg_print(f" .... sql: {sql}")
        self.connections.execute(sql)
        self.commit_if_has_connection()
        dbg_print(f" renamed db view: {from_} -> {to_}")

    def _drop_db_view_if_exists(self, identifier: str):
        schema, table = identifier.split('.')
        try:
            self.connections.execute(f'DROP VIEW "{self.database}"."{schema}"."{table}"')
            self.commit_if_has_connection()
            dbg_print(f" dropped db schema: {schema}")
        except Exception as e:
            if f"View with name {table} does not exist" not in str(e):
                raise e

    @available
    def handle_source(self, relation: BaseRelation, fetcher=_get_iceberg_table) -> BaseRelation:
        schema = relation.schema
        table = relation.table
        dbg_print(f"HANDLE SOURCE: {schema} {table}")
        iceberg_table = fetcher(self, schema, table)
        if iceberg_table:
            location = iceberg_table.metadata_location
            dbg_print(f"  ... location :{location}")
            # we need to wrap iceberg tables in views so we can use them in complex queries
            connection = self.acquire_connection()
            self.connections.open(connection)
            self._create_db_schema(schema)
            identifier = f"{schema}.{table}"
            self._drop_db_view_if_exists(identifier)
            self._create_db_view_from_iceberg(identifier, iceberg_table)

        return BaseRelation.create(database=relation.database, schema=schema, identifier=table)

    def drop_relation(self, relation):
        dbg_print(f" DROP RELATION: {relation} | {relation.type}")

        if relation.type == "view":
            super().drop_relation(relation)
        else:
            self._drop_table(relation)

    # Don't call self.catalog.drop_table() directly, call this method so we cleanup the folder too
    def _drop_table(self, relation: BaseRelation, table_exists: bool = False):
        dbg_print(f" DROP TABLE: {relation}")

        identifier = self._relation_to_identifier(relation)
        if table_exists or self.catalog.table_exists(identifier):
            self.catalog.purge_table(identifier)

        self._drop_db_view_if_exists(identifier)

    def rename_relation(self, from_relation: BaseRelation, to_relation: BaseRelation):
        dbg_print(f">> RENAME_RELATION: {from_relation} {from_relation.type} {to_relation}")
        dbg_print(f"    -- {from_relation.schema}.{from_relation.identifier} -> {to_relation.schema}.{to_relation.identifier}")

        if from_relation.type == "view":
            dbg_print(f"      .... rename view")
            super().rename_relation(from_relation, to_relation)
        else:
            dbg_print(f"      .... rename table")
            from_table = self._relation_to_identifier(from_relation)
            if self.catalog.table_exists(from_table):
                to_table = self._relation_to_identifier(to_relation)
                dbg_print(f"          .... to_table: {to_table}")
                if self.catalog.table_exists(to_table):
                    dbg_print(f"  TO TABLE {to_table} exists, dropping")
                    self._drop_table(to_relation, True)
                self.catalog.rename_table(from_table, to_table)
                self._drop_db_view_if_exists(to_table)
                try:
                    self._rename_db_view(from_table, to_table)
                except Exception as e:
                    # Local "view cache" for remote table must have gotten out of sync, 
                    # we don't have a view for this table
                    pass
