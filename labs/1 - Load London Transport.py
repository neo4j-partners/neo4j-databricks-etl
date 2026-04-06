# Databricks notebook source

# MAGIC %md
# MAGIC # Load London Transport
# MAGIC
# MAGIC ### Estimated time: 5-10 minutes
# MAGIC
# MAGIC This notebook loads the complete London Transport Network into Neo4j in a single step:
# MAGIC
# MAGIC 1. **CSV to Delta Lake** - Reads station and tube line data from the Unity Catalog Volume into Delta tables
# MAGIC 2. **Station nodes** - Writes 302 Station nodes to Neo4j via the Spark Connector
# MAGIC 3. **Tube line relationships** - Creates bidirectional relationships with **line-specific types** (e.g., `:BAKERLOO`, `:CENTRAL`, `:CIRCLE`)
# MAGIC
# MAGIC After this notebook runs, Neo4j contains the complete graph:
# MAGIC - **302 Station nodes** with names, zones, postcodes, and coordinates
# MAGIC - **Bidirectional relationships** for all tube lines using line-specific relationship types
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Run **0 - Required Setup** first
# MAGIC - Cluster must be **Dedicated** mode with the Neo4j Spark Connector Maven library installed

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Model
# MAGIC
# MAGIC The London Transport graph uses a simple but effective model:
# MAGIC
# MAGIC ```
# MAGIC (:Station) -[:BAKERLOO]->    (:Station)
# MAGIC (:Station) -[:CENTRAL]->     (:Station)
# MAGIC (:Station) -[:CIRCLE]->      (:Station)
# MAGIC (:Station) -[:DISTRICT]->    (:Station)
# MAGIC (:Station) -[:JUBILEE]->     (:Station)
# MAGIC (:Station) -[:METROPOLITAN]->(:Station)
# MAGIC (:Station) -[:NORTHERN]->    (:Station)
# MAGIC (:Station) -[:PICCADILLY]->  (:Station)
# MAGIC (:Station) -[:VICTORIA]->    (:Station)
# MAGIC ...and more
# MAGIC ```
# MAGIC
# MAGIC **Key design decision:** Each tube line is a **relationship type**, not a property on a
# MAGIC generic `:CONNECTED` relationship. This provides better query performance, clearer
# MAGIC semantics, and better visualization in Neo4j Browser.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run the Import

# COMMAND ----------

# MAGIC %run ./Includes/_lib/london_transport_import

# COMMAND ----------

run_full_import()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Explore the Graph
# MAGIC
# MAGIC Open Neo4j Browser and try these queries:
# MAGIC
# MAGIC **See the full schema:**
# MAGIC ```cypher
# MAGIC CALL db.schema.visualization()
# MAGIC ```
# MAGIC
# MAGIC **Count stations:**
# MAGIC ```cypher
# MAGIC MATCH (s:Station)
# MAGIC RETURN count(s) AS total_stations
# MAGIC ```
# MAGIC
# MAGIC **Connections by tube line:**
# MAGIC ```cypher
# MAGIC MATCH ()-[r]->()
# MAGIC RETURN type(r) AS line, count(r) AS connections
# MAGIC ORDER BY connections DESC
# MAGIC ```
# MAGIC
# MAGIC **Top 10 busiest stations:**
# MAGIC ```cypher
# MAGIC MATCH (s:Station)
# MAGIC RETURN s.name AS station, count{(s)-[]-()} AS total_connections
# MAGIC ORDER BY total_connections DESC
# MAGIC LIMIT 10
# MAGIC ```
# MAGIC
# MAGIC **Baker Street connections (all lines):**
# MAGIC ```cypher
# MAGIC MATCH (s:Station {name: 'Baker Street'})-[r]-(connected:Station)
# MAGIC RETURN s.name AS from_station, type(r) AS tube_line, connected.name AS to_station
# MAGIC ```
# MAGIC
# MAGIC **Shortest path between two stations:**
# MAGIC ```cypher
# MAGIC MATCH path = shortestPath(
# MAGIC   (from:Station {name: "King's Cross St. Pancras"})-[*..5]-(to:Station {name: 'Victoria'})
# MAGIC )
# MAGIC RETURN path, length(path) AS hops,
# MAGIC        [rel IN relationships(path) | type(rel)] AS lines_used
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC The graph is fully loaded. Continue to:
# MAGIC
# MAGIC - **2 - Query London Transport**: Ask questions in natural language using text-to-Cypher
# MAGIC - **Neo4j Browser**: Explore the graph visually
