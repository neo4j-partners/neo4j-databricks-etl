# Neo4j Natural Language Query Agent

A standalone Python program that allows you to query the Neo4j London Transport graph using natural language. Converted from the Databricks notebook `query_london_transport.ipynb` to run anywhere with `uv`.

## Features

- 🗣️ **Natural Language Queries** - Ask questions in plain English
- 🔍 **Automatic Cypher Generation** - LLM converts your questions to Cypher
- 📊 **Direct Results** - Execute queries and display results immediately
- 🔄 **Interactive Mode** - Continuous question-and-answer sessions
- 🎯 **Single Question Mode** - Run one query and exit
- 🌐 **Flexible LLM Support** - Works with OpenAI, Databricks, Ollama, or any OpenAI-compatible endpoint

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

#### Configuration Options

**For OpenAI:**
```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
```

**For Databricks Foundation Models:**
```bash
NEO4J_URL=neo4j+s://xxx.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=your_databricks_token
OPENAI_BASE_URL=https://your-workspace.cloud.databricks.com/serving-endpoints
MODEL_NAME=databricks-claude-sonnet-4-5
```

**For Ollama (local):**
```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
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

Example session:
```
✓ Connected to Neo4j at bolt://localhost:7687
✓ London Transport data found:
  - Stations: 302
  - Connections: 732
✓ LLM configured: gpt-4
✓ Cypher QA chain created

================================================================================
INTERACTIVE MODE
================================================================================

Ask questions about the London Transport Network.
Type 'exit', 'quit', or press Ctrl+C to exit.

Example questions:
  - How many stations are in zone 1?
  - Which stations does the Bakerloo line connect?
  - What tube lines go through Baker Street?
  - Which stations have the most connections?
  - Find a path between King's Cross and Victoria

Your question: How many stations are in zone 1?
================================================================================
QUESTION: How many stations are in zone 1?
================================================================================

> Entering new GraphCypherQAChain chain...
Generated Cypher:
MATCH (s:Station {zone: '1'})
RETURN count(s) AS station_count

Full Context:
[{'station_count': 52}]

> Finished chain.

================================================================================
RESULT:
================================================================================
[{'station_count': 52}]

Your question: exit
Goodbye!
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

## Project Structure

```
agents/
├── README.md              # This file
├── pyproject.toml         # Project dependencies (uv format)
├── .env.example           # Environment variable template
├── .env                   # Your configuration (create from .env.example)
├── query_neo4j.py         # Main script
└── .venv/                 # Virtual environment (created by uv)
```

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

## Troubleshooting

### "Error: NEO4J_PASSWORD not set in .env file"
- Ensure you've created `.env` from `.env.example`
- Check that `NEO4J_PASSWORD` is set in `.env`

### "Error connecting to Neo4j"
- Verify Neo4j is running
- Check `NEO4J_URL` is correct (`bolt://host:7687` or `neo4j+s://host:7687`)
- Confirm credentials are correct

### "No data found"
- Run the ETL notebook first: `../notebooks/load_london_transport.ipynb`
- Verify you're connecting to the correct database

### "Error: OPENAI_API_KEY not set"
- Set `OPENAI_API_KEY` in `.env`
- For Databricks, use your personal access token
- For Ollama, can be set to any value (e.g., "not-needed")

### Invalid Cypher Generated
- The question may be too ambiguous
- Try rephrasing with more specific details
- Check that you're asking about data that exists

### LLM Connection Errors
- Verify `OPENAI_BASE_URL` is correct
- For Databricks: `https://your-workspace.cloud.databricks.com/serving-endpoints`
- For Ollama: `http://localhost:11434/v1`
- For OpenAI: `https://api.openai.com/v1`

## Development

### Running with `uv run`

The recommended way to run the script (automatically manages the venv):

```bash
uv run query_neo4j.py
```

### Installing the package

Install as an editable package:

```bash
uv pip install -e .
```

Then run from anywhere:

```bash
query-neo4j
```

### Adding dependencies

```bash
uv add package-name
```

## Differences from Databricks Notebook

| Feature | Notebook | This Script |
|---------|----------|-------------|
| Configuration | `dbutils.widgets` | `.env` file |
| Secrets | `dbutils.secrets` | `.env` file |
| Python Runtime | Databricks cluster | Local Python (uv) |
| Interface | Notebook cells | CLI (interactive/single) |
| Execution | Cell-by-cell | Continuous program |

## References

- [uv best practices](https://emily.space/posts/251023-uv)
- [LangChain Neo4j Integration](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)

## License

Same as parent project.
