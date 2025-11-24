# From Raw Data to Intelligent Knowledge Graphs with Natural Language Queries

## Introduction

The journey from raw data to an intelligent, conversational knowledge graph represents a shift from rigid, pre-defined dashboards to flexible, natural language interrogation. This post details the engineering implementation of a system that combines the **Databricks Lakehouse** architecture with **Neo4j's** graph capabilities.

The data is then made broadly accessible by creating a text-to-Cypher interface powered by **LangChain** and Large Language Models (LLMs). Using London's public transport network as our dataset, we will examine the code required to transform CSV files into a sophisticated knowledge graph. We will then build a reliable agent capable of answering questions like "Find the shortest path between King's Cross and Victoria."

## Architecture Overview

The pipeline follows a data engineering flow of the following: data ingestion via Databricks, graph construction via the Neo4j Spark Connector, and query processing via a LangChain agent.

```mermaid
graph LR
    subgraph "Data Ingestion & Storage"
        CSV[Raw CSV Files] -->|Unity Catalog| Volume[UC Volume]
        Volume -->|PySpark| Delta[Delta Lake Tables]
    end
    
    subgraph "Graph Construction"
        Delta -->|Neo4j Spark Connector| Neo4j[(Neo4j Graph DB)]
        Note[Dynamic Relationship Types<br/>e.g., :BAKERLOO, :CENTRAL] -.-> Neo4j
    end
    
    subgraph "AI Application"
        User[User Question] -->|LangChain| Agent[GraphCypherQAChain]
        Agent -->|Schema & Instructions| LLM[LLM]
        LLM -->|Cypher Query| Neo4j
        Neo4j -->|Graph Result| Agent
        Agent -->|Natural Language| User
    end
```

## Stage One: The Foundation - Databricks Lakehouse & Unity Catalog

Before we can build a high-quality graph, we need a robust data foundation. We utilize the **Databricks Lakehouse** architecture, which unifies the massive scale of data lakes with the data management features of data warehouses.

### Unity Catalog: Governed Data Management
Central to this architecture is **Unity Catalog**. In our implementation, we use Unity Catalog Volumes to handle our raw file ingestion. This abstracts the underlying cloud storage (like S3 or ADLS), providing a unified, governed namespace for our files (`/Volumes/catalog/schema/volume/file.csv`).

This governance layer is critical for enterprise security. It ensures that access to raw data is audited and controlled before any processing begins.

### Delta Lake: The Reliability Layer
In our pipeline, we don't just read files and write to the graph. We ingest raw CSVs into **Delta Lake** tables first. Delta Lake adds a layer of reliability to standard Parquet files.

It brings **ACID transactions** to Spark. This ensures that our data operations are atomic and consistent. If a write fails midway, we don't end up with corrupted or partial data.

It also provides **Schema Enforcement**. We define our schema explicitly in PySpark, which ensures coordinates are doubles and IDs are integers. Any bad data is rejected at this stage, preventing "garbage in" from reaching the graph.

```python
# From notebooks/load_london_transport.ipynb
# Validating and writing stations to a managed Delta table
stations_clean = (
    stations_df
    .select(
        F.col("ID").cast("integer").alias("station_id"),
        F.col("Station_Name").alias("name"),
        # ... types are enforced here
    )
)
# Writing to Delta ensures ACID guarantees and persistence
stations_clean.write.format("delta").mode("overwrite").saveAsTable(STATIONS_TABLE)
```

## Stage Two: High-Scale Ingestion with the Neo4j Spark Connector

Moving data from a relational/tabular format (Spark DataFrames) to a graph structure (Nodes and Relationships) requires efficient translation. We use the **Neo4j Spark Connector**, a specialized library designed for high-throughput data movement.

### Data Transformation with Spark
Before ingestion, the data often needs precise transformation to match the target graph schema. Using PySpark, we can cast types, rename columns, and clean data efficiently before it ever touches the database.

In our `load_london_transport.ipynb` notebook, we explicitly define the schema for our Station nodes. This step ensures that coordinates are stored as doubles and IDs as integers, which is crucial for spatial calculations and indexed lookups later.

```python
# Select relevant columns and rename for Neo4j
stations_clean = (
    stations_df
    .select(
        F.col("ID").cast("integer").alias("station_id"),
        F.col("Station_Name").alias("name"),
        F.col("Latitude").cast("double").alias("latitude"),
        F.col("Longitude").cast("double").alias("longitude"),
        F.col("Zone").alias("zone"),
        F.col("Postcode").alias("postcode")
    )
)
```

### Distributed Processing Architecture
The connector leverages the distributed nature of Apache Spark. When a write operation is triggered, the Spark driver does not handle the data row-by-row. Instead, the DataFrame is partitioned across the cluster's executors.

Each executor establishes its own batch of connections to the Neo4j database using the **Bolt** binary protocol. This allows for massive parallelism. We can load millions of nodes and relationships simultaneously, limited only by the size of the Spark cluster and the Neo4j instance's write capacity.

### Dynamic Graph Modeling: Data as Schema
A critical design choice in this project is how we model transit lines. We avoid generic modeling. Instead of a single `:CONNECTED_TO` relationship with a property `{line: "Bakerloo"}`, we create specific relationship types for each line, such as `:BAKERLOO` or `:VICTORIA`.

**Performance Implications:**
Neo4j uses **native pointer chasing** (index-free adjacency) for traversal, but it indexes relationship types. Querying `MATCH ()-[:BAKERLOO]-()` allows the engine to instantly isolate only the relevant pointers. Scanning a generic relationship type and filtering on a string property would require reading every single connection and checking its properties—a much slower operation O(n) vs O(1) lookups.

### The Code Implementation: Dynamic & Idempotent Writes
We achieve this dynamically in PySpark. We first collect the distinct tube lines from our dataset, and then iterate through them. For each line, we sanitize the name to create a valid Neo4j relationship type (e.g., "Bakerloo" becomes "BAKERLOO", "Circle" becomes "CIRCLE").

Crucially, we use the `.option("relationship.save.strategy", "keys")` configuration. This tells the connector to perform a **MERGE** operation based on the node keys (station names). If we used the default `Create` strategy, re-running the pipeline would duplicate every connection. The `keys` strategy ensures **idempotency**—the pipeline generates the exact same graph state regardless of how many times it runs.

```python
# Iterate through each tube line to create specific relationship types
for line in sorted(tube_lines_list):
    # Convert tube line name to valid Neo4j relationship type
    # e.g. "Northern" -> "NORTHERN", "Metropolitan" -> "METROPOLITAN"
    rel_type = line.upper().replace(" ", "_").replace("&", "AND")
    
    # Write relationships using Neo4j Spark Connector
    (
        line_data.write
        .format("org.neo4j.spark.DataSource")
        .mode("Append")
        .option("relationship", rel_type)             # Dynamic Type: BAKERLOO
        
        # Idempotent Merge Strategy:
        # Matches existing nodes instead of creating new ones.
        .option("relationship.save.strategy", "keys") 
        
        # Schema Mapping:
        # Maps DataFrame columns to Node Properties for lookup
        .option("relationship.source.labels", ":Station")
        .option("relationship.source.node.keys", "from_station:name")
        .option("relationship.target.labels", ":Station")
        .option("relationship.target.node.keys", "to_station:name")
        .save()
    )
```

## Stage Three: The Natural Language Agent

With the graph built, we move to the final and most transformative stage: creating an intelligent agent that allows users to query this data using natural language. We utilize **LangChain's** `GraphCypherQAChain`, a powerful component designed to bridge the semantic gap between human questions and database query languages. Instead of writing complex Cypher code like `MATCH p=shortestPath((s1:Station)-[*]-(s2:Station))...`, a user can simply ask, "How do I get from Brixton to Victoria?". The agent translates this intent into a precise database query, executes it, and interprets the results, effectively acting as a translator between the user's intent and the graph's strict schema.

### The Agent Workflow and Architecture
The agent is built as a Python CLI tool (`agents/query_neo4j.py`) that integrates **LangChain**, **OpenAI** (or any compatible LLM), and the **Neo4j Python Driver**.

The core of the application is the `GraphCypherQAChain`, which automates the retrieval-generation loop:
1.  **Schema Retrieval:** The agent first connects to Neo4j to fetch the current schema (node labels, relationship types, and property keys). This schema is dynamically injected into the prompt, ensuring the LLM always knows the exact database structure.
2.  **Prompt Construction:** It combines the user's question with the schema and our specific instructions into a prompt.
3.  **Cypher Generation:** The LLM (e.g., GPT-4) generates a Cypher query based on the instructions.
4.  **Execution:** The generated query is executed against the Neo4j database. `GraphCypherQAChain` handles connection management and error catching.
5.  **Response Synthesis:** The raw database results are sent back to the LLM to generate a natural language answer.

### Prompt Engineering for Reliability
The biggest challenge with Text-to-Cypher is **hallucination**—the LLM generating invalid syntax or assuming schema elements that don't exist.

To combat this, we don't just rely on the LLM's inherent knowledge. We provide a strict `PromptTemplate` that enforces rules specific to our graph structure. We use a low temperature (`0.0`) for the LLM to maximize determinism.

In our `agents/query_neo4j.py`, we explicitly instruct the model on:
1.  **Case Insensitivity:** Users write "kings cross", database has "King's Cross". We force `toLower()` comparisons to ensure matches.
2.  **Modern Syntax:** We enforce the use of `COUNT{}` subqueries (Neo4j 5.x syntax) for better performance and cleaner code.
3.  **Schema Awareness:** We remind the model that tube lines are *relationship types*, not properties, preventing queries like `MATCH ()-[r {type:'Bakerloo'}]-()`.

Here is the prompt template we use to guide the model:

```python
# From agents/query_neo4j.py
cypher_template = """Task: Generate Cypher statement to query the London Transport Network graph database.

Instructions:
- Use only the provided relationship types and properties in the schema
- Do not use any other relationship types or properties that are not provided
- Use `WHERE toLower(node.name) CONTAINS toLower('name')` for case-insensitive name matching
- Relationships are bidirectional - you can traverse them in either direction
- For counting patterns, use modern COUNT{{}} subquery syntax
- Each tube line has its own relationship type (e.g., :BAKERLOO, :CENTRAL, :CIRCLE)
- Station properties include: station_id, name, zone, latitude, longitude, postcode
- To find busy stations, count connections: `count{{(s)-[]->()}}`
- To find paths, use shortest path: `shortestPath((from)-[*]-(to))`

Schema:
{schema}

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that ask anything other than generating a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}
"""
```

### Putting It All Together: The Conversational Interface
Finally, we instantiate the chain that ties the LLM, the prompt, and the database connection together.

The `GraphCypherQAChain.from_llm` method is the workhorse here. It takes our configured `ChatOpenAI` model (which serves as both the Cypher generator and the final answer synthesizer), our Neo4j connection, and our carefully crafted prompt.

By explicitly setting `return_direct=False` (or leaving it as default), the chain performs a final crucial step: it takes the raw JSON output from Neo4j and passes it back to the LLM with the original question. The LLM then summarizes these data points into a concise, human-readable sentence, completing the conversational experience.

```python
# From agents/query_neo4j.py
def create_cypher_chain(graph, config):
    cypher_llm = ChatOpenAI(
        api_key=config["openai_api_key"],
        model=config["model_name"],
        temperature=0.0
    )

    return GraphCypherQAChain.from_llm(
        graph=graph,
        llm=cypher_llm,              # Used for final answer synthesis
        cypher_llm=cypher_llm,       # Used for generating Cypher
        cypher_prompt=cypher_prompt, # Our strict schema instructions
        verbose=True,
        return_direct=False          # False = Generate natural language answer
    )
```

## Conclusion

By combining **Databricks** for robust data engineering, the **Neo4j Spark Connector** for efficient graph construction, and **LangChain** for accessible user interfaces, we can build knowledge graph applications that are both performant and easy to use.

The shift from "Code" to "Natural Language" doesn't eliminate the need for engineering; it shifts the focus. The engineering effort moves to:
1.  **Data Quality:** Ensuring the graph contains clean, valid data (Delta Lake).
2.  **Graph Modeling:** Designing schemas that are performant and semantically clear (Dynamic Relationship Types).
3.  **Prompt Engineering:** Creating constraints that guide the LLM to write correct database queries.