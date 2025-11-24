# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository demonstrates ETL from Databricks to Neo4j using Delta Lake and PySpark. It loads the London Transport Network dataset (302 stations, multiple tube lines) from CSV files into a Neo4j graph database.

**Key Architecture:** CSV → Unity Catalog Volume → Delta Lake Tables → PySpark → Neo4j

## Core Commands

### Development & Testing
```bash
# List repository structure
ls -la

# View notebook contents (Jupyter notebook format)
# Notebooks are in notebooks/load_london_transport.ipynb
```

**Note:** This is a Databricks notebook-based project. There are no local build, test, or lint commands. All execution happens in Databricks workspace.

### Databricks Execution

The main notebook is `notebooks/load_london_transport.ipynb` which must be run in a Databricks environment with:
- Unity Catalog enabled
- Neo4j Spark Connector library: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
- Neo4j Python Driver: `neo4j==6.0.2`
- Databricks Secrets configured (scope: `neo4j`, key: `password`)

## Architecture & Data Flow

### ETL Pipeline Structure

```
CSV Files (Unity Catalog Volume)
    ↓
Delta Lake Tables (Intermediate Storage)
    ↓
PySpark Transformations
    ↓
Neo4j Graph Database (via Spark Connector)
```

### Data Model

**Source Data:**
- `London_stations.csv` - 302 stations with coordinates, zones, postcodes
- `London_tube_lines.csv` - Tube line connections between stations

**Delta Lake Tables:**
- `{catalog}.{schema}.london_stations` - Cleaned station data
- `{catalog}.{schema}.london_tube_lines` - Tube line connections

**Neo4j Graph Model:**
- Nodes: `(:Station)` with properties: `station_id`, `name`, `latitude`, `longitude`, `zone`, `postcode`
- Relationships: Line-specific types (`:BAKERLOO`, `:CENTRAL`, `:CIRCLE`, `:DISTRICT`, etc.)
  - **Critical Design Decision:** Uses relationship TYPES instead of a single relationship type with properties
  - Rationale: Better query performance, clearer semantics, better visualization in Neo4j Browser

### Key Implementation Patterns

**Neo4j Connection Configuration:**
```python
NEO4J_URL = dbutils.widgets.get("neo4j_url")
NEO4J_USER = dbutils.widgets.get("neo4j_username")
NEO4J_PASS = dbutils.secrets.get(scope="neo4j", key="password")
NEO4J_DB = dbutils.widgets.get("neo4j_database")

spark.conf.set("neo4j.url", NEO4J_URL)
spark.conf.set("neo4j.authentication.basic.username", NEO4J_USER)
spark.conf.set("neo4j.authentication.basic.password", NEO4J_PASS)
spark.conf.set("neo4j.database", NEO4J_DB)
```

**Reading CSV to Delta Lake:**
```python
df = spark.read.option("header", "true").option("inferSchema", "true").csv(f"{BASE_PATH}/file.csv")
df.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.table_name")
```

**Writing Nodes to Neo4j:**
```python
df.write \
  .format("org.neo4j.spark.DataSource") \
  .mode("Overwrite") \
  .option("labels", ":Station") \
  .option("node.keys", "station_id") \
  .save()
```

**Writing Relationships to Neo4j (Bidirectional):**
```python
# Forward direction
df.write \
  .format("org.neo4j.spark.DataSource") \
  .mode("Append") \
  .option("relationship", "LINE_TYPE") \
  .option("relationship.save.strategy", "keys") \
  .option("relationship.source.labels", ":Station") \
  .option("relationship.source.save.mode", "Match") \
  .option("relationship.source.node.keys", "from_station:name") \
  .option("relationship.target.labels", ":Station") \
  .option("relationship.target.save.mode", "Match") \
  .option("relationship.target.node.keys", "to_station:name") \
  .save()

# Reverse direction (for bidirectional)
df.select(
    F.col("to_station").alias("from_station"),
    F.col("from_station").alias("to_station")
).write \
  .format("org.neo4j.spark.DataSource") \
  .mode("Append") \
  .option("relationship", "LINE_TYPE") \
  # ... same options as forward
  .save()
```

## File Structure

```
neo4j-databricks-etl/
├── README.md                              # Setup instructions and overview
├── CLAUDE.md                              # This file - guidance for Claude Code
├── EXPLORING_DATA.md                      # Visual exploration guide for Neo4j Aura
├── DBX_PORT_v2.md                         # Implementation plan and status
├── TEXT2CYPHER_PROPOSAL.md                # Text-to-Cypher agent proposal and status
├── datasets/
│   ├── csv_files/london_transport/
│   │   ├── London_stations.csv            # 302 stations
│   │   └── London_tube_lines.csv          # Tube connections
│   └── README.md                          # Dataset documentation
├── images/
│   ├── aura_explore.png                   # Aura Explore interface screenshot
│   ├── search_stations.png                # Search pattern example
│   └── all_stations_graph.png             # Full graph visualization
└── notebooks/
    ├── load_london_transport.ipynb        # ETL notebook (12 steps)
    └── query_london_transport.ipynb       # Text-to-Cypher agent for querying data
```

## Notebook Structure

### ETL Notebook

The ETL notebook (`load_london_transport.ipynb`) is organized into these sections:

1. **Prerequisites & Configuration** - Widgets for connection parameters
2. **Connection Testing** - Verify Neo4j connectivity
3. **Part 1: CSV → Delta Lake** (Steps 1-6)
   - Verify CSV files in Unity Catalog Volume
   - Load and transform stations data
   - Load tube lines data
   - Write to Delta tables
4. **Part 2: Stations → Neo4j** (Steps 7-9)
   - Write Station nodes
   - Create index on station_id
   - Verify node creation
5. **Part 3: Bakerloo Line (Proof-of-Concept)** (Steps 10-12)
   - Create relationships for single line
   - Validate implementation
6. **Part 4: All Tube Lines** (Steps 13-14)
   - Dynamically create line-specific relationship types
   - Process all remaining tube lines
7. **Part 5: Final Validation** (Step 15)
   - Count nodes and relationships by type
   - Query busiest stations
   - Sample path queries

### Text-to-Cypher Query Notebook

The query notebook (`query_london_transport.ipynb`) allows natural language queries:

1. **Configuration** - Widgets for Neo4j and Databricks Foundation Model setup
2. **Connection and Validation** - Verify graph data exists
3. **Schema Retrieval** - Display graph structure
4. **LLM Configuration** - Set up Cypher generation with specialized prompt
5. **Query Interface** - Simple `ask_question()` function
6. **Example Questions** - Organized by category:
   - Basic counting ("How many stations in zone 1?")
   - Station information ("What zone is King's Cross in?")
   - Tube line queries ("Which stations does Bakerloo connect?")
   - Connection/traffic queries ("Which stations have most connections?")
   - London travel ("Find path between stations", "Avoid busy stations")
7. **Documentation** - How it works, limitations, troubleshooting

**Key Features:**
- Uses Databricks Foundation Models (databricks-claude-sonnet-4-5)
- Temperature 0.0 for consistent Cypher generation
- Modern Cypher syntax (COUNT{} subqueries)
- Verbose mode shows generated Cypher
- Direct result return (no LLM post-processing)

## Important Neo4j Best Practices

### Relationship Types vs Properties

This project uses **relationship types** (not properties) for tube lines:

**Good (this project):**
```cypher
MATCH (from:Station)-[:BAKERLOO]->(to:Station)
```

**Avoid:**
```cypher
MATCH (from:Station)-[:CONNECTED {line: "Bakerloo"}]->(to:Station)
```

**Why:**
1. Relationship type lookups are indexed by Neo4j
2. Better query performance
3. Clearer semantics
4. Better visualization (different colors in Neo4j Browser)

### Modern Cypher Patterns (Neo4j 5.x+)

The notebook uses modern Cypher syntax:

**COUNT{} subqueries** (preferred over OPTIONAL MATCH):
```cypher
RETURN
  count{MATCH (s:Station)} as total_stations,
  count{MATCH ()-[r:BAKERLOO]->()} as total_relationships
```

**Avoids Cartesian products:**
```cypher
// GOOD: Each COUNT{} runs independently
MATCH (s:Station)
WHERE count{(s)-[:BAKERLOO]-()} > 0
RETURN s.name, count{(s)-[:BAKERLOO]-()} as connections

// AVOID: Creates cross product
MATCH (s:Station), ()-[r:BAKERLOO]->()
RETURN count(s), count(r)
```

## Common Modifications

### Adding New Tube Lines

To add support for additional tube lines, simply add rows to `London_tube_lines.csv` with the new line name. The notebook dynamically creates relationship types from the `Tube_Line` column.

### Changing Delta Lake Location

Update the widgets in the notebook:
```python
dbutils.widgets.text("catalog_name", "your_catalog", "Catalog Name")
dbutils.widgets.text("schema_name", "your_schema", "Schema Name")
dbutils.widgets.text("volume_name", "your_volume", "Volume Name")
```

### Changing Neo4j Connection

Update the Neo4j widgets:
```python
dbutils.widgets.text("neo4j_url", "bolt://your-host:7687", "Neo4j URL")
dbutils.widgets.text("neo4j_database", "neo4j", "Neo4j Database")
```

And ensure Databricks Secrets are configured:
```bash
databricks secrets create-scope neo4j
databricks secrets put-secret neo4j password
```

## Troubleshooting

### Connection Issues

**"Access mode must be Dedicated (Single user)"**
- The Neo4j Spark Connector requires Dedicated access mode
- Shared access mode is not supported
- Update cluster configuration to use Dedicated mode

**"Connection refused"**
- Verify Neo4j is running
- Check firewall allows port 7687
- Confirm URL format: `bolt://host:7687` or `neo4j+s://instance.databases.neo4j.io:7687`

**"Authentication failed"**
- Verify Databricks Secrets scope exists: `databricks secrets list-scopes`
- Check password is set: `databricks secrets list-secrets neo4j`

### File Issues

**"File not found"**
- Verify Unity Catalog volume path: `/Volumes/{catalog}/{schema}/{volume}`
- Confirm CSV files are uploaded to the volume
- Use `dbutils.fs.ls()` to list volume contents

### Data Issues

**"Relationship creation failed"**
- Ensure Station nodes exist before creating relationships (run Parts 1-2 first)
- Verify station names match exactly between CSVs (case-sensitive, watch for trailing spaces)
- Check Delta tables have correct data: `spark.table("london_catalog.london_schema.london_stations").show()`

### Notebook Format Issues

**CRITICAL: Databricks notebook formatting requirements**

Databricks notebooks must be properly structured Jupyter notebook JSON files (.ipynb). Common issues:

**"Notebook won't open in Databricks"**
- The notebook file contains raw JSON as text in a single cell instead of being parsed as multiple cells
- This happens when a notebook is pasted or imported incorrectly
- Databricks sees the entire JSON structure as plain text content rather than a multi-cell notebook

**How to fix:**
1. **Never** copy/paste raw .ipynb JSON content into Databricks
2. **Always** use Databricks "Import" feature (File → Import) for .ipynb files
3. When creating notebooks programmatically, use the Databricks-native format shown below

**Databricks Notebook Format (Required)**

Databricks notebooks require specific metadata that standard Jupyter notebooks don't have. Here's the structure that works in Databricks:

```python
import uuid

# Databricks-native notebook structure
notebook = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": 0,
            "metadata": {
                "application/vnd.databricks.v1+cell": {
                    "cellMetadata": {},
                    "inputWidgets": {},
                    "nuid": str(uuid.uuid4()),
                    "showTitle": False,
                    "tableResultSettingsMap": {},
                    "title": ""
                }
            },
            "outputs": [],
            "source": ["print('Hello')"]
        },
        {
            "cell_type": "markdown",
            "metadata": {
                "application/vnd.databricks.v1+cell": {
                    "cellMetadata": {},
                    "inputWidgets": {},
                    "nuid": str(uuid.uuid4()),
                    "showTitle": False,
                    "tableResultSettingsMap": {},
                    "title": ""
                }
            },
            "source": ["# Markdown cell"]
        }
    ],
    "metadata": {
        "application/vnd.databricks.v1+notebook": {
            "computePreferences": None,
            "dashboards": [],
            "environmentMetadata": None,
            "inputWidgetPreferences": None,
            "language": "python",
            "notebookMetadata": {
                "pythonIndentUnit": 4
            },
            "notebookName": "my_notebook",
            "widgets": {}
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open('notebook.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)
```

**Required metadata fields:**

**Notebook level:**
- `application/vnd.databricks.v1+notebook`: Container for Databricks-specific notebook settings
  - `language`: "python"
  - `notebookMetadata`: `{"pythonIndentUnit": 4}`
  - `notebookName`: Filename without extension
  - `widgets`: `{}` (widget configuration)
  - `computePreferences`, `dashboards`, `environmentMetadata`, `inputWidgetPreferences`: `null` or `[]`

**Cell level (EVERY cell must have this):**
- `application/vnd.databricks.v1+cell`: Container for Databricks-specific cell settings
  - `nuid`: Unique identifier (UUID) - use `str(uuid.uuid4())`
  - `showTitle`: `false`
  - `title`: `""`
  - `cellMetadata`: `{}`
  - `inputWidgets`: `{}`
  - `tableResultSettingsMap`: `{}`

**Standard fields:**
- `execution_count`: `0` for code cells
- `language_info`: `{"name": "python"}` (no version field)
- `nbformat`: `4`
- `nbformat_minor`: `4`

## Working Approach for New Features and Changes

**CRITICAL: Always start simple and plan before coding.**

When the user requests new features or changes:

1. **Start Simple**: Begin with the simplest possible approach. Avoid over-engineering.

2. **Multiple Options**: If there are multiple ways to implement something, write a very basic list of options (2-4 bullet points each) and ask the user which approach they prefer. Do NOT assume.

3. **Proposal First, Code Later**:
   - Always write a proposal using only English requirements and descriptions
   - NO code in the proposal - only describe what needs to be done
   - Break down into clear phases

4. **Implementation Plan Structure**:
   - Each phase should have a numbered todo list
   - Last item in the plan must be: "Code review and testing"
   - Keep phases small and achievable

5. **Think Deeply**: Take extra time to think through the implications, edge cases, and simplest path forward.

6. **Afternoon-Sized Changes**: Greatly simplify proposals so they can be completed in an afternoon. This is NOT production-scale work - keep it really basic and focused.

## Reference Project

This implementation follows patterns from the [databricks-neo4j-mcp-demo](https://github.com/neo4j-partners/databricks-neo4j-mcp-demo) project, specifically the data loading patterns in `data_setup/2_upload_test_data_to_neo4j.ipynb`.

## Key Differences from GCP Dataflow

This project is a port from a GCP Dataflow pipeline with these architectural differences:

| Aspect | GCP Dataflow | This Project |
|--------|--------------|--------------|
| Configuration | JSON templates | Notebook cells with widgets |
| Data Source | BigQuery tables | Delta Lake tables |
| File Storage | GCS buckets | Unity Catalog Volumes |
| Credentials | Secret Manager or JSON | Databricks Secrets |
| Orchestration | Managed Dataflow template | Direct PySpark code |
| Transformations | Declarative JSON mappings | Imperative DataFrame operations |
| Monitoring | Dataflow console | Notebook output and Spark UI |
