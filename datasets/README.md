# London Transport Network Dataset

Sample dataset demonstrating ETL from CSV files to Neo4j graph database.

## Dataset Overview

**Source:** Transport for London public transport network
**Records:** 302 stations with tube line connections
**Format:** CSV files with headers

## Files

### London_stations.csv

Contains metadata for London transport stations.

**Columns:**
- `ID` - Unique station identifier (integer)
- `Station_Name` - Full station name (string)
- `OS X` - Ordnance Survey X coordinate (integer)
- `OS Y` - Ordnance Survey Y coordinate (integer)
- `Latitude` - Latitude coordinate (decimal)
- `Longitude` - Longitude coordinate (decimal)
- `Zone` - Transport zone (string)
- `Postcode` - UK postal code (string)
- `Zone_original` - Original zone designation (string)

**Sample:**
```
ID,Station_Name,OS X,OS Y,Latitude,Longitude,Zone,Postcode,Zone_original
1,Abbey Road,539081,183352,51.53195199547290,0.003723371,3,E15 3NB,3
2,Abbey Wood,547297,179002,51.49078429543710,0.12027197064065100,4,SE2 9RH,4
```

**Row count:** 302 stations

### London_tube_lines.csv

Contains tube line connections between stations.

**Columns:**
- `Tube_Line` - Name of the tube line (string)
- `From_Station` - Origin station name (string)
- `To_Station` - Destination station name (string)

**Sample:**
```
Tube_Line,From_Station,To_Station
Bakerloo,Baker Street,Regents Park
Bakerloo,Charing Cross,Embankment
Central,Bank,Liverpool Street
```

**Tube lines included:**
- Bakerloo
- Central
- Circle
- District
- Hammersmith & City
- Jubilee
- Metropolitan
- Northern
- Piccadilly
- Victoria
- Waterloo & City

**Row count:** ~300 connections

## Graph Model

When loaded into Neo4j, the data creates:

### Nodes

**Label:** Station

**Properties:**
- `station_id` (integer) - Unique identifier
- `name` (string) - Station name
- `latitude` (double) - Geographic coordinate
- `longitude` (double) - Geographic coordinate
- `zone` (string) - Transport zone
- `postcode` (string) - UK postal code

### Relationships

**Type:** Named by tube line (e.g., BAKERLOO, CENTRAL, DISTRICT)

**Direction:** Bidirectional (created in both directions)

**Properties:** None in basic implementation

## Data Quality Notes

### Station Names
- Station names in `London_tube_lines.csv` must match exactly with `Station_Name` in `London_stations.csv`
- Names are case-sensitive
- Watch for trailing spaces

### Coordinates
- Latitude/Longitude are in decimal degrees (WGS84)
- OS X/Y are in British National Grid coordinates
- Some coordinates may be approximations

### Zones
- Transport zones range from 1 (central) to 6 (outer)
- Some stations span multiple zones (shown in `Zone_original`)
- Single zone selected in `Zone` column for simplicity

## Usage in ETL Pipeline

### Step 1: Load to Delta Lake

```python
# Read CSV with headers
stations_df = spark.read.option("header", "true").csv("path/to/London_stations.csv")
tube_lines_df = spark.read.option("header", "true").csv("path/to/London_tube_lines.csv")

# Write to Delta tables
stations_df.write.format("delta").saveAsTable("london_stations")
tube_lines_df.write.format("delta").saveAsTable("london_tube_lines")
```

### Step 2: Transform for Neo4j

```python
# Select and rename columns
stations_clean = stations_df.select(
    F.col("ID").cast("integer").alias("station_id"),
    F.col("Station_Name").alias("name"),
    F.col("Latitude").cast("double").alias("latitude"),
    F.col("Longitude").cast("double").alias("longitude"),
    F.col("Zone").alias("zone"),
    F.col("Postcode").alias("postcode")
)
```

### Step 3: Load to Neo4j

```python
# Write Station nodes
stations_clean.write \
    .format("org.neo4j.spark.DataSource") \
    .option("labels", ":Station") \
    .save()

# Create relationships using custom Cypher
create_rel_query = """
UNWIND $rows AS row
MATCH (from:Station {name: row.From_Station})
MATCH (to:Station {name: row.To_Station})
MERGE (from)-[:BAKERLOO]->(to)
MERGE (to)-[:BAKERLOO]->(from)
"""
```

## Data Source

This is a cleaned and simplified version of Transport for London public data representing the London Underground network.

**Original source:** Transport for London (TfL)
**License:** Public domain for educational use
**Modified:** Simplified for demonstration purposes

## Validation Queries

After loading, validate with these Cypher queries:

```cypher
// Total stations
MATCH (s:Station) RETURN count(s);

// Stations by zone
MATCH (s:Station)
RETURN s.zone, count(*) as stations
ORDER BY s.zone;

// Sample tube line connections
MATCH (from:Station)-[r:BAKERLOO]->(to:Station)
RETURN from.name, to.name
LIMIT 10;

// Find interchange stations (multiple connections)
MATCH (s:Station)-[r]-()
WITH s, count(r) as connections
WHERE connections > 4
RETURN s.name, connections
ORDER BY connections DESC;
```

## Notes

- Connection data represents direct connections, not full routes
- Not all possible connections may be included
- Relationship direction is for demonstration; in reality, most connections are bidirectional
- Data is current as of capture date and may not reflect recent changes to the network

---

For complete ETL implementation, see `notebooks/load_london_transport.ipynb`
