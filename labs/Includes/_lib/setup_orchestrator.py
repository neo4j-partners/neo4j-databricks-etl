"""
Setup orchestrator for the London Transport ETL Workshop.

This module handles all environment preparation:
- Catalog, schema, and volume creation
- Data file copying from Includes/data/ to the volume
- Neo4j secret scope creation and validation
- Neo4j connectivity verification

Called by the "0 - Required Setup" notebook via %run.
"""

import os
import shutil


def get_username() -> str:
    """Get the current Databricks username."""
    return spark.sql("SELECT current_user()").first()[0]  # noqa: F821


def derive_catalog_name(prefix: str, username: str) -> str:
    """Derive a catalog name from prefix and username.

    Sanitizes the username to be a valid catalog identifier:
    - Takes the part before @ in the email
    - Replaces dots and hyphens with underscores
    """
    user_part = username.split("@")[0]
    user_part = user_part.replace(".", "_").replace("-", "_")
    return f"{prefix}_{user_part}"


def setup_catalog_and_schema(catalog_name: str, schema_name: str, volume_name: str) -> dict:
    """Create catalog, schema, and volume if they don't exist.

    Returns dict with catalog, schema, volume names and the full volume path.
    """
    print("=" * 70)
    print("STEP 1: Creating Catalog, Schema, and Volume")
    print("=" * 70)

    # Create catalog
    print(f"\n  Creating catalog: {catalog_name}")
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog_name}`")  # noqa: F821
        print(f"  [OK] Catalog '{catalog_name}' ready")
    except Exception as e:
        print(f"  [FAIL] Could not create catalog: {e}")
        print("  You may need CREATE CATALOG permission. Ask your workspace admin.")
        raise

    # Use the catalog
    spark.sql(f"USE CATALOG `{catalog_name}`")  # noqa: F821

    # Create schema
    print(f"\n  Creating schema: {schema_name}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{schema_name}`")  # noqa: F821
    print(f"  [OK] Schema '{schema_name}' ready")

    # Use the schema
    spark.sql(f"USE SCHEMA `{schema_name}`")  # noqa: F821

    # Create volume
    print(f"\n  Creating volume: {volume_name}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{volume_name}`")  # noqa: F821
    print(f"  [OK] Volume '{volume_name}' ready")

    volume_path = f"/Volumes/{catalog_name}/{schema_name}/{volume_name}"
    print(f"\n  Volume path: {volume_path}")

    return {
        "catalog": catalog_name,
        "schema": schema_name,
        "volume": volume_name,
        "volume_path": volume_path,
    }


def copy_data_files(volume_path: str, includes_data_path: str) -> dict:
    """Copy CSV files from Includes/data/ to the volume.

    Both workspace files (/Workspace/...) and Unity Catalog volumes (/Volumes/...)
    are accessible as regular filesystem paths in Databricks.

    Args:
        volume_path: Target Unity Catalog volume path (e.g. /Volumes/catalog/schema/vol).
        includes_data_path: Workspace path to the Includes/data/ directory.

    Returns:
        Dict with count of files copied.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Copying Data Files to Volume")
    print("=" * 70)

    counts = {"csv": 0}

    source_dir = os.path.join(includes_data_path, "csv")
    target_dir = os.path.join(volume_path, "csv")

    # Create target subdirectory
    os.makedirs(target_dir, exist_ok=True)

    print("\n  Copying CSV files...")
    if not os.path.isdir(source_dir):
        print(f"    [WARN] Source directory not found: {source_dir}")
        return counts

    for filename in sorted(os.listdir(source_dir)):
        if filename.endswith(".csv"):
            src = os.path.join(source_dir, filename)
            dst = os.path.join(target_dir, filename)
            shutil.copy2(src, dst)
            counts["csv"] += 1
            print(f"    [OK] {filename}")

    print(f"\n  Summary: {counts['csv']} CSV files copied")
    return counts


def setup_neo4j_secrets(scope_name: str, neo4j_url: str, neo4j_username: str, neo4j_password: str, volume_path: str) -> bool:
    """Create Databricks secret scope and store Neo4j credentials.

    Uses the Databricks SDK WorkspaceClient to manage secrets, since
    dbutils.secrets only supports reading secrets, not writing them.

    Args:
        scope_name: Name of the secret scope to create.
        neo4j_url: Neo4j connection URI.
        neo4j_username: Neo4j username.
        neo4j_password: Neo4j password.
        volume_path: Volume path to store as a secret.

    Returns:
        True if all secrets were stored successfully.
    """
    from databricks.sdk import WorkspaceClient

    print("\n" + "=" * 70)
    print("STEP 3: Configuring Neo4j Secrets")
    print("=" * 70)

    w = WorkspaceClient()

    # Create scope
    print(f"\n  Creating secret scope: {scope_name}")
    try:
        w.secrets.create_scope(scope=scope_name)
        print(f"  [OK] Scope '{scope_name}' created")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  [OK] Scope '{scope_name}' already exists")
        else:
            print(f"  [FAIL] Could not create scope: {e}")
            raise

    # Store secrets
    secrets_to_store = {
        "url": neo4j_url,
        "username": neo4j_username,
        "password": neo4j_password,
        "volume_path": volume_path,
    }

    for key, value in secrets_to_store.items():
        print(f"  Storing secret: {key}")
        try:
            w.secrets.put_secret(scope=scope_name, key=key, string_value=value)
            print(f"  [OK] {key} stored")
        except Exception as e:
            print(f"  [FAIL] Could not store {key}: {e}")
            raise

    return True


def verify_neo4j_connection(neo4j_url: str, neo4j_username: str, neo4j_password: str) -> bool:
    """Verify that Neo4j is reachable.

    Uses the Neo4j Python driver to test connectivity.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Verifying Neo4j Connection")
    print("=" * 70)

    try:
        from neo4j import GraphDatabase

        print(f"\n  Connecting to: {neo4j_url}")
        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_username, neo4j_password))

        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 'Connected' AS status")
            record = result.single()
            print(f"  [OK] Neo4j responded: {record['status']}")

        driver.close()
        return True

    except Exception as e:
        print(f"  [FAIL] Could not connect to Neo4j: {e}")
        print("\n  Check that:")
        print("    - The Neo4j URI is correct (should start with neo4j+s:// for Aura)")
        print("    - The username and password are correct")
        print("    - The Neo4j instance is running")
        return False


def print_summary(info: dict):
    """Print a summary of the setup results."""
    print("\n" + "=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print(f"""
  Catalog:     {info['catalog']}
  Schema:      {info['schema']}
  Volume:      {info['volume']}
  Volume Path: {info['volume_path']}
  Neo4j URL:   {info['neo4j_url']}
  Scope:       {info['scope_name']}

  Data files copied:
    CSV: {info['file_counts']['csv']}

  Neo4j connection: {'OK' if info['neo4j_connected'] else 'FAILED'}
""")
    print("=" * 70)

    if info["neo4j_connected"]:
        print("\n  You are ready to proceed to '1 - Load London Transport'.")
    else:
        print("\n  Fix the Neo4j connection before proceeding.")
