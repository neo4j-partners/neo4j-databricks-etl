# Databricks to Neo4j ETL Pipeline: From Lakehouse to Knowledge Graph with Natural Language Agent

## Overview

This project demonstrates a production-ready architecture for transforming raw data into an intelligent, queryable Knowledge Graph, complete with a natural language interface. By combining the **Databricks Lakehouse** for robust data engineering with **Neo4j's** graph database capabilities, we create a pipeline that is both scalable and semantically rich.

The solution implements a complete **AI Application** stack. Raw CSV files are ingested into **Delta Lake** for governed validation, transformed into a graph structure using the high-performance **Neo4j Spark Connector**, and then exposed to end-users via a **Generative AI agent** that translates natural language questions into precise Cypher database queries. This enables users to interact with complex graph data using plain English, democratizing access to insights.

**Key Technologies:**
- **Databricks Unity Catalog:** Governed data management for files and tables, ensuring security and lineage.
- **Delta Lake:** Provides ACID transactions, schema enforcement, and time travel capabilities for data reliability.
- **PySpark:** Distributed data processing and type-safe transformations for scalable ETL.
- **Neo4j Spark Connector:** High-throughput, parallelized graph ingestion for efficient data loading into Neo4j.
- **LangChain & LLMs:** Framework for building conversational AI agents that understand natural language and generate Cypher queries.

**Dataset:** London Transport Network (302 stations, 13 tube lines, geographic/zone data).

## Setup

This section outlines all the necessary steps to prepare your Databricks environment and Neo4j database for running the ETL pipeline and the natural language agent.

### Prerequisites

Before you begin, ensure you have:
1. **Databricks workspace** with Unity Catalog enabled.
2. **Neo4j database** (Neo4j AuraDB instance recommended for ease of use, or a self-hosted instance).
3. **Neo4j Spark Connector** library installed on your Databricks cluster:
   - Maven coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
4. **Databricks Secrets** configured to securely store your Neo4j password:
   ```bash
   # Create secrets scope (if it doesn't exist)
   databricks secrets create-scope neo4j

   # Add your Neo4j password to the 'neo4j' scope under the key 'password'
   databricks secrets put-secret neo4j password
   ```

### Setup Steps

#### 1. Setup Unity Catalog Volume and Upload CSV Files

The first step is to establish a governed storage location for your raw data within Databricks Unity Catalog and then upload the London Transport CSV files.

1. Navigate to **Catalog** in the left sidebar of your Databricks workspace.
2. Click the **+ Add** button (often a plus sign `+` icon) in the top right.
3. Select **Create a catalog**.
4. In the dialog:
   - **Catalog name:** `london_catalog`
   - **Type:** Standard
   - **Storage location:** Select a default external location and name it `london_catalog`.
5. Click **Create**.
6. Navigate into the newly created `london_catalog` and create a schema:
    - **Schema name:** `london_schema`
    - **Storage location:** Select a default external location and name it `london_schema`.
7. Navigate into the `london_schema` and click **+ Add** > **Create a volume**.
    - **Volume name:** `london_transport`
    - **Storage location:** Select a default external location and name it `london_transport`.
8. Upload files from the `datasets/csv_files/london_transport/` directory (from this repository) to the created volume. The target path in Databricks will be `/Volumes/london_catalog/london_schema/london_transport`.
   - Upload `London_stations.csv` (contains 302 station records).
   - Upload `London_tube_lines.csv` (contains tube line connection records).

Your final Unity Catalog volume structure should appear similar to this:

![Final Volume](images/final_volume.png)


#### 2. Create and Configure a Databricks Cluster

A Databricks cluster is required to run the PySpark notebooks. Pay close attention to the access mode and library installations.

1. Navigate to **Compute** in your Databricks workspace.
2. Click **Create Compute**.
3. Configure the cluster with the following settings:
   - **Cluster name**: "Neo4j-London-Transport-Cluster" (or a name of your choice).
   - **Cluster mode**: Standard.
   - **Access mode**: **Dedicated (formerly: Single user)** - ⚠️ **This is REQUIRED** for the Neo4j Spark Connector to function correctly. The connector does **NOT** work in Shared or No Isolation Shared access modes.
   - **Databricks Runtime Version**: 13.3 LTS or higher (ensures Spark 3.x compatibility).
   - **Node type**: Standard_DS3_v2 (recommended 14 GB Memory, 4 Cores for this demo).
   - **Workers**: Enable "Single node" for this demonstration (sufficient for the London Transport dataset).
4. Click **Create**.

**Install required libraries on the cluster:**

Once the cluster is created and running, install the necessary libraries:

**Maven Library** (for the Neo4j Spark Connector):
- Click on your cluster's name → navigate to the **Libraries** tab.
- Click **Install New** → Select **Maven** as the library source.
- Enter the Maven coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`.
- Click **Install** and wait for the library status to show "Installed".

**PyPI Libraries** (for the Neo4j Python Driver and LangChain components):
- Click **Install New** → Select **PyPI** as the library source.
- Enter package name: `neo4j==6.0.2`. Click **Install**.
- Repeat for `langchain`, `langchain-neo4j`, `langchain-openai`.

**Important Notes on Cluster Configuration:**
- If you change the cluster access mode or install new libraries, a cluster restart might be required to ensure all dependencies are correctly loaded.


#### 3. Upload Notebooks to Databricks Workspace

Upload the provided PySpark notebooks into your Databricks workspace.

1. In Databricks, navigate to **Workspace** in the left sidebar.
2. Navigate to your user directory: **Users** > `your.email@domain.com` (this is typically your username).
3. Create a new folder for this project (e.g., `neo4j-databricks-etl`).
4. Inside that new folder, create a `notebooks` subfolder.
5. Upload the following notebooks from this repository's `notebooks/` directory to this location:
   - `load_london_transport.ipynb` (the ETL pipeline notebook)
   - `query_london_transport.ipynb` (the natural language agent notebook)

Your workspace structure should resemble this:

![Notebook Setup](images/notebook_setup.png)

**Note:** The exact appearance may vary based on other folders you've created in your workspace.

## Running the ETL Pipeline Notebook

This section guides you through executing the `load_london_transport.ipynb` notebook to ingest the London Transport data into Neo4j.

### Configure and Run `load_london_transport.ipynb`

Open the `load_london_transport.ipynb` notebook in your Databricks workspace. You will need to update the configuration widgets at the beginning of the notebook with your specific Neo4j connection details and Unity Catalog paths.

```python
# Neo4j connection details
NEO4J_URL = "bolt://localhost:7687"  # Replace with your Neo4j instance's Bolt URL
NEO4J_DB  = "neo4j"                   # Replace with your Neo4j database name (e.g., 'neo4j', 'aura')

# Unity Catalog paths based on your setup in Step 1
BASE_PATH = "/Volumes/london_catalog/london_schema/london_transport"
CATALOG = "london_catalog"
SCHEMA = "london_schema"
```

Once configured, execute all cells in the notebook sequentially. The notebook performs the following steps:
1.  **Configures Connection:** Sets up Spark session properties for Neo4j.
2.  **Tests Neo4j Connectivity:** Verifies the connection to your Neo4j instance.
3.  **Loads CSVs to Delta Lake:** Ingests raw CSV data into reliable Delta tables.
4.  **Writes Station Nodes to Neo4j:** Creates all `(:Station)` nodes in your graph.
5.  **Creates Tube Line Relationships:** Dynamically creates line-specific relationships (e.g., `[:BAKERLOO]`, `[:CENTRAL]`) between stations.
6.  **Validates Results:** Runs Cypher queries to confirm data integrity and completeness in Neo4j.

### Expected Results

Upon successful execution of the `load_london_transport.ipynb` notebook, your Neo4j database will contain:
-   **302 Station nodes:** Each `(:Station)` node will have properties like `station_id`, `name`, `latitude`, `longitude`, `zone`, and `postcode`.
-   **All tube line relationships:** Bidirectional relationships connecting stations for each of the London tube lines (e.g., Bakerloo, Central, Circle, District, etc.). These relationships adhere to the best practice of using **line-specific relationship types** (e.g., `:BAKERLOO`, `:CENTRAL`).
-   **Delta Lake tables:** Managed Delta tables for `london_stations` and `london_tube_lines` will exist in your Unity Catalog.

**Note:** The notebook includes comprehensive validation queries in its final step (Step 15) to help you verify the loaded data.

## Exploring and Querying the Data

Once the London Transport Network data is loaded into Neo4j, you have powerful options for exploring and querying the graph, from visual tools to a natural language interface.

### Visual Exploration in Neo4j Aura

For interactive visual analysis and understanding the graph structure, Neo4j Aura's built-in **Graph Explorer** is invaluable.

**Guide:** For detailed step-by-step instructions on visual exploration, refer to [EXPLORING_DATA.md](EXPLORING_DATA.md).

**Quick Start:**
1.  Log in to your Neo4j Aura console.
2.  Navigate to the **Tools** section and select **Explore**.
3.  Connect to your Neo4j AuraDB instance.
4.  In the search bar, try a simple pattern like `Station — (any) — Station` to see an interactive visualization of connected stations.

**Key Features of Visual Exploration:**
-   **Interactive Graph Visualization:** Visually inspect nodes and relationships, with different tube lines (relationship types) often color-coded for clarity.
-   **Filtering & Search:** Easily filter stations by properties (zone, name, postcode) or search for specific stations.
-   **Pathfinding:** Visually trace shortest paths between stations.
-   **Network Analysis:** Identify major interchange stations or examine connectivity patterns.

## Natural Language Query Agent (Text-to-Cypher)

This section details how to set up and use the natural language agent, implemented in `query_london_transport.ipynb`, to interact with your Neo4j graph using plain English questions. The primary goal of this agent is to democratize access to the rich insights stored within the graph by removing the technical barrier of learning Cypher, Neo4j's native query language. The agent leverages state-of-the-art Large Language Models (LLMs) served via Databricks Foundation Models, orchestrating a complex process to translate a user's natural language intent into precise Cypher queries, execute them against the Neo4j database, and then present the results back to the user in an easily understandable English format.

### Setup: Databricks Foundation Model Serving Endpoint

The natural language agent relies on a Large Language Model (LLM) to perform the text-to-Cypher translation. We use **Databricks Foundation Model Serving** to host this LLM securely and scalably.

#### 1. Navigate to Serving Endpoints

1.  In your Databricks workspace, click on **Serving** in the left sidebar (under the AI/ML section).
2.  Click **Create serving endpoint** to set up a new one, or select an existing endpoint if available.

#### 2. Configure the Endpoint

When creating your serving endpoint, configure it as follows:
-   **Endpoint Name:** Provide a descriptive name, e.g., `databricks-claude-sonnet-4-5` (or your preferred model's name).
-   **Served Entity:** From the "Foundation Models" tab, select **Claude Sonnet 4.5** or another suitable code-generation-capable LLM.
-   **Description:** Add a brief description, e.g., "Claude Sonnet 4.5 for text-to-Cypher generation."

#### 3. Get Your Endpoint URL

Once the endpoint is successfully deployed and its status shows a green checkmark "Ready":

1.  Copy the **full endpoint URL** from the top of the endpoint details page.
    -   Example Format: `https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints/databricks-claude-sonnet-4-5/invocations`
2.  From this, extract the **base URL** (the part before `/invocations`):
    -   Example Format: `https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints`

#### 4. Configure `query_london_transport.ipynb`

Open the `query_london_transport.ipynb` notebook in your Databricks workspace. You will need to update its configuration widgets to point to your newly created LLM serving endpoint.

```python
# Databricks Foundation Model Serving Endpoint details
DB_MODEL_ENDPOINT_URL = "https://adb-XXXXXXXXX.X.azuredatabricks.net/serving-endpoints" # Your base URL
DB_MODEL_NAME = "databricks-claude-sonnet-4-5" # Your endpoint name
```
The notebook is designed to automatically retrieve your Databricks token from the current notebook context for authentication with the serving endpoint.

### Requirements for the Agent Notebook

To run the natural language agent successfully, ensure these are met:
1.  **London Transport data loaded:** The `load_london_transport.ipynb` notebook must have been run successfully to populate your Neo4j graph.
2.  **Python libraries installed** on the Databricks cluster (as described in Setup Step 2):
    -   `langchain`
    -   `langchain-neo4j`
    -   `langchain-openai`
    -   `neo4j`
3.  **Databricks Foundation Model serving endpoint** configured and running (as described above).

### Usage of the Natural Language Agent

The `query_london_transport.ipynb` notebook provides an interactive environment to test the text-to-Cypher agent.

1.  Run all cells in the initial configuration section of the notebook.
2.  Verify that the Neo4j connection is successful and that London Transport data is detected in the graph.
3.  Proceed to the interactive cells, where you can input your questions.
4.  Try the provided example questions or formulate your own. The agent will display the generated Cypher query (due to verbose mode) before executing it and presenting the natural language result.

**Example questions you can ask:**
-   "How many stations are in zone 1?"
-   "Which stations does the Bakerloo line connect?"
-   "What tube lines go through Baker Street?"
-   "Which stations have the most connections?"
-   "Find a path between King's Cross and Victoria"
-   "Show me stations to avoid during rush hour"

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
Raw CSV files (Unity Catalog Volume) → Delta Lake Tables (Unity Catalog) → PySpark (Transform) → Neo4j (Graph Database) → LangChain (Natural Language Agent) → User
```

### Delta Lake Tables

**Stations Table:**
- Columns: `station_id` (Integer), `name` (String), `latitude` (Double), `longitude` (Double), `zone` (String), `postcode` (String).
- Row count: 302.

**Tube Lines Table:**
- Columns: `Tube_Line` (String), `From_Station` (String), `To_Station` (String).
- Row count: Approximately 300 connections.

### Neo4j Graph Model

**Nodes:**
-   `(:Station)` label with properties: `station_id`, `name`, `latitude`, `longitude`, `zone`, `postcode`.

**Relationships:**
-   **Line-specific relationship types** for each tube line. These are inherently bidirectional due to the loading process.
-   **Examples:** `:BAKERLOO`, `:CENTRAL`, `:CIRCLE`, `:DISTRICT`, `:HAMMERSMITH_AND_CITY`, `:JUBILEE`, `:METROPOLITAN`, `:NORTHERN`, `:PICCADILLY`, `:VICTORIA`, `:WATERLOO_AND_CITY`.
-   **Format:** `(:Station)-[:TUBE_LINE]->(:Station)`.
-   **Neo4j Best Practice:** Using distinct relationship types (not properties on a generic relationship) offers superior query performance and clarity by leveraging Neo4j's native indexing of relationship types.

### Key Features

-   **Intermediate Delta Lake storage:** Ensures data quality, ACID compliance, and schema enforcement before graph ingestion.
-   **Type-safe transformations:** Implemented using PySpark to maintain data integrity throughout the ETL process.
-   **Line-specific relationship types:** A best practice in Neo4j modeling that transforms data values into schema elements for performance and semantic clarity.
-   **Batch relationship creation:** Utilizes the Neo4j Spark Connector for efficient, parallelized loading of graph data.
-   **Comprehensive validation queries:** Built into the `load_london_transport.ipynb` notebook to verify successful graph population.
-   **Index creation:** Automated indexing on key node properties (e.g., `station_id`, `name`) for optimized query performance in Neo4j.

## Troubleshooting

### Connection Issues

**Error:** `Connection refused`
-   **Verify Neo4j is running:** Ensure your Neo4j instance is active and accessible.
-   **Check firewall:** Confirm that network firewalls allow outgoing connections from your Databricks cluster to Neo4j's Bolt port (default 7687).
-   **Confirm URL format:** Double-check that your Neo4j URL is correctly formatted (e.g., `bolt://your_host:7687` or `neo4j+s://your_aura_instance.databases.neo4j.io:7687`).

**Error:** `Authentication failed`
-   **Verify Databricks Secrets:** Ensure your `neo4j` scope and `password` key are correctly configured in Databricks Secrets.
-   **Check credentials:** Confirm the username and password stored in Databricks Secrets match your Neo4j database credentials.

### File Issues

**Error:** `File not found`
-   **Verify Unity Catalog volume path:** Ensure the `BASE_PATH` in your notebooks accurately reflects the Unity Catalog volume path (e.g., `/Volumes/london_catalog/london_schema/london_transport`).
-   **Confirm CSV files uploaded:** Double-check that `London_stations.csv` and `London_tube_lines.csv` have been successfully uploaded to the specified Unity Catalog volume.
-   **Check file permissions:** Ensure your Databricks cluster user has appropriate read permissions on the Unity Catalog volume.

### Data Issues

**Error:** `Relationship creation failed`
-   **Node existence:** Verify that `(:Station)` nodes corresponding to the `From_Station` and `To_Station` names exist in Neo4j *before* attempting to create relationships.
-   **Data consistency:** Ensure station names in `London_tube_lines.csv` exactly match the `name` property of `(:Station)` nodes. Check for subtle differences like capitalization, extra spaces, or special characters.

## Performance Tips

1.  **Batch relationship creation:** For large datasets, process relationships in manageable chunks to optimize transaction size and network overhead.
2.  **Create indexes first:** Always create indexes on node properties (e.g., `station_id`, `name`) before loading relationships. This significantly speeds up the node lookup required during relationship creation.
3.  **Use Delta Lake caching:** If you perform multiple reads from the same Delta tables within your Spark job, consider caching them (`spark.table(TABLE_NAME).cache()`) to improve performance.
4.  **Monitor Spark UI:** Regularly check the Spark UI for your cluster during job execution. Look for signs of data skew, excessive shuffle operations, or memory issues that might be bottlenecks.

## License

Sample data from Transport for London. Educational purposes only.

---

**Built with:** Databricks | Delta Lake | PySpark | Neo4j Spark Connector | LangChain
