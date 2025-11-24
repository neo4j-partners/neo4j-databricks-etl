#!/usr/bin/env python3
"""
Natural Language Query Agent for Neo4j London Transport Graph

This script allows you to ask questions about the London Transport Network
in plain English and get answers through automatically generated Cypher queries.

Example usage:
    python query_neo4j.py
    python query_neo4j.py --question "How many stations are in zone 1?"
    python query_neo4j.py --interactive
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI


def load_config() -> dict:
    """Load configuration from environment variables."""
    # Load .env file from the same directory as this script
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    config = {
        "neo4j_url": os.getenv("NEO4J_URL", "bolt://localhost:7687"),
        "neo4j_username": os.getenv("NEO4J_USERNAME", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
        "neo4j_database": os.getenv("NEO4J_DATABASE", "neo4j"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
        "model_name": os.getenv("MODEL_NAME", "gpt-4"),
    }

    # Validate required configuration
    if not config["neo4j_password"]:
        print("Error: NEO4J_PASSWORD not set in .env file", file=sys.stderr)
        sys.exit(1)

    if not config["openai_api_key"]:
        print("Error: OPENAI_API_KEY not set in .env file", file=sys.stderr)
        sys.exit(1)

    return config


def connect_to_neo4j(config: dict) -> Neo4jGraph:
    """Connect to Neo4j and return graph instance."""
    try:
        graph = Neo4jGraph(
            url=config["neo4j_url"],
            username=config["neo4j_username"],
            password=config["neo4j_password"],
            database=config["neo4j_database"]
        )
        print(f"✓ Connected to Neo4j at {config['neo4j_url']}")
        return graph
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}", file=sys.stderr)
        sys.exit(1)


def validate_data(graph: Neo4jGraph) -> bool:
    """Validate that London Transport data exists in the graph."""
    validation_query = """
    MATCH (s:Station)
    WITH count(s) as station_count
    MATCH ()-[r]->()
    RETURN station_count, count(r) as relationship_count
    """

    try:
        result = graph.query(validation_query)

        if result and result[0]['station_count'] > 0:
            print(f"✓ London Transport data found:")
            print(f"  - Stations: {result[0]['station_count']}")
            print(f"  - Connections: {result[0]['relationship_count']}")
            return True
        else:
            print("✗ No data found. Please run load_london_transport.ipynb first.", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error validating data: {e}", file=sys.stderr)
        return False


def create_cypher_chain(graph: Neo4jGraph, config: dict) -> GraphCypherQAChain:
    """Create the Cypher QA chain with LLM."""
    # Initialize LLM for Cypher generation with temperature 0.0 for consistency
    llm_config = {
        "api_key": config["openai_api_key"],
        "model": config["model_name"],
        "temperature": 0.0,
    }

    # Add base_url if provided (for Databricks or other OpenAI-compatible endpoints)
    if config["openai_base_url"]:
        llm_config["base_url"] = config["openai_base_url"]

    cypher_llm = ChatOpenAI(**llm_config)

    print(f"✓ LLM configured: {config['model_name']}")

    # Create Cypher generation prompt template
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

    cypher_prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template=cypher_template
    )

    # Create the Cypher QA chain
    cypher_chain = GraphCypherQAChain.from_llm(
        graph=graph,
        llm=cypher_llm,
        cypher_llm=cypher_llm,
        cypher_prompt=cypher_prompt,
        allow_dangerous_requests=True,
        return_direct=True,
        verbose=True
    )

    print("✓ Cypher QA chain created")
    print()

    return cypher_chain


def ask_question(chain: GraphCypherQAChain, question: str) -> dict:
    """
    Ask a question about the London Transport Network.

    The LLM will generate a Cypher query, execute it, and return the results.
    Generated Cypher will be displayed due to verbose=True.
    """
    print("=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)

    result = chain.invoke({"query": question})

    print()
    print("=" * 80)
    print("RESULT:")
    print("=" * 80)
    print(result)
    print()

    return result


def interactive_mode(chain: GraphCypherQAChain):
    """Run in interactive mode, allowing continuous questions."""
    print("=" * 80)
    print("INTERACTIVE MODE")
    print("=" * 80)
    print()
    print("Ask questions about the London Transport Network.")
    print("Type 'exit', 'quit', or press Ctrl+C to exit.")
    print()
    print("Example questions:")
    print("  - How many stations are in zone 1?")
    print("  - Which stations does the Bakerloo line connect?")
    print("  - What tube lines go through Baker Street?")
    print("  - Which stations have the most connections?")
    print("  - Find a path between King's Cross and Victoria")
    print()

    while True:
        try:
            question = input("Your question: ").strip()

            if not question:
                continue

            if question.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            ask_question(chain, question)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query Neo4j London Transport graph with natural language"
    )
    parser.add_argument(
        "-q", "--question",
        type=str,
        help="Ask a single question and exit"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (default if no question provided)"
    )
    parser.add_argument(
        "--show-schema",
        action="store_true",
        help="Display the graph schema and exit"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Connect to Neo4j
    graph = connect_to_neo4j(config)

    # Validate data exists
    if not validate_data(graph):
        sys.exit(1)

    print()

    # Show schema if requested
    if args.show_schema:
        print("=" * 80)
        print("LONDON TRANSPORT GRAPH SCHEMA")
        print("=" * 80)
        print(graph.schema)
        print("=" * 80)
        return

    # Create Cypher chain
    chain = create_cypher_chain(graph, config)

    # Handle different modes
    if args.question:
        # Single question mode
        ask_question(chain, args.question)
    else:
        # Interactive mode (default)
        interactive_mode(chain)


if __name__ == "__main__":
    main()
