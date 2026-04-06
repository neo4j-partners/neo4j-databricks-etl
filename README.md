[![Databricks](https://img.shields.io/badge/Databricks-Solution_Accelerator-FF3621?style=for-the-badge&logo=databricks)](https://databricks.com)
[![Unity Catalog](https://img.shields.io/badge/Unity_Catalog-Enabled-00A1C9?style=for-the-badge)](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
[![Neo4j](https://img.shields.io/badge/Neo4j-Partner-4581C3?style=for-the-badge&logo=neo4j)](https://neo4j.com/partners/databricks/)

# London Transport ETL Workshop: From Lakehouse to Knowledge Graph

## Overview

This workshop demonstrates a production-ready architecture for transforming raw data into an intelligent, queryable Knowledge Graph, complete with a natural language interface. By combining the **Databricks Lakehouse** for robust data engineering with **Neo4j's** graph database capabilities, we create a pipeline that is both scalable and semantically rich.

The solution implements a complete **AI Application** stack. Raw CSV files are ingested into **Delta Lake** for governed validation, transformed into a graph structure using the high-performance **Neo4j Spark Connector**, and then exposed to end-users via a **Generative AI agent** that translates natural language questions into precise Cypher database queries.

**Key Technologies:**
- **Databricks Unity Catalog:** Governed data management for files and tables
- **Delta Lake:** ACID transactions, schema enforcement, and time travel
- **PySpark:** Distributed data processing and type-safe transformations
- **Neo4j Spark Connector:** High-throughput, parallelized graph ingestion
- **LangChain & LLMs:** Text-to-Cypher natural language query interface

**Dataset:** London Transport Network (302 stations, 13 tube lines, geographic/zone data).

## Architecture

```
CSV Files (Includes/data/)
    ↓  (0 - Required Setup)
Unity Catalog Volume
    ↓  (1 - Load London Transport)
Delta Lake Tables → Neo4j Graph Database
    ↓  (2 - Query London Transport)
Natural Language → Cypher → Results
```

## Prerequisites

Before you begin, ensure you have:

1. **Databricks workspace** with Unity Catalog enabled
2. **Neo4j database** (Neo4j AuraDB recommended, or self-hosted)
3. **Databricks cluster** configured:
   - **Access mode:** Dedicated (required for Neo4j Spark Connector)
   - **Runtime:** 13.3 LTS or higher
   - **Maven library:** `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
   - **PyPI library:** `neo4j==6.0.2`

## Quick Start

### 1. Import Labs to Databricks

Upload the entire `labs/` directory to your Databricks workspace:

1. Navigate to **Workspace** > your user directory
2. Create a folder (e.g., `london-transport-etl`)
3. Import/upload the `labs/` directory contents into that folder

### 2. Run the Notebooks in Order

**Lab 0 - Required Setup** (~5 minutes)
- Fill in Neo4j connection widgets (URL, username, password)
- Run all cells
- Creates catalog, schema, volume, copies data, stores secrets

**Lab 1 - Load London Transport** (~5-10 minutes)
- Run all cells (no configuration needed - reads from secrets)
- Loads CSV → Delta Lake → Neo4j
- Creates 302 Station nodes and all tube line relationships

**Lab 2 - Query London Transport** (~10 minutes)
- Fill in Databricks endpoint widget
- Ask questions in plain English: "How many stations in zone 1?"

## Project Structure

```
neo4j-databricks-etl/
├── README.md
├── CLAUDE.md
├── EXPLORING_DATA.md              # Visual exploration guide for Neo4j Aura
├── images/                        # Screenshots and diagrams
├── agents/                        # Standalone Python CLI agent
│   └── query_neo4j.py
└── labs/                          # Self-contained workshop labs
    ├── 0 - Required Setup.py      # Environment setup
    ├── 1 - Load London Transport.py   # ETL pipeline
    ├── 2 - Query London Transport.py  # Natural language queries
    └── Includes/
        ├── config.yaml            # Centralized configuration
        ├── _lib/
        │   ├── setup_orchestrator.py      # Setup functions
        │   └── london_transport_import.py # ETL functions
        └── data/
            └── csv/
                ├── London_stations.csv    # 302 stations
                └── London_tube_lines.csv  # Tube connections
```

## Neo4j Graph Model

**Nodes:**
- `(:Station)` with properties: `station_id`, `name`, `latitude`, `longitude`, `zone`, `postcode`

**Relationships:** Line-specific types for each tube line (bidirectional):
- `:BAKERLOO`, `:CENTRAL`, `:CIRCLE`, `:DISTRICT`, `:HAMMERSMITH_AND_CITY`, `:JUBILEE`, `:METROPOLITAN`, `:NORTHERN`, `:PICCADILLY`, `:VICTORIA`, `:WATERLOO_AND_CITY`, etc.

**Design Decision:** Using relationship **types** (not properties) for tube lines provides better query performance, clearer semantics, and better visualization in Neo4j Browser.

## Configuration

All configuration is centralized in `labs/Includes/config.yaml`:

```yaml
catalog:
  prefix: "london_transport"    # Catalog: {prefix}_{username}
  schema_name: "london_data"
  volume_name: "source_files"

secrets:
  scope_name: "neo4j-london"   # Databricks secret scope
```

Neo4j credentials are stored as Databricks secrets by the setup notebook and read by subsequent notebooks automatically.

## Exploring the Graph

### Neo4j Browser

After loading data, try these Cypher queries:

```cypher
-- Schema visualization
CALL db.schema.visualization()

-- Top 10 busiest stations
MATCH (s:Station)
RETURN s.name AS station, count{(s)-[]-()} AS connections
ORDER BY connections DESC
LIMIT 10

-- Shortest path between stations
MATCH path = shortestPath(
  (from:Station {name: "King's Cross St. Pancras"})-[*..5]-(to:Station {name: 'Victoria'})
)
RETURN path
```

### Visual Exploration

See [EXPLORING_DATA.md](EXPLORING_DATA.md) for a guide to exploring the graph visually in Neo4j Aura.

## Troubleshooting

**"Access mode must be Dedicated"**
- The Neo4j Spark Connector requires Dedicated access mode on the cluster

**"Connection refused"**
- Verify Neo4j is running and URL is correct
- Check firewall allows port 7687

**"File not found"**
- Re-run `0 - Required Setup.py` to ensure data files are copied to the volume

## Project Support

Please note the code in this project is provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects. The source in this project is provided subject to the Databricks [License](./LICENSE.md). All included or referenced third party libraries are subject to the licenses set forth below.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support.

## Third-Party Package Licenses

| library | description | license | source |
|---------|-------------|---------|--------|
| neo4j-connector-apache-spark | Neo4j Spark Connector | Apache 2.0 | https://github.com/neo4j/neo4j-spark-connector |
| langchain-neo4j | Neo4j LangChain integration | MIT | https://github.com/langchain-ai/langchain-neo4j |
| langchain-openai | OpenAI LangChain integration | MIT | https://github.com/langchain-ai/langchain |
| langchain-core | LangChain core primitives | MIT | https://github.com/langchain-ai/langchain |
| pyyaml | YAML parsing | MIT | https://github.com/yaml/pyyaml |
| python-dotenv | Environment variable loading | BSD-3 | https://github.com/theskumar/python-dotenv |

Sample data from Transport for London. Educational purposes only.

&copy; 2026 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the [Databricks License](https://databricks.com/db-license-source). All included or referenced third party libraries are subject to the licenses set forth above.
