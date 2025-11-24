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
2. **Neo4j database** (Aura free tier or self-hosted)
3. **Neo4j Spark Connector** library installed on cluster:
   - Maven coordinates: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
4. **Databricks Secrets** configured:
   ```bash
   # Create secrets scope
   databricks secrets create-scope --scope neo4j-creds

   # Add credentials
   databricks secrets put --scope neo4j-creds --key username
   databricks secrets put --scope neo4j-creds --key password
   ```

### Setup Steps

#### 1. Upload CSV Files to Unity Catalog Volume

```sql
-- Create volume in Databricks SQL
CREATE VOLUME IF NOT EXISTS main.default.london_transport;
```

Upload files from `datasets/csv_files/london_transport/`:
- `London_stations.csv` (302 stations)
- `London_tube_lines.csv` (tube line connections)

#### 2. Configure Notebook

Open `notebooks/load_london_transport.ipynb` and update:

```python
# Neo4j connection
NEO4J_URL = "bolt://localhost:7687"  # Your Neo4j URL
NEO4J_DB  = "neo4j"                   # Your database name

# Unity Catalog paths
BASE_PATH = "/Volumes/main/default/london_transport"
CATALOG = "main"
SCHEMA = "default"
```

#### 3. Run Notebook

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
- **Bakerloo line relationships** connecting stations bidirectionally
- **Delta Lake tables** for stations and tube lines

## Project Structure

```
neo4j-databricks-etl/
├── README.md                              # This file
├── DBX_PORT_v2.md                         # Implementation plan and status
├── datasets/
│   ├── csv_files/
│   │   └── london_transport/
│   │       ├── London_stations.csv        # 302 stations
│   │       └── London_tube_lines.csv      # Tube connections
│   └── README.md                          # Dataset documentation
└── notebooks/
    └── load_london_transport.ipynb        # Main ETL notebook
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
- `(:Station)-[:BAKERLOO]->(:Station)` (bidirectional)

### Key Features

- **Intermediate Delta Lake storage** for data validation
- **Type-safe transformations** using PySpark
- **Batch relationship creation** using custom Cypher
- **Comprehensive validation queries**
- **Index creation** for performance

## Extending the Implementation

### Add All Tube Lines

Modify Step 10 in the notebook to process all lines:

```python
# Get all unique tube lines
tube_lines_list = (
    tube_lines
    .select("Tube_Line")
    .distinct()
    .rdd
    .flatMap(lambda x: x)
    .collect()
)

# Process each line
for line in tube_lines_list:
    line_data = tube_lines.filter(F.col("Tube_Line") == line)
    # Create relationships...
```

### Dynamic Relationship Types

Create different relationship types for each line:

```python
# Use line name as relationship type
create_rel_query = f"""
UNWIND $rows AS row
MATCH (from:Station {{name: row.From_Station}})
MATCH (to:Station {{name: row.To_Station}})
MERGE (from)-[:{line.upper()}]->(to)
MERGE (to)-[:{line.upper()}]->(from)
"""
```

## Validation Queries

Run these in Neo4j Browser:

```cypher
// Count all stations
MATCH (s:Station)
RETURN count(s) as total_stations;

// Count Bakerloo relationships
MATCH ()-[r:BAKERLOO]->()
RETURN count(r) as bakerloo_relationships;

// Find stations with most connections
MATCH (s:Station)-[:BAKERLOO]-()
RETURN s.name, count(*) as connections
ORDER BY connections DESC
LIMIT 5;

// Sample path query
MATCH path = (from:Station {name: 'Baker Street'})-[:BAKERLOO*1..3]-(to:Station)
RETURN path
LIMIT 5;
```

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

## Reference

This implementation follows patterns from the [databricks-neo4j-mcp-demo](https://github.com/neo4j-partners/databricks-neo4j-mcp-demo) project.

### Key Differences from GCP Dataflow

| Aspect | GCP Dataflow | This Project |
|--------|--------------|--------------|
| Configuration | JSON templates | Notebook cells |
| Data Source | BigQuery | Delta Lake |
| Orchestration | Managed template | Direct PySpark |
| Monitoring | Dataflow console | Spark UI |

## License

Sample data from Transport for London. Educational purposes only.

---

**Built with:** Databricks | Delta Lake | PySpark | Neo4j Spark Connector
