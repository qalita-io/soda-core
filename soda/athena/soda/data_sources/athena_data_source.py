from __future__ import annotations

import datetime
import logging

import pyathena
from soda.common.aws_credentials import AwsCredentials
from soda.common.exceptions import DataSourceConnectionError
from soda.common.logs import Logs
from soda.execution.data_source import DataSource
from soda.execution.data_type import DataType

logger = logging.getLogger(__name__)


class AthenaDataSource(DataSource):
    TYPE = "athena"

    def __init__(self, logs: Logs, data_source_name: str, data_source_properties: dict, connection_properties: dict):
        super().__init__(logs, data_source_name, data_source_properties, connection_properties)

        self.athena_staging_dir = connection_properties.get("staging_dir")
        self.catalog = connection_properties.get("catalog")
        self.work_group = connection_properties.get("work_group")
        self.aws_credentials = AwsCredentials(
            access_key_id=connection_properties.get("access_key_id"),
            secret_access_key=connection_properties.get("secret_access_key"),
            role_arn=connection_properties.get("role_arn"),
            session_token=connection_properties.get("session_token"),
            region_name=connection_properties.get("region_name"),
            profile_name=connection_properties.get("profile_name"),
        )

    def connect(self):
        try:
            self.connection = pyathena.connect(
                profile_name=self.aws_credentials.profile_name,
                aws_access_key_id=self.aws_credentials.access_key_id,
                aws_secret_access_key=self.aws_credentials.secret_access_key,
                s3_staging_dir=self.athena_staging_dir,
                region_name=self.aws_credentials.region_name,
                role_arn=self.aws_credentials.role_arn,
                catalog_name=self.catalog,
                work_group=self.work_group,
                schema_name=self.schema,
            )

            return self.connection
        except Exception as e:
            raise DataSourceConnectionError(self.TYPE, e)

    SCHEMA_CHECK_TYPES_MAPPING: dict = {
        "string": ["character varying", "varchar"],
    }
    SQL_TYPE_FOR_CREATE_TABLE_MAP: dict = {
        DataType.TEXT: "string",
        DataType.INTEGER: "int",
        DataType.DECIMAL: "double",
        DataType.DATE: "date",
        DataType.TIME: "date",
        DataType.TIMESTAMP: "timestamp",
        DataType.TIMESTAMP_TZ: "timestamp",
        DataType.BOOLEAN: "boolean",
    }

    SQL_TYPE_FOR_SCHEMA_CHECK_MAP: dict = {
        DataType.TEXT: "varchar",
        DataType.INTEGER: "integer",
        DataType.DECIMAL: "double",
        DataType.DATE: "date",
        DataType.TIME: "date",
        DataType.TIMESTAMP: "timestamp",
        DataType.TIMESTAMP_TZ: "timestamp",
        DataType.BOOLEAN: "boolean",
    }

    # NUMERIC_TYPES_FOR_PROFILING: list = ["NUMERIC", "INT64"]
    # TEXT_TYPES_FOR_PROFILING: list = ["STRING"]

    def literal_datetime(self, datetime: datetime):
        formatted = datetime.strftime("%Y-%m-%d %H:%M:%S")
        return f"TIMESTAMP '{formatted}'"

    def quote_column_declaration(self, column_name: str) -> str:
        return self.quote_column_for_create(column_name)

    def quote_column_for_create(self, column_name: str) -> str:
        return f"`{column_name}`"

    def quote_column(self, column_name: str) -> str:
        return f'"{column_name}"'

    def regex_replace_flags(self) -> str:
        return ""

    @staticmethod
    def column_metadata_catalog_column() -> str:
        return "table_schema"

    @staticmethod
    def default_casify_table_name(identifier: str) -> str:
        return identifier.lower()

    @staticmethod
    def default_casify_column_name(identifier: str) -> str:
        return identifier.lower()

    def get_metric_sql_aggregation_expression(self, metric_name: str, metric_args: list[object] | None, expr: str):
        if metric_name in [
            "stddev",
            "stddev_pop",
            "stddev_samp",
            "variance",
            "var_pop",
            "var_samp",
        ]:
            return f"{metric_name.upper()}({expr})"
        return super().get_metric_sql_aggregation_expression(metric_name, metric_args, expr)

    def sql_get_table_names_with_count(
        self, include_tables: list[str] | None = None, exclude_tables: list[str] | None = None
    ) -> str:
        return ""

    def rollback(self):
        pass

    def create_test_table_manager(self):
        from tests.athena_data_source_fixture import AthenaDataSourceFixture

        return AthenaDataSourceFixture(self)