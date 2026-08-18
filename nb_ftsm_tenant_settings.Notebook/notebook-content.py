# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "",
# META       "default_lakehouse_workspace_id": "",
# META       "known_lakehouses": []
# META     }
# META   }
# META }

# MARKDOWN ********************

# ##### Set a **defaultLakehouse** configuration

# CELL ********************

# MAGIC %%configure -f
# MAGIC {
# MAGIC     "defaultLakehouse": {
# MAGIC         "name": "FTSMonitorLH"
# MAGIC     }
# MAGIC }

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ##### Create **Delta tables** in the Lakehouse

# CELL ********************

# Create Delta tables if not exists
spark.sql("""
CREATE TABLE IF NOT EXISTS ftsm_capacity_settings (
    capacityId STRING,
    tenantSettingGroup STRING,
    delegatedFrom STRING,
    settingName STRING,
    title STRING,
    enabled STRING,
    canSpecifySecurityGroups STRING,
    enabledSecurityGroups STRING,
    snapshotTimestamp TIMESTAMP,
    snapshotDate DATE
)
USING DELTA
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS ftsm_fabric_capacities (
    capacityId STRING,
    capacityName STRING,
    capacityRegion STRING,
    capacitySku STRING,
    capacityState STRING,
    snapshotTimestamp TIMESTAMP,
    snapshotDate DATE
)
USING DELTA
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS ftsm_tenant_settings (
    tenantSettingGroup STRING,
    title STRING,
    settingName STRING,
    enabled BOOLEAN,
    canSpecifySecurityGroups BOOLEAN,
    enabledSecurityGroups ARRAY<MAP<STRING,STRING>>,
    delegateToWorkspace BOOLEAN,
    delegateToDomain BOOLEAN,
    delegateToCapacity BOOLEAN,
    properties ARRAY<MAP<STRING,STRING>>,
    snapshotTimestamp TIMESTAMP,
    snapshotDate DATE
)
USING DELTA
""")

print("Tables created successfully (or already existed).")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ##### Define a shared **SnapshotTimestamp** for all records in this run

# CELL ********************

# Set Common Snapshot Run time as snapshotTimestamp based on current_timestamp()
from datetime import datetime, timezone

pSnapshotTS = datetime.now(timezone.utc)

print(pSnapshotTS)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ##### Extract the **admin/tenantsettings** and persist in the lakehouse

# CELL ********************

import json
import sempy.fabric as fabric
from pyspark.sql import functions as F
from pyspark.sql.types import *
from sempy.fabric.exceptions import FabricHTTPException


def get_tenantSettings():

    schema = StructType([
        StructField("tenantSettingGroup", StringType(), True),
        StructField("title", StringType(), True),
        StructField("settingName", StringType(), True),
        StructField("enabled", BooleanType(), True),
        StructField("canSpecifySecurityGroups", BooleanType(), True),
        StructField("enabledSecurityGroups", ArrayType(MapType(StringType(), StringType())), True),
        StructField("delegateToWorkspace", BooleanType(), True),
        StructField("delegateToDomain", BooleanType(), True),
        StructField("delegateToCapacity", BooleanType(), True),
        StructField("properties", ArrayType(MapType(StringType(), StringType())), True),
        StructField("snapshotTimestamp", TimestampType(), True),
        StructField("snapshotDate", DateType(), True)
    ])

    try:
        client = fabric.PowerBIRestClient()
        response = client.get("v1/admin/tenantsettings")

        if response.status_code != 200:
            print(f"API returned status code {response.status_code}")
            return spark.createDataFrame([], schema)

        data = json.loads(response.text)
        tenant_settings = data.get("tenantSettings", [])

        if not tenant_settings:
            print("No tenant settings returned.")
            return spark.createDataFrame([], schema)

        df_fts = spark.createDataFrame(tenant_settings)

        snapshot_col = (
            F.lit(pSnapshotTS)
            if "pSnapshotTS" in globals() and pSnapshotTS is not None
            else F.current_timestamp()
        )

        df_tenantsettings = (
            df_fts
            .select(
                "tenantSettingGroup",
                "title",
                "settingName",
                "enabled",
                "canSpecifySecurityGroups",
                "enabledSecurityGroups",
                "delegateToWorkspace",
                "delegateToDomain",
                "delegateToCapacity",
                "properties"
            )
            .withColumn("snapshotTimestamp", snapshot_col)
            .withColumn("snapshotDate", F.to_date("snapshotTimestamp"))
        )

        return df_tenantsettings

    except FabricHTTPException as e:
        print(
            "WARNING: Unable to retrieve tenant settings from v1/admin/tenantsettings. "
            "This API requires the executing identity to hold the Fabric Administrator role "
            "(or equivalent tenant admin API access). Continuing without failing the run; "
            "no rows will be written to ftsm_tenant_settings for this snapshot.\n"
            f"Details: {e}"
        )
        return spark.createDataFrame([], schema)

    except Exception as e:
        print(f"WARNING: Unexpected error retrieving tenant settings: {e}")
        return spark.createDataFrame([], schema)


# Execute
df_fts = get_tenantSettings()

display(df_fts)

# Only write if data exists (DataFrame check, no RDD)
if df_fts.limit(1).count() > 0:
    (
        df_fts.write
        .mode("append")
        .format("delta")
        .saveAsTable("ftsm_tenant_settings")
    )
    print("Appended tenant settings data successfully.")
else:
    print("No tenant settings data available to write.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ##### Extract the **list of capacities** and persist in the lakehouse

# CELL ********************

import sempy.fabric as fabric
from pyspark.sql import functions as F
from pyspark.sql.types import *


def get_capacities():

    schema = StructType([
        StructField("capacityId", StringType(), True),
        StructField("capacityName", StringType(), True),
        StructField("capacityRegion", StringType(), True),
        StructField("capacitySku", StringType(), True),
        StructField("capacityState", StringType(), True),
        StructField("snapshotTimestamp", TimestampType(), True),
        StructField("snapshotDate", DateType(), True)
    ])

    try:
        caps = fabric.list_capacities()

        # Handle None or empty result
        if caps is None or len(caps) == 0:
            print("No capacities returned.")
            return spark.createDataFrame([], schema)

        df_fcaps = spark.createDataFrame(caps)

        snapshot_col = (
            F.lit(pSnapshotTS)
            if 'pSnapshotTS' in globals() and pSnapshotTS is not None
            else F.current_timestamp()
        )

        df_capacities = (
            df_fcaps
            .select(
                F.lower(F.col("Id")).alias("capacityId"),
                F.col("Display Name").alias("capacityName"),
                F.col("Region").alias("capacityRegion"),
                F.col("Sku").alias("capacitySku"),
                F.col("State").alias("capacityState")
            )
            .withColumn("snapshotTimestamp", snapshot_col)
            .withColumn("snapshotDate", F.to_date("snapshotTimestamp"))
        )

        return df_capacities

    except Exception as e:
        print(
            "WARNING: Unable to retrieve capacities via fabric.list_capacities(). "
            "Ensure the executing identity has Capacity Contributor/Admin rights on the "
            "relevant capacities (or Fabric Administrator for a full tenant-wide list). "
            "Continuing without failing the run; no rows will be written to "
            f"ftsm_fabric_capacities for this snapshot.\nDetails: {e}"
        )
        return spark.createDataFrame([], schema)


# Execute
df_caps = get_capacities()

display(df_caps)

# Write only if rows exist (DataFrame check, no RDD)
if df_caps.limit(1).count() > 0:
    (
        df_caps.write
        .mode("append")
        .format("delta")
        .saveAsTable("ftsm_fabric_capacities")
    )
    print("Appended capacity data successfully.")
else:
    print("No capacity data available to write.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ##### Extract the **admin/capacities/delegatedTenantSettingOverrides** and persist in the lakehouse

# CELL ********************

import json
import sempy.fabric as fabric
from sempy.fabric.exceptions import FabricHTTPException
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, BooleanType, ArrayType
)

tenant_setting_schema = StructType([
    StructField("tenantSettingGroup", StringType()),
    StructField("delegatedFrom", StringType()),
    StructField("settingName", StringType()),
    StructField("title", StringType()),
    StructField("enabled", BooleanType()),
    StructField("canSpecifySecurityGroups", BooleanType()),
    StructField("enabledSecurityGroups", ArrayType(StringType())),
])

raw_schema = StructType([
    StructField("id", StringType()),
    StructField("tenantSettings", ArrayType(tenant_setting_schema)),
])


def flatten_delegated(df_raw):
    return (
        df_raw
        .withColumn("tenantSetting", F.explode_outer("tenantSettings"))
        .select(
            F.lower(F.col("id")).alias("capacityId"),
            F.col("tenantSetting.tenantSettingGroup"),
            F.col("tenantSetting.delegatedFrom"),
            F.col("tenantSetting.settingName"),
            F.col("tenantSetting.title"),
            F.col("tenantSetting.enabled").cast("string").alias("enabled"),
            F.col("tenantSetting.canSpecifySecurityGroups").cast("string").alias("canSpecifySecurityGroups"),
            F.to_json(F.col("tenantSetting.enabledSecurityGroups")).alias("enabledSecurityGroups"),
        )
        .withColumn(
            "snapshotTimestamp",
            F.lit(pSnapshotTS).cast("timestamp")
            if ("pSnapshotTS" in globals() and pSnapshotTS is not None)
            else F.current_timestamp(),
        )
        .withColumn("snapshotDate", F.to_date("snapshotTimestamp"))
    )


def get_delegatedTenantSettings():
    client = fabric.PowerBIRestClient()
    try:
        response = client.get("v1/admin/capacities/delegatedTenantSettingOverrides")
        data = json.loads(response.text)
        rows = data.get("value", [])
        df_raw = spark.createDataFrame(rows, schema=raw_schema)
        return flatten_delegated(df_raw)
    except FabricHTTPException as e:
        print(
            "WARNING: Unable to retrieve delegated tenant setting overrides from "
            "v1/admin/capacities/delegatedTenantSettingOverrides. This API requires the "
            "Fabric Administrator role (or equivalent tenant admin API access). Continuing "
            "without failing the run; no rows will be written to ftsm_capacity_settings "
            f"for this snapshot.\nDetails: {e}"
        )
        empty_raw = spark.createDataFrame([], schema=raw_schema)
        return flatten_delegated(empty_raw)


df_dctso = get_delegatedTenantSettings()
display(df_dctso)

if df_dctso.limit(1).count() > 0:
    df_dctso.write \
        .mode("append") \
        .format("delta") \
        .saveAsTable("ftsm_capacity_settings")
    print("Appended delegated tenant settings data successfully.")
else:
    print("No delegated tenant settings data available to write.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time
import sempy.fabric as fabric

dataset = "FTSMonitorSM"

request_id = fabric.refresh_dataset(dataset=dataset, refresh_type="full")
print(f"Refresh started: {request_id}")

while True:
    history = fabric.list_refresh_requests(dataset=dataset)
    row = history[history["Request Id"] == request_id]
    status = row["Status"].iloc[0] if not row.empty else "Unknown"
    print(f"Status: {status}")
    if status in ("Completed", "Failed", "Cancelled"):
        break
    time.sleep(30)

if status != "Completed":
    raise Exception(f"Semantic model refresh {status}")
print("Semantic model refreshed successfully.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
