# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository demonstrates ETL from Databricks to Neo4j using Delta Lake and PySpark. It loads the London Transport Network dataset (302 stations, multiple tube lines) from CSV files into a Neo4j graph database.

**Key Architecture:** CSV → Unity Catalog Volume → Delta Lake Tables → PySpark → Neo4j

## Core Commands

**Note:** This is a Databricks notebook-based project. There are no local build, test, or lint commands. All execution happens in Databricks workspace.

### Databricks Execution

Notebooks live in `labs/` and must be run in order on a Databricks cluster with:
- **Access mode:** Dedicated (required for Neo4j Spark Connector)
- **Runtime:** 13.3 LTS or higher
- **Maven library:** `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
- **PyPI library:** `neo4j==6.0.2`

Run order:
1. `0 - Required Setup.py` - Creates catalog, schema, volume, copies data, stores Neo4j secrets
2. `1 - Load London Transport.py` - ETL: CSV -> Delta Lake -> Neo4j
3. `2 - Query London Transport.py` - Text-to-Cypher natural language queries

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

**Configuration:** Centralized in `labs/Includes/config.yaml`. The setup notebook (`0 - Required Setup.py`) stores Neo4j credentials in a Databricks secret scope. Subsequent notebooks load credentials from secrets via `config.yaml`.

**Shared Libraries:** Reusable logic lives in `labs/Includes/_lib/`:
- `setup_orchestrator.py` - Catalog/schema/volume creation, data copying, secret management
- `london_transport_import.py` - Full ETL pipeline (CSV -> Delta -> Neo4j)

Notebooks import shared libraries via `%run ./Includes/_lib/module_name`.

**Neo4j Connection (from secrets):**
```python
scope = config["secrets"]["scope_name"]
NEO4J_URL = dbutils.secrets.get(scope=scope, key="url")
NEO4J_USER = dbutils.secrets.get(scope=scope, key="username")
NEO4J_PASS = dbutils.secrets.get(scope=scope, key="password")
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
├── images/                                # Screenshots and diagrams
├── agents/                                # Standalone Python CLI agent
│   └── query_neo4j.py
└── labs/                                  # Self-contained labs (run in order)
    ├── 0 - Required Setup.py              # Environment setup notebook
    ├── 1 - Load London Transport.py       # ETL notebook
    ├── 2 - Query London Transport.py      # Text-to-Cypher notebook
    └── Includes/
        ├── config.yaml                    # Centralized configuration
        ├── _lib/
        │   ├── __init__.py
        │   ├── setup_orchestrator.py      # Setup functions
        │   └── london_transport_import.py # ETL functions
        └── data/
            └── csv/
                ├── London_stations.csv    # 302 stations
                └── London_tube_lines.csv  # Tube connections
```

## Labs Structure

### Notebook Format

All notebooks use Databricks `.py` notebook format (not `.ipynb`):
- `# Databricks notebook source` header
- `# COMMAND ----------` cell separators
- `# MAGIC %md` for markdown cells
- `# MAGIC %run ./path` for importing shared libraries

### 0 - Required Setup

Creates the complete environment in 4 steps:
1. Create catalog (`london_transport_{username}`), schema, and volume
2. Copy CSV data files from `Includes/data/` to the volume
3. Store Neo4j credentials as Databricks secrets
4. Verify Neo4j connectivity

### 1 - Load London Transport

ETL pipeline orchestrated by `run_full_import()` from `london_transport_import.py`:
1. Load config from secrets
2. Clear Neo4j database
3. Load CSVs to Delta Lake tables
4. Write Station nodes to Neo4j
5. Create all tube line relationships (bidirectional, line-specific types)
6. Validate the imported graph

### 2 - Query London Transport

Text-to-Cypher natural language interface:
1. Load Neo4j credentials from secrets (via config.yaml)
2. Connect to Neo4j and validate data
3. Configure LLM (Databricks Foundation Model, temperature 0.0)
4. Create Cypher generation chain with specialized prompt
5. Interactive `ask_question()` interface with example questions

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

Add rows to `labs/Includes/data/csv/London_tube_lines.csv` with the new line name. The import dynamically creates relationship types from the `Tube_Line` column.

### Changing Catalog/Schema Names

Edit `labs/Includes/config.yaml`:
```yaml
catalog:
  prefix: "your_prefix"
  schema_name: "your_schema"
  volume_name: "your_volume"
```

### Changing Neo4j Connection

Re-run `0 - Required Setup.py` with updated widget values. Credentials are stored in the secret scope defined in `config.yaml`.

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
- Verify setup notebook ran successfully (check volume path in secrets)
- CSV files should be in `/Volumes/{catalog}/{schema}/{volume}/csv/`
- Use `dbutils.fs.ls()` to list volume contents

### Data Issues

**"Relationship creation failed"**
- Run notebooks in order: Setup -> Load -> Query
- Verify station names match exactly between CSVs (case-sensitive)

### Notebook Format

This project uses Databricks `.py` notebook format (not `.ipynb`). The `.py` format:
- Uses `# COMMAND ----------` as cell separators
- Uses `# MAGIC %md` for markdown cells
- Uses `# MAGIC %run` for imports
- Imports directly into Databricks via the workspace file system

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
