# Databricks notebook source

# MAGIC %md
# MAGIC # Query London Transport
# MAGIC
# MAGIC ### Estimated time: 10 minutes
# MAGIC
# MAGIC Ask questions about the London Transport Network in plain English and get answers
# MAGIC through automatically generated Cypher queries.
# MAGIC
# MAGIC 1. **Connects to Neo4j** - Uses the London Transport graph loaded in Lab 1
# MAGIC 2. **Retrieves Graph Schema** - Automatically gets the structure of nodes and relationships
# MAGIC 3. **Converts Questions to Cypher** - Uses an LLM to generate valid Cypher queries
# MAGIC 4. **Executes and Returns Results** - Runs the generated Cypher directly
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Run **0 - Required Setup** and **1 - Load London Transport** first
# MAGIC - Cluster must be **Dedicated** mode

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

# MAGIC %pip install --quiet langchain==1.0.8 langchain-neo4j==0.6.0 langchain-openai==1.0.3 neo4j==5.25.0

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Neo4j credentials are loaded from the secrets stored by the setup notebook.
# MAGIC Configure the Databricks Foundation Model endpoint in the widgets.

# COMMAND ----------

dbutils.widgets.text("databricks_endpoint", "", "Databricks Serving Endpoint URL")
dbutils.widgets.text("model_name", "databricks-claude-sonnet-4-5", "Model Name")

# COMMAND ----------

import yaml

# Load Neo4j credentials from secrets
notebook_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
workspace_base = "/Workspace" + notebook_path.rsplit("/", 1)[0]
config_path = f"{workspace_base}/Includes/config.yaml"

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

scope = config["secrets"]["scope_name"]

NEO4J_URL = dbutils.secrets.get(scope=scope, key="url")
NEO4J_USER = dbutils.secrets.get(scope=scope, key="username")
NEO4J_PASS = dbutils.secrets.get(scope=scope, key="password")
NEO4J_DB = "neo4j"

DATABRICKS_ENDPOINT = dbutils.widgets.get("databricks_endpoint")
MODEL_NAME = dbutils.widgets.get("model_name")
DATABRICKS_TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

print("Configuration loaded:")
print(f"  Neo4j URL:  {NEO4J_URL}")
print(f"  Neo4j User: {NEO4J_USER}")
print(f"  Model:      {MODEL_NAME}")
print(f"  Endpoint:   {DATABRICKS_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Neo4j and Validate Data

# COMMAND ----------

from langchain_neo4j import Neo4jGraph

graph = Neo4jGraph(
    url=NEO4J_URL,
    username=NEO4J_USER,
    password=NEO4J_PASS,
    database=NEO4J_DB,
)

print("[OK] Connected to Neo4j")

# COMMAND ----------

# Validate that London Transport data exists
validation_query = """
RETURN
  count{MATCH (s:Station)} as station_count,
  count{MATCH ()-[r]->()} as relationship_count
"""

result = graph.query(validation_query)

if result and result[0]["station_count"] > 0:
    print(f"[OK] London Transport data found:")
    print(f"  Stations:    {result[0]['station_count']}")
    print(f"  Connections: {result[0]['relationship_count']}")
else:
    print("[FAIL] No data found. Please run '1 - Load London Transport' first.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Graph Schema

# COMMAND ----------

schema = graph.schema

print("=" * 80)
print("LONDON TRANSPORT GRAPH SCHEMA")
print("=" * 80)
print(schema)
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configure LLM for Cypher Generation
# MAGIC
# MAGIC Uses a Databricks Foundation Model with temperature 0.0 for deterministic,
# MAGIC consistent Cypher generation.

# COMMAND ----------

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain

cypher_llm = ChatOpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url=DATABRICKS_ENDPOINT,
    model=MODEL_NAME,
    temperature=0.0,
)

print("[OK] LLM configured")

# COMMAND ----------

cypher_template = """Task: Generate Cypher statement to query the London Transport Network graph database.

Instructions:
- Use only the provided relationship types and properties in the schema
- Do not use any other relationship types or properties that are not provided
- Use `WHERE toLower(node.name) CONTAINS toLower('name')` for case-insensitive name matching
- Relationships are bidirectional - you can traverse them in either direction
- For counting patterns, use modern COUNT{{}} subquery syntax
- Each tube line has its own relationship type (e.g., :BAKERLOO, :CENTRAL, :CIRCLE)
- Station properties include: station_id, name, zone, latitude, longitude, postcode
- To find busy stations, count connections: `count{{(s)-[]-()}}`
- To find paths, use shortest path: `shortestPath((from)-[*]-(to))`

Schema:
{schema}

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that ask anything other than generating a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}
"""

cypher_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template=cypher_template,
)

print("[OK] Cypher prompt template created")

# COMMAND ----------

cypher_chain = GraphCypherQAChain.from_llm(
    graph=graph,
    llm=cypher_llm,
    cypher_llm=cypher_llm,
    cypher_prompt=cypher_prompt,
    allow_dangerous_requests=True,
    return_direct=True,
    verbose=True,
)

print("[OK] Cypher QA chain created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Query Interface
# MAGIC
# MAGIC Use `ask_question()` to ask questions in natural language.
# MAGIC The LLM generates Cypher, executes it, and returns results directly.

# COMMAND ----------

def ask_question(question: str):
    """Ask a question about the London Transport Network."""
    print("=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)

    result = cypher_chain.invoke({"query": question})

    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)

    return result

# COMMAND ----------

# MAGIC %md
# MAGIC ### Try Your Own Question
# MAGIC
# MAGIC Modify the question below and run the cell:

# COMMAND ----------

question = "How many stations are in zone 1?"

result = ask_question(question)
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example Questions
# MAGIC
# MAGIC Run the cells below to try different types of questions.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Basic Counting

# COMMAND ----------

result = ask_question("How many stations are there in total?")
print(result)

# COMMAND ----------

result = ask_question("How many stations are in zone 2?")
print(result)

# COMMAND ----------

result = ask_question("Count the stations in each zone")
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Station Information

# COMMAND ----------

result = ask_question("Show me all stations in zone 1")
print(result)

# COMMAND ----------

result = ask_question("What zone is King's Cross St. Pancras in?")
print(result)

# COMMAND ----------

result = ask_question("Show me 10 stations with their zones and postcodes")
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tube Line Queries

# COMMAND ----------

result = ask_question("Which stations does the Bakerloo line connect?")
print(result)

# COMMAND ----------

result = ask_question("What tube lines go through Baker Street?")
print(result)

# COMMAND ----------

result = ask_question("Show all Central line connections")
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Connection and Traffic

# COMMAND ----------

result = ask_question("Which stations have the most connections?")
print(result)

# COMMAND ----------

result = ask_question("Show me the top 10 busiest interchange stations")
print(result)

# COMMAND ----------

result = ask_question("Which stations have fewer than 4 connections?")
print(result)

# COMMAND ----------

result = ask_question("How many connections does Oxford Circus have?")
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Path Finding and Travel

# COMMAND ----------

result = ask_question("Find a path between King's Cross St. Pancras and Victoria")
print(result)

# COMMAND ----------

result = ask_question("What's a route from Paddington to Liverpool Street?")
print(result)

# COMMAND ----------

result = ask_question("Show me stations I should avoid during rush hour based on connection counts")
print(result)

# COMMAND ----------

result = ask_question("Which quieter stations could I use as alternatives to busy interchanges?")
print(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## How It Works
# MAGIC
# MAGIC This notebook uses a text-to-Cypher pipeline:
# MAGIC
# MAGIC 1. **Natural Language Question** - You ask a question in plain English
# MAGIC 2. **Schema Context** - The graph schema is provided to the LLM
# MAGIC 3. **Cypher Generation** - The LLM generates a Cypher query (displayed in output)
# MAGIC 4. **Query Execution** - The Cypher is executed against Neo4j
# MAGIC 5. **Results Display** - Results are returned directly
# MAGIC
# MAGIC ### Why Temperature 0.0?
# MAGIC
# MAGIC The Cypher generation LLM uses `temperature=0.0` for deterministic, consistent query
# MAGIC generation. This ensures the same question produces the same Cypher query every time.
# MAGIC
# MAGIC ### Modern Cypher Syntax
# MAGIC
# MAGIC The prompt instructs the LLM to use modern Neo4j 5.x syntax:
# MAGIC - `COUNT{}` subqueries instead of OPTIONAL MATCH
# MAGIC - Case-insensitive matching with `toLower()`
# MAGIC - Efficient pattern matching

# COMMAND ----------

# MAGIC %md
# MAGIC ## Limitations
# MAGIC
# MAGIC **What it does well:**
# MAGIC - Simple counting queries ("How many...")
# MAGIC - Station lookups ("Which stations...")
# MAGIC - Relationship queries ("What lines connect...")
# MAGIC - Basic path finding ("Find a route...")
# MAGIC
# MAGIC **What it cannot do:**
# MAGIC - Complex multi-hop reasoning
# MAGIC - Optimal journey planning with transfers
# MAGIC - Real-time timetable information
# MAGIC - Updates or modifications to data (read-only)
# MAGIC - Ambiguous questions without clear intent
# MAGIC
# MAGIC **Best practices:**
# MAGIC - Be specific in your questions
# MAGIC - Use station names as they appear in the data
# MAGIC - Review the generated Cypher to understand results
# MAGIC - For complex questions, break them into simpler parts
