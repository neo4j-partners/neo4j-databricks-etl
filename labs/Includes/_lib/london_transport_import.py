"""
London Transport import module.

This module handles the full ETL pipeline:
- Load CSV files from Unity Catalog Volume into Delta Lake tables
- Write Station nodes to Neo4j via Spark Connector
- Create tube line relationships with line-specific relationship types
- Validate the imported graph

Called by the "1 - Load London Transport" notebook via %run.
"""

import time

import yaml
from pyspark.sql import functions as F


# =============================================================================
# CONFIGURATION
# =============================================================================

def _load_config() -> dict:
    """Read config.yaml from the Includes directory."""
    notebook_path = (
        dbutils.entry_point.getDbutils()  # noqa: F821
        .notebook().getContext().notebookPath().get()
    )
    workspace_base = "/Workspace" + notebook_path.rsplit("/", 1)[0]
    config_path = f"{workspace_base}/Includes/config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_neo4j_config() -> dict:
    """Load Neo4j configuration from Databricks Secrets.

    Returns dict with neo4j_url, neo4j_user, neo4j_pass, volume_path,
    neo4j_database, catalog, and schema.
    """
    print("=" * 70)
    print("CONFIGURATION")
    print("=" * 70)

    file_config = _load_config()
    scope = file_config["secrets"]["scope_name"]

    config = {
        "neo4j_url": dbutils.secrets.get(scope=scope, key="url"),  # noqa: F821
        "neo4j_user": dbutils.secrets.get(scope=scope, key="username"),  # noqa: F821
        "neo4j_pass": dbutils.secrets.get(scope=scope, key="password"),  # noqa: F821
        "volume_path": dbutils.secrets.get(scope=scope, key="volume_path"),  # noqa: F821
        "neo4j_database": "neo4j",
    }

    # Derive catalog and schema from volume path: /Volumes/{catalog}/{schema}/{volume}
    parts = config["volume_path"].strip("/").split("/")
    config["catalog"] = parts[1]
    config["schema"] = parts[2]

    # Configure Spark session for Neo4j connector
    spark.conf.set("neo4j.url", config["neo4j_url"])  # noqa: F821
    spark.conf.set("neo4j.authentication.basic.username", config["neo4j_user"])  # noqa: F821
    spark.conf.set("neo4j.authentication.basic.password", config["neo4j_pass"])  # noqa: F821
    spark.conf.set("neo4j.database", config["neo4j_database"])  # noqa: F821

    print(f"  Neo4j URL:    {config['neo4j_url']}")
    print(f"  Volume Path:  {config['volume_path']}")
    print(f"  Catalog:      {config['catalog']}")
    print(f"  Schema:       {config['schema']}")
    print("  [OK] Configuration loaded")
    return config


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_cypher(config: dict, query: str):
    """Execute a Cypher query via the Spark Connector and return results."""
    return (
        spark.read.format("org.neo4j.spark.DataSource")  # noqa: F821
        .option("url", config["neo4j_url"])
        .option("authentication.basic.username", config["neo4j_user"])
        .option("authentication.basic.password", config["neo4j_pass"])
        .option("database", config["neo4j_database"])
        .option("query", query)
        .load()
    )


# =============================================================================
# CLEAR DATABASE
# =============================================================================

def clear_database(config: dict) -> bool:
    """Clear all nodes and relationships from Neo4j."""
    from neo4j import GraphDatabase

    print("\n" + "=" * 70)
    print("CLEARING DATABASE")
    print("=" * 70)

    driver = GraphDatabase.driver(config["neo4j_url"], auth=(config["neo4j_user"], config["neo4j_pass"]))
    with driver.session(database=config["neo4j_database"]) as session:
        result = session.run("MATCH (n) DETACH DELETE n")
        summary = result.consume()
        print(f"  Deleted {summary.counters.nodes_deleted} nodes, {summary.counters.relationships_deleted} relationships")
    driver.close()
    return True


# =============================================================================
# CSV TO DELTA LAKE
# =============================================================================

def load_csv_to_delta(config: dict) -> dict:
    """Load CSV files from volume, transform, and write to Delta Lake tables.

    Returns dict with station and tube line DataFrames and table names.
    """
    print("\n" + "=" * 70)
    print("LOADING CSV DATA TO DELTA LAKE")
    print("=" * 70)

    csv_path = f"{config['volume_path']}/csv"
    catalog = config["catalog"]
    schema = config["schema"]

    stations_table = f"{catalog}.{schema}.london_stations"
    tube_lines_table = f"{catalog}.{schema}.london_tube_lines"

    # Load and transform stations
    print(f"\n  Reading London_stations.csv...")
    stations_raw = (
        spark.read  # noqa: F821
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(f"{csv_path}/London_stations.csv")
    )
    print(f"  [OK] {stations_raw.count()} rows loaded")

    stations_clean = stations_raw.select(
        F.col("ID").cast("integer").alias("station_id"),
        F.col("Station_Name").alias("name"),
        F.col("Latitude").cast("double").alias("latitude"),
        F.col("Longitude").cast("double").alias("longitude"),
        F.col("Zone").alias("zone"),
        F.col("Postcode").alias("postcode"),
    )

    print(f"  Writing to Delta table: {stations_table}")
    stations_clean.write.format("delta").mode("overwrite").saveAsTable(stations_table)
    station_count = spark.table(stations_table).count()  # noqa: F821
    print(f"  [OK] {station_count} stations in Delta table")

    # Load tube lines
    print(f"\n  Reading London_tube_lines.csv...")
    tube_lines_raw = (
        spark.read  # noqa: F821
        .option("header", "true")
        .csv(f"{csv_path}/London_tube_lines.csv")
    )
    print(f"  [OK] {tube_lines_raw.count()} rows loaded")

    print(f"  Writing to Delta table: {tube_lines_table}")
    tube_lines_raw.write.format("delta").mode("overwrite").saveAsTable(tube_lines_table)
    tube_count = spark.table(tube_lines_table).count()  # noqa: F821
    print(f"  [OK] {tube_count} connections in Delta table")

    return {
        "stations_table": stations_table,
        "tube_lines_table": tube_lines_table,
        "station_count": station_count,
        "tube_count": tube_count,
    }


# =============================================================================
# WRITE NODES TO NEO4J
# =============================================================================

def write_station_nodes(config: dict, tables: dict) -> int:
    """Write Station nodes from Delta table to Neo4j."""
    print("\n" + "=" * 70)
    print("WRITING STATION NODES TO NEO4J")
    print("=" * 70)

    stations = spark.table(tables["stations_table"])  # noqa: F821
    count = stations.count()

    start_time = time.time()
    print(f"\n  Writing {count} Station nodes...")

    (
        stations.write
        .format("org.neo4j.spark.DataSource")
        .mode("Overwrite")
        .option("labels", ":Station")
        .option("node.keys", "station_id")
        .save()
    )

    elapsed = time.time() - start_time
    print(f"  [OK] {count} Station nodes written ({elapsed:.1f}s)")
    return count


def create_station_index(config: dict):
    """Create index on station_id for query performance."""
    print("\n  Creating index on station_id...")
    try:
        run_cypher(config, "CREATE INDEX station_id IF NOT EXISTS FOR (s:Station) ON (s.station_id)").collect()
        print("  [OK] Index created")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  [OK] Index already exists")
        else:
            print(f"  Index creation result: {e}")


# =============================================================================
# WRITE RELATIONSHIPS TO NEO4J
# =============================================================================

def write_tube_line_relationships(config: dict, tables: dict) -> dict:
    """Create bidirectional relationships for all tube lines.

    Uses line-specific relationship types (e.g., :BAKERLOO, :CENTRAL)
    instead of a single type with properties, following Neo4j best practices.

    Returns dict with counts per tube line.
    """
    print("\n" + "=" * 70)
    print("CREATING TUBE LINE RELATIONSHIPS")
    print("=" * 70)

    print("\n  Neo4j Best Practice: Using relationship TYPES for each tube line")
    print("  (e.g., :BAKERLOO, :CENTRAL) instead of a single type with properties.\n")

    tube_lines = spark.table(tables["tube_lines_table"])  # noqa: F821

    # Get all unique tube lines
    line_names = (
        tube_lines.select("Tube_Line").distinct()
        .rdd.flatMap(lambda x: x).collect()
    )
    print(f"  Found {len(line_names)} tube lines to process\n")

    results = {}
    total_start = time.time()

    for line in sorted(line_names):
        line_data = (
            tube_lines
            .filter(F.col("Tube_Line") == line)
            .select(
                F.col("From_Station").alias("from_station"),
                F.col("To_Station").alias("to_station"),
            )
        )

        connection_count = line_data.count()

        # Convert line name to valid Neo4j relationship type
        rel_type = line.upper().replace(" ", "_").replace("&", "AND")

        start_time = time.time()

        # Forward direction
        (
            line_data.write
            .format("org.neo4j.spark.DataSource")
            .mode("Append")
            .option("relationship", rel_type)
            .option("relationship.save.strategy", "keys")
            .option("relationship.source.labels", ":Station")
            .option("relationship.source.save.mode", "Match")
            .option("relationship.source.node.keys", "from_station:name")
            .option("relationship.target.labels", ":Station")
            .option("relationship.target.save.mode", "Match")
            .option("relationship.target.node.keys", "to_station:name")
            .save()
        )

        # Reverse direction for bidirectional connections
        (
            line_data
            .select(
                F.col("to_station").alias("from_station"),
                F.col("from_station").alias("to_station"),
            )
            .write
            .format("org.neo4j.spark.DataSource")
            .mode("Append")
            .option("relationship", rel_type)
            .option("relationship.save.strategy", "keys")
            .option("relationship.source.labels", ":Station")
            .option("relationship.source.save.mode", "Match")
            .option("relationship.source.node.keys", "from_station:name")
            .option("relationship.target.labels", ":Station")
            .option("relationship.target.save.mode", "Match")
            .option("relationship.target.node.keys", "to_station:name")
            .save()
        )

        elapsed = time.time() - start_time
        results[rel_type] = connection_count
        print(f"  [OK] :{rel_type} - {connection_count} bidirectional connections ({elapsed:.1f}s)")

    total_elapsed = time.time() - total_start
    total_connections = sum(results.values())
    print(f"\n  Total: {total_connections} connections across {len(results)} tube lines ({total_elapsed:.1f}s)")
    return results


# =============================================================================
# VALIDATION
# =============================================================================

def validate_import(config: dict) -> bool:
    """Validate the import by checking node and relationship counts."""
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    # Station count
    print("\n  Station nodes:")
    node_counts = run_cypher(config, "MATCH (s:Station) RETURN count(s) AS count").collect()
    for row in node_counts:
        print(f"    Station: {row['count']}")

    # Relationships by type
    print("\n  Relationships by tube line:")
    rel_query = """
    MATCH ()-[r]->()
    RETURN type(r) AS line, count(r) AS count
    ORDER BY count DESC
    """
    rel_counts = run_cypher(config, rel_query).collect()
    for row in rel_counts:
        print(f"    {row['line']:<25} {row['count']:>6}")

    total_rels = sum(row["count"] for row in rel_counts)
    print(f"\n  Total: {node_counts[0]['count']} stations, {total_rels} relationships")

    # Top 10 busiest stations
    print("\n  Top 10 busiest stations:")
    busiest_query = """
    MATCH (s:Station)
    RETURN s.name AS station, count{(s)-[]-()} AS total_connections
    ORDER BY total_connections DESC
    LIMIT 10
    """
    busiest = run_cypher(config, busiest_query).collect()
    for row in busiest:
        print(f"    {row['station']:<35} {row['total_connections']:>4} connections")

    return True


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def run_full_import() -> bool:
    """Run the complete London Transport ETL pipeline.

    Pipeline: CSV (Volume) -> Delta Lake -> Neo4j
    """
    total_start = time.time()

    # Load config from secrets
    config = load_neo4j_config()

    # Verify connection
    print("\n  Verifying Neo4j connection...")
    run_cypher(config, "RETURN 'Connected' AS status").collect()
    print("  [OK] Connected to Neo4j")

    # Clear database
    clear_database(config)

    # Load CSVs to Delta Lake
    tables = load_csv_to_delta(config)

    # Write nodes
    write_station_nodes(config, tables)
    create_station_index(config)

    # Write relationships
    write_tube_line_relationships(config, tables)

    # Validate
    validate_import(config)

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 70)
    print(f"IMPORT COMPLETE ({total_elapsed:.1f}s)")
    print("=" * 70)
    print("\n  Proceed to '2 - Query London Transport' or explore the graph in Neo4j Browser.")

    return True
