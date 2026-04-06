# Databricks notebook source

# MAGIC %md
# MAGIC # Required Setup
# MAGIC
# MAGIC ### Estimated setup time: 5 minutes
# MAGIC
# MAGIC This notebook prepares your Databricks environment for the London Transport ETL Workshop.
# MAGIC It creates the required catalog, schema, volume, copies data files, and configures
# MAGIC Neo4j credentials.
# MAGIC
# MAGIC **Run this notebook once before starting any labs.**
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - A **Dedicated** compute cluster with the Neo4j Spark Connector installed:
# MAGIC   - Access mode: **Dedicated** (required for the Spark Connector)
# MAGIC   - Runtime: 13.3 LTS or higher
# MAGIC   - Maven library: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
# MAGIC   - PyPI library: `neo4j==6.0.2`
# MAGIC - A running **Neo4j** instance (Aura or self-hosted) with connection details ready
# MAGIC - Permission to **create a catalog** in your workspace (or an existing catalog you can use)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Enter Your Neo4j Connection Details
# MAGIC
# MAGIC Fill in the widgets at the top of this notebook with your Neo4j connection information.
# MAGIC These values will be stored as Databricks secrets so subsequent notebooks can use them.

# COMMAND ----------

dbutils.widgets.text("neo4j_url", "", "Neo4j URI (e.g. neo4j+s://xxx.databases.neo4j.io)")
dbutils.widgets.text("neo4j_username", "neo4j", "Neo4j Username")
dbutils.widgets.text("neo4j_password", "", "Neo4j Password")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Run the Setup
# MAGIC
# MAGIC The cell below will:
# MAGIC 1. Create a catalog and schema based on your username
# MAGIC 2. Create a volume and copy the London Transport CSV files into it
# MAGIC 3. Store your Neo4j credentials as Databricks secrets
# MAGIC 4. Verify the Neo4j connection
# MAGIC
# MAGIC Review the output to confirm everything succeeded.

# COMMAND ----------

# Get widget values
neo4j_url = dbutils.widgets.get("neo4j_url")
neo4j_username = dbutils.widgets.get("neo4j_username")
neo4j_password = dbutils.widgets.get("neo4j_password")

if not neo4j_url or not neo4j_password:
    raise ValueError(
        "Please fill in the Neo4j URI and Password widgets at the top of this notebook before running."
    )

# COMMAND ----------

# MAGIC %run ./Includes/_lib/setup_orchestrator

# COMMAND ----------

import yaml

# Load configuration
notebook_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
workspace_base = "/Workspace" + notebook_path.rsplit("/", 1)[0]
config_path = f"{workspace_base}/Includes/config.yaml"

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

catalog_config = config["catalog"]
secrets_config = config["secrets"]

print("Configuration loaded:")
print(f"  Catalog prefix: {catalog_config['prefix']}")
print(f"  Schema:         {catalog_config['schema_name']}")
print(f"  Volume:         {catalog_config['volume_name']}")
print(f"  Secret scope:   {secrets_config['scope_name']}")

# COMMAND ----------

# Step 1: Create catalog, schema, and volume
username = get_username()
catalog_name = derive_catalog_name(catalog_config["prefix"], username)

catalog_info = setup_catalog_and_schema(
    catalog_name=catalog_name,
    schema_name=catalog_config["schema_name"],
    volume_name=catalog_config["volume_name"],
)

# COMMAND ----------

# Step 2: Copy data files to volume
includes_data_path = f"{workspace_base}/Includes/data"

file_counts = copy_data_files(
    volume_path=catalog_info["volume_path"],
    includes_data_path=includes_data_path,
)

# COMMAND ----------

# Step 3: Store Neo4j secrets
setup_neo4j_secrets(
    scope_name=secrets_config["scope_name"],
    neo4j_url=neo4j_url,
    neo4j_username=neo4j_username,
    neo4j_password=neo4j_password,
    volume_path=catalog_info["volume_path"],
)

# COMMAND ----------

# Step 4: Verify Neo4j connection
neo4j_connected = verify_neo4j_connection(neo4j_url, neo4j_username, neo4j_password)

# COMMAND ----------

# Print summary
print_summary({
    "catalog": catalog_info["catalog"],
    "schema": catalog_info["schema"],
    "volume": catalog_info["volume"],
    "volume_path": catalog_info["volume_path"],
    "neo4j_url": neo4j_url,
    "scope_name": secrets_config["scope_name"],
    "file_counts": file_counts,
    "neo4j_connected": neo4j_connected,
})

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC If the setup completed successfully, proceed to **1 - Load London Transport** to load all data into Neo4j.
