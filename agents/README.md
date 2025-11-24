# Neo4j Natural Language Query Agent

A standalone Python program that allows you to query the Neo4j London Transport graph using natural language. Converted from the Databricks notebook `query_london_transport.ipynb` to run anywhere with `uv`.

## Features

- **Natural Language Queries** - Ask questions in plain English
- **Automatic Cypher Generation** - LLM converts your questions to Cypher
- **Direct Results** - Execute queries and display results immediately
- **Interactive Mode** - Continuous question-and-answer sessions
- **Single Question Mode** - Run one query and exit
- **Flexible LLM Support** - Works with OpenAI, Databricks Foundation Models, Ollama, or any OpenAI-compatible endpoint

## Prerequisites

- **Python 3.11+** (managed by `uv`)
- **Neo4j database** with London Transport data loaded (run `../notebooks/load_london_transport.ipynb` first)
- **LLM API access** (OpenAI, Databricks Foundation Models, or compatible endpoint)

## Installation

### 1. Install `uv`

Following [uv best practices](https://emily.space/posts/251023-uv):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Set up the project

```bash
cd agents

# Create virtual environment and install dependencies
uv sync

# Or manually:
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 3. Configure environment variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

#### Configuration for Databricks Foundation Models

To use Databricks Foundation Models:

1. **Generate a Personal Access Token**: Follow the [Databricks authentication documentation](https://docs.databricks.com/en/dev-tools/auth/pat.html) to create a personal access token
2. **Find your serving endpoint URL**: In your Databricks workspace, go to Serving and note the endpoint URL (e.g., `https://your-workspace.cloud.databricks.com/serving-endpoints`)
3. **Configure `.env`**:

```bash
NEO4J_URL=neo4j+s://xxx.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

# Databricks configuration
OPENAI_API_KEY=dapi1234567890abcdef  # Your Databricks PAT token
OPENAI_BASE_URL=https://your-workspace.cloud.databricks.com/serving-endpoints
MODEL_NAME=databricks-claude-sonnet-4-5
```

#### Configuration for OpenAI

```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
```

#### Configuration for Ollama (Local)

```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL_NAME=llama2
```

## Usage

### Interactive Mode (Default)

Ask multiple questions in a continuous session:

```bash
# Using uv run (recommended)
uv run query_neo4j.py

# Or activate venv first
source .venv/bin/activate
python query_neo4j.py
```

### Single Question Mode

Ask one question and exit:

```bash
uv run query_neo4j.py --question "How many stations are in zone 1?"
uv run query_neo4j.py -q "Which stations does the Bakerloo line connect?"
```

### Display Graph Schema

View the Neo4j graph structure:

```bash
uv run query_neo4j.py --show-schema
```

## Example Questions

### Basic Counting
- "How many stations are there in total?"
- "How many stations are in zone 2?"
- "Count the stations in each zone"

### Station Information
- "Show me all stations in zone 1"
- "What zone is King's Cross St. Pancras in?"
- "Show me 10 stations with their zones and postcodes"

### Tube Line Queries
- "Which stations does the Bakerloo line connect?"
- "What tube lines go through Baker Street?"
- "Show all Central line connections"

### Connection Analysis
- "Which stations have the most connections?"
- "Show me the top 10 busiest interchange stations"
- "Which stations have fewer than 4 connections?"
- "How many connections does Oxford Circus have?"

### Path Finding
- "Find a path between King's Cross St. Pancras and Victoria"
- "What's a route from Paddington to Liverpool Street?"
- "Show me stations I should avoid during rush hour based on connection counts"

## How It Works

This program uses a **text-to-Cypher pipeline**:

1. **Natural Language Question** - You ask in plain English
2. **Schema Context** - The Neo4j graph schema is provided to the LLM
3. **Cypher Generation** - LLM generates a Cypher query (displayed in verbose output)
4. **Query Execution** - Cypher is executed against Neo4j
5. **Results Display** - Results are returned directly

### Why Temperature 0.0?

The LLM uses `temperature=0.0` for **deterministic, consistent** query generation. The same question will produce the same Cypher query every time.

### Modern Cypher Syntax

The prompt instructs the LLM to use modern Neo4j 5.x syntax:
- `COUNT{}` subqueries instead of `OPTIONAL MATCH`
- Case-insensitive matching with `toLower()`
- Efficient pattern matching

## Limitations

**What it does well:**
- Simple counting queries ("How many...")
- Station lookups ("Which stations...")
- Relationship queries ("What lines connect...")
- Basic path finding ("Find a route...")

**What it cannot do:**
- Complex multi-hop reasoning
- Optimal journey planning with transfers
- Real-time timetable information
- Updates or modifications to data (read-only)
- Ambiguous questions without clear intent
- Questions about data not in the graph

**Best practices:**
- Be specific in your questions
- Use station names as they appear in the data
- Review the generated Cypher to understand results
- For complex questions, break them into simpler parts


## References

- [uv best practices](https://emily.space/posts/251023-uv)
- [LangChain Neo4j Integration](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)

## License

Same as parent project.
