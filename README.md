# Databricks to Neo4j ETL Pipeline

Load London Transport Network data from Databricks into Neo4j using Delta Lake and PySpark.

## Overview

This project demonstrates how to ETL data from CSV files in Databricks Unity Catalog into Neo4j graph database using:
- **Delta Lake** for intermediate data storage
- **PySpark** for data transformations
- **Neo4j Spark Connector** for loading graph data

**Dataset:** London Transport Network with 302 stations and tube line connections

## Quick Start

### Prerequisites

1. **Databricks workspace** with Unity Catalog enabled
2. **Neo4j database** 
3. **Neo4j Spark Connector** library installed on cluster:
   - Maven coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
4. **Databricks Secrets** configured:
   ```bash
   # Create secrets scope
   databricks secrets create-scope neo4j

   # Add credentials
   databricks secrets put-secret neo4j password
   ```

### Setup Steps

#### 1. Setup Unity Catalog Volume Using the UI and Upload CSV Files

1. Navigate to **Catalog** in the left sidebar
2. Click the **+** button in the top right
3. Select **Create a catalog**
4. In the dialog:
   - **Catalog name:** `london_catalog`
   - **Type:** Standard
   - **Storage location:** Select default external location and name it `london_catalog`
5. Click **Create**
6. Navigate to the catalog and create a schema:
    - **Schema name:** `london_schema`
    - **Storage location:** Select default external location and name it `london_schema`
7. Navigate to the schema and click **+** > **Create a volume**
    - **Volume name:** `datasets`
    - **Storage location:** Select default external location and name it `datasets`
9. Upload files from `datasets/csv_files/london_transport/` to the volume at `/Volumes/london_catalog/london_schema/london_transport`:
   - `London_stations.csv` (302 stations)
   - `London_tube_lines.csv` (tube line connections)

Your final volume should look like this:

![Final Volume](images/final_volume.png)


#### 2. Create a Databricks Cluster

1. Navigate to **Compute** in your Databricks workspace
2. Click **Create Compute**
3. Configure the cluster with:
   - **Cluster name**: "Neo4j-London-Transport-Cluster" (or your preferred name)
   - **Cluster mode**: Standard
   - **Access mode**: **Dedicated (formerly: Single user)** - ⚠️ **REQUIRED** for Neo4j Spark Connector
   - **Databricks Runtime**: 13.3 LTS or higher (Spark 3.x)
   - **Node type**: Standard_DS3_v2 (14 GB Memory, 4 Cores)
   - **Workers**: Enable "Single node" (sufficient for this demo with 302 stations)
4. Click **Create**

**Install required libraries:**

After the cluster is created, install the following libraries:

**Maven Library** (Neo4j Spark Connector):
- Click on your cluster → **Libraries** tab
- Click **Install New** → Select **Maven**
- Enter coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
- Click **Install** and wait for status: "Installed"

**PyPI Library** (Neo4j Python Driver):
- Click **Install New** → Select **PyPI**
- Enter package name: `neo4j==6.0.2`
- Click **Install** and wait for status: "Installed"

**Important Notes:**
- ⚠️ The Neo4j Spark Connector does **NOT** work in Shared access mode
- Restart the cluster if needed to ensure libraries are loaded


#### 3. Upload Notebook to Databricks

1. In Databricks, navigate to **Workspace** in the left sidebar
2. Navigate to **Users** > **your.email@domain.com** (your username)
3. Create a new folder (e.g., `neo4j-databricks-etl`)
4. Inside that folder, create a `notebooks` subfolder
5. Upload `notebooks/load_london_transport.ipynb` to this location

Your workspace structure should look like this:

![Notebook Setup](images/notebook_setup.png)

**Note:** Your workspace may look different depending on other folders you've created.

#### 4. Configure Notebook

Open the uploaded notebook and update the widgets with your values:

```python
# Neo4j connection
NEO4J_URL = "bolt://localhost:7687"  # Your Neo4j URL
NEO4J_DB  = "neo4j"                   # Your database name

# Unity Catalog paths
BASE_PATH = "/Volumes/london_catalog/london_schema/london_transport"
CATALOG = "london_catalog"
SCHEMA = "london_schema"
```

#### 5. Run Notebook

Execute all cells in order:
1. Configure connection
2. Test Neo4j connectivity
3. Load CSVs to Delta Lake
4. Write Station nodes to Neo4j
5. Create tube line relationships
6. Validate results

### Expected Results

After successful execution:
- **302 Station nodes** in Neo4j with properties: name, zone, postcode, coordinates
- **All tube line relationships** connecting stations bidirectionally (Bakerloo, Central, Circle, District, etc.)
- **Line-specific relationship types** for each tube line (e.g., :BAKERLOO, :CENTRAL, :CIRCLE)
- **Delta Lake tables** for stations and tube lines

**Note:** All validation queries are included in Step 15 of the notebook.

## Exploring and Querying the Data

### Visual Exploration in Neo4j Aura

After loading the data, you can visually explore the London Transport Network graph:

**Guide:** See [EXPLORING_DATA.md](EXPLORING_DATA.md) for step-by-step instructions

**Quick Start:**
1. Go to Neo4j Aura Console → Tools → **Explore**
2. Connect to your instance
3. Search pattern: `Station — (any) — Station`
4. View the interactive graph visualization

**Features:**
- Visual graph exploration with color-coded tube lines
- Filter by station properties (zone, name, postcode)
- Find shortest paths between stations
- Identify major interchange stations
- Custom perspectives and layouts

---

### Text-to-Cypher Agent (NEW)

After loading the data, you can query it using natural language with the **Text-to-Cypher Agent** notebook:

**Notebook:** `notebooks/query_london_transport.ipynb`

**What it does:**
- Ask questions in plain English about the London Transport Network
- Automatically generates and executes Cypher queries
- Displays results directly

**Example questions:**
- "How many stations are in zone 1?"
- "Which stations does the Bakerloo line connect?"
- "What tube lines go through Baker Street?"
- "Which stations have the most connections?"
- "Find a path between King's Cross and Victoria"
- "Show me stations to avoid during rush hour"

---

### Setup: Databricks Serving Endpoint

Before using the Text-to-Cypher agent, set up a Databricks Foundation Model serving endpoint:

#### 1. Navigate to Serving Endpoints

1. In your Databricks workspace, click on **Serving** in the left sidebar (under AI/ML section)
2. Click **Create serving endpoint** or use an existing endpoint

#### 2. Configure the Endpoint

**Endpoint Configuration:**
- **Name:** `databricks-claude-sonnet-4-5` (or your preferred model)
- **Served Entity:** Select **Claude Sonnet 4.5** from Foundation Models or your preferred model
- **Description:** Claude Sonnet 4.5 for text-to-Cypher generation


#### 3. Get Your Endpoint URL

Once the endpoint is ready (status shows green checkmark "Ready"):

1. Copy the **endpoint URL** from the top of the page
   - Format: `https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints/databricks-claude-sonnet-4-5/invocations`
2. Note the **base URL** (without `/invocations`):
   - Format: `https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints`

#### 4. Configure the Notebook

Open `notebooks/query_london_transport.ipynb` and update the widgets:

1. **Databricks Endpoint:** Enter your base URL
   ```
   https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints
   ```

2. **Model Name:** Enter your endpoint name
   ```
   databricks-claude-sonnet-4-5
   ```

The notebook will automatically retrieve your Databricks token from the notebook context.

---

### Requirements

1. **London Transport data loaded** - Run `load_london_transport.ipynb` first
2. **Python libraries installed** on cluster:
   - `langchain`
   - `langchain-neo4j`
   - `langchain-openai`
   - `neo4j`
3. **Databricks Foundation Model endpoint** configured (see setup above)

---

### Usage

1. Run all cells in the configuration section
2. Verify Neo4j connection and data exists
3. Try the example questions or modify the interactive cell
4. Review generated Cypher queries in the output (verbose mode enabled)

## Project Structure

```
neo4j-databricks-etl/
├── README.md                              # This file
├── CLAUDE.md                              # Claude Code guidance
├── EXPLORING_DATA.md                      # Visual exploration guide (NEW)
├── DBX_PORT_v2.md                         # Implementation plan and status
├── TEXT2CYPHER_PROPOSAL.md                # Text-to-Cypher agent proposal
├── datasets/
│   ├── csv_files/
│   │   └── london_transport/
│   │       ├── London_stations.csv        # 302 stations
│   │       └── London_tube_lines.csv      # Tube connections
│   └── README.md                          # Dataset documentation
├── images/
│   ├── aura_explore.png                   # Aura Explore interface
│   ├── search_stations.png                # Search pattern example
│   └── all_stations_graph.png             # Graph visualization
└── notebooks/
    ├── load_london_transport.ipynb        # ETL notebook
    └── query_london_transport.ipynb       # Text-to-Cypher agent (NEW)
```

## Implementation Details

### Data Flow

```
CSV files → Unity Catalog Volume → Delta Lake tables → PySpark → Neo4j
```

### Delta Lake Tables

**Stations Table:**
- Columns: station_id, name, latitude, longitude, zone, postcode
- Row count: 302

**Tube Lines Table:**
- Columns: Tube_Line, From_Station, To_Station
- Row count: ~300 connections

### Neo4j Graph Model

**Nodes:**
- `(:Station)` with properties: station_id, name, latitude, longitude, zone, postcode

**Relationships:**
- Line-specific relationship types for each tube line (bidirectional)
- Examples: `:BAKERLOO`, `:CENTRAL`, `:CIRCLE`, `:DISTRICT`, `:HAMMERSMITH_AND_CITY`, `:JUBILEE`, `:METROPOLITAN`, `:NORTHERN`, `:PICCADILLY`, `:VICTORIA`, `:WATERLOO_AND_CITY`
- Format: `(:Station)-[:TUBE_LINE]->(:Station)`
- **Neo4j Best Practice:** Uses relationship types (not properties) for better performance and query clarity

### Key Features

- **Intermediate Delta Lake storage** for data validation
- **Type-safe transformations** using PySpark
- **Line-specific relationship types** - creates distinct relationship types for each tube line (following Neo4j best practices)
- **Batch relationship creation** using Neo4j Spark Connector
- **Comprehensive validation queries** built into the notebook
- **Index creation** for performance

## Troubleshooting

### Connection Issues

**Error:** `Connection refused`
- Verify Neo4j is running
- Check firewall allows port 7687
- Confirm URL format: `bolt://host:7687` or `neo4j+s://instance.databases.neo4j.io:7687`

**Error:** `Authentication failed`
- Verify Databricks Secrets are configured correctly
- Check username/password in Databricks Secrets scope

### File Issues

**Error:** `File not found`
- Verify Unity Catalog volume path: `/Volumes/catalog/schema/volume`
- Confirm CSV files are uploaded to volume
- Check file permissions

### Data Issues

**Error:** `Relationship creation failed`
- Ensure Station nodes exist before creating relationships
- Verify station names match exactly between CSVs
- Check for trailing spaces or case mismatches

## Performance Tips

1. **Batch relationship creation** - Process in chunks for large datasets
2. **Create indexes first** - Before loading relationships
3. **Use Delta Lake caching** - Cache tables used multiple times
4. **Monitor Spark UI** - Check for data skew or memory issues

## License

Sample data from Transport for London. Educational purposes only.

---

**Built with:** Databricks | Delta Lake | PySpark | Neo4j Spark Connector
