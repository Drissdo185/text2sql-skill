#!/usr/bin/env python3
"""
Schema Scanner for Text2SQL Skill
Extracts and analyzes PostgreSQL database schemas
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import psycopg
except ImportError:
    print("Error: psycopg library not found. Please install it:")
    print("  pip install 'psycopg[binary]'")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def mask_connection_string(conn_str: str) -> str:
    """
    Mask password in connection string for safe display

    Args:
        conn_str: Database connection string

    Returns:
        Connection string with masked password
    """
    try:
        parsed = urlparse(conn_str)
        if parsed.password:
            masked = conn_str.replace(parsed.password, '***')
            return masked
        return conn_str
    except Exception:
        return "***connection string***"


def get_cache_path(conn_str: str, schema: str) -> str:
    """
    Generate cache file path based on connection string and schema

    Args:
        conn_str: Database connection string
        schema: Schema name

    Returns:
        Path to cache file
    """
    # Create hash of connection string (without password for consistency)
    masked = mask_connection_string(conn_str)
    hash_obj = hashlib.md5(f"{masked}:{schema}".encode())
    cache_hash = hash_obj.hexdigest()[:12]

    return f"/tmp/text2sql_schema_{cache_hash}.json"


def is_cache_valid(cache_path: str, ttl_seconds: int = 3600) -> bool:
    """
    Check if cache file exists and is still valid

    Args:
        cache_path: Path to cache file
        ttl_seconds: Time-to-live in seconds (default: 1 hour)

    Returns:
        True if cache is valid, False otherwise
    """
    if not os.path.exists(cache_path):
        return False

    file_age = time.time() - os.path.getmtime(cache_path)
    return file_age < ttl_seconds


def load_cache(cache_path: str) -> Optional[Dict]:
    """
    Load schema data from cache file

    Args:
        cache_path: Path to cache file

    Returns:
        Cached schema data or None if load fails
    """
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def save_cache(cache_path: str, data: Dict) -> None:
    """
    Save schema data to cache file

    Args:
        cache_path: Path to cache file
        data: Schema data to cache
    """
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Schema cached to {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def connect_to_database(connection_string: str) -> psycopg.Connection:
    """
    Establish connection to PostgreSQL database

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        Database connection object

    Raises:
        Exception: If connection fails
    """
    try:
        logger.info(f"Connecting to database: {mask_connection_string(connection_string)}")
        conn = psycopg.connect(connection_string)

        # Verify connection
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            logger.info(f"Connected successfully: {version.split(',')[0]}")

        return conn
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise


def get_all_schemas(conn: psycopg.Connection) -> List[str]:
    """
    Get list of all user schemas (excluding system schemas)

    Args:
        conn: Database connection

    Returns:
        List of schema names
    """
    query = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return [row[0] for row in cur.fetchall()]


def get_tables(conn: psycopg.Connection, schema: str = 'public') -> List[Dict]:
    """
    Get all tables in schema with metadata

    Args:
        conn: Database connection
        schema: Schema name (default: 'public')

    Returns:
        List of table dictionaries with metadata
    """
    query = """
        SELECT
            t.table_name,
            t.table_type,
            pg_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)) as size_bytes,
            obj_description((quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))::regclass, 'pg_class') as description
        FROM information_schema.tables t
        WHERE t.table_schema = %s
            AND t.table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY t.table_name
    """

    tables = []
    with conn.cursor() as cur:
        cur.execute(query, (schema,))
        for row in cur.fetchall():
            table_name, table_type, size_bytes, description = row

            # Get row count estimate for base tables
            row_count = None
            if table_type == 'BASE TABLE':
                try:
                    cur.execute(f"""
                        SELECT reltuples::bigint
                        FROM pg_class
                        WHERE oid = %s::regclass
                    """, (f"{schema}.{table_name}",))
                    row_count = cur.fetchone()[0]
                except Exception:
                    pass

            tables.append({
                'name': table_name,
                'type': table_type,
                'size_bytes': size_bytes,
                'size_human': format_bytes(size_bytes) if size_bytes else None,
                'row_count_estimate': row_count,
                'description': description
            })

    return tables


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes into human-readable string

    Args:
        bytes_size: Size in bytes

    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def get_columns(conn: psycopg.Connection, table_name: str, schema: str = 'public') -> List[Dict]:
    """
    Get column details for a table

    Args:
        conn: Database connection
        table_name: Name of the table
        schema: Schema name (default: 'public')

    Returns:
        List of column dictionaries
    """
    query = """
        SELECT
            c.column_name,
            c.data_type,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            c.is_nullable,
            c.column_default,
            c.ordinal_position,
            col_description((quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass, c.ordinal_position) as description
        FROM information_schema.columns c
        WHERE c.table_schema = %s
            AND c.table_name = %s
        ORDER BY c.ordinal_position
    """

    columns = []
    with conn.cursor() as cur:
        cur.execute(query, (schema, table_name))
        for row in cur.fetchall():
            col_name, data_type, char_max_len, num_precision, num_scale, is_nullable, col_default, ordinal_pos, description = row

            # Build full type string
            type_str = data_type
            if char_max_len:
                type_str += f"({char_max_len})"
            elif num_precision and data_type in ('numeric', 'decimal'):
                if num_scale:
                    type_str += f"({num_precision},{num_scale})"
                else:
                    type_str += f"({num_precision})"

            columns.append({
                'name': col_name,
                'type': type_str,
                'nullable': is_nullable == 'YES',
                'default': col_default,
                'position': ordinal_pos,
                'description': description
            })

    return columns


def get_indexes(conn: psycopg.Connection, table_name: str, schema: str = 'public') -> List[Dict]:
    """
    Get index information for a table

    Args:
        conn: Database connection
        table_name: Name of the table
        schema: Schema name (default: 'public')

    Returns:
        List of index dictionaries
    """
    query = """
        SELECT
            i.relname as index_name,
            ix.indisunique as is_unique,
            ix.indisprimary as is_primary,
            am.amname as index_type,
            array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as column_names
        FROM pg_index ix
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_am am ON am.oid = i.relam
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE n.nspname = %s
            AND t.relname = %s
        GROUP BY i.relname, ix.indisunique, ix.indisprimary, am.amname
        ORDER BY i.relname
    """

    indexes = []
    with conn.cursor() as cur:
        cur.execute(query, (schema, table_name))
        for row in cur.fetchall():
            index_name, is_unique, is_primary, index_type, column_names = row
            indexes.append({
                'name': index_name,
                'columns': column_names,
                'unique': is_unique,
                'primary': is_primary,
                'type': index_type
            })

    return indexes


def get_constraints(conn: psycopg.Connection, table_name: str, schema: str = 'public') -> List[Dict]:
    """
    Get constraint information for a table

    Args:
        conn: Database connection
        table_name: Name of the table
        schema: Schema name (default: 'public')

    Returns:
        List of constraint dictionaries
    """
    query = """
        SELECT
            tc.constraint_name,
            tc.constraint_type,
            array_agg(kcu.column_name ORDER BY kcu.ordinal_position) as column_names,
            cc.check_clause
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            AND tc.table_name = kcu.table_name
        LEFT JOIN information_schema.check_constraints cc
            ON tc.constraint_name = cc.constraint_name
        WHERE tc.table_schema = %s
            AND tc.table_name = %s
        GROUP BY tc.constraint_name, tc.constraint_type, cc.check_clause
        ORDER BY tc.constraint_type, tc.constraint_name
    """

    constraints = []
    with conn.cursor() as cur:
        cur.execute(query, (schema, table_name))
        for row in cur.fetchall():
            constraint_name, constraint_type, column_names, check_clause = row
            constraints.append({
                'name': constraint_name,
                'type': constraint_type,
                'columns': column_names if column_names[0] is not None else [],
                'check_clause': check_clause
            })

    return constraints


def scan_full_schema(
    conn: psycopg.Connection,
    schema: str = 'public',
    use_cache: bool = True,
    cache_ttl: int = 3600,
    include_stats: bool = True,
    connection_string: str = None
) -> Dict:
    """
    Perform complete schema scan with optional caching

    Args:
        conn: Database connection
        schema: Schema name (default: 'public')
        use_cache: Whether to use caching (default: True)
        cache_ttl: Cache time-to-live in seconds (default: 3600)
        include_stats: Whether to include statistics (default: True)
        connection_string: Connection string for cache key generation

    Returns:
        Complete schema data dictionary
    """
    # Check cache if enabled
    if use_cache and connection_string:
        cache_path = get_cache_path(connection_string, schema)
        if is_cache_valid(cache_path, cache_ttl):
            logger.info("Loading schema from cache...")
            cached_data = load_cache(cache_path)
            if cached_data:
                return cached_data

    logger.info(f"Scanning schema '{schema}'...")

    # Get all tables
    tables = get_tables(conn, schema)

    schema_data = {
        'schema': schema,
        'scanned_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'table_count': len(tables),
        'tables': []
    }

    # Scan each table
    for table in tables:
        table_name = table['name']
        logger.info(f"  Scanning table: {table_name}")

        table_data = {
            **table,
            'columns': get_columns(conn, table_name, schema),
            'indexes': get_indexes(conn, table_name, schema),
            'constraints': get_constraints(conn, table_name, schema)
        }

        schema_data['tables'].append(table_data)

    # Save to cache if enabled
    if use_cache and connection_string:
        save_cache(cache_path, schema_data)

    return schema_data


def format_schema_output(schema_data: Dict, format_type: str = 'markdown') -> str:
    """
    Format schema data for display

    Args:
        schema_data: Schema data dictionary
        format_type: Output format ('markdown', 'json', or 'compact')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(schema_data, indent=2, default=str)

    elif format_type == 'compact':
        lines = []
        lines.append(f"Schema: {schema_data['schema']}")
        lines.append(f"Tables: {schema_data['table_count']}")
        lines.append(f"Scanned: {schema_data['scanned_at']}")
        lines.append("")

        for table in schema_data['tables']:
            cols = ', '.join([f"{c['name']}:{c['type']}" for c in table['columns'][:5]])
            if len(table['columns']) > 5:
                cols += f", ... ({len(table['columns'])} total)"
            lines.append(f"  {table['name']} ({len(table['columns'])} columns): {cols}")

        return '\n'.join(lines)

    else:  # markdown (default)
        lines = []
        lines.append(f"# Database Schema: {schema_data['schema']}")
        lines.append(f"\nScanned at: {schema_data['scanned_at']}")
        lines.append(f"Total tables: {schema_data['table_count']}")
        lines.append("")

        for table in schema_data['tables']:
            lines.append(f"\n## Table: `{table['name']}`")

            if table.get('description'):
                lines.append(f"\n{table['description']}")

            # Metadata
            metadata = []
            if table.get('type'):
                metadata.append(f"Type: {table['type']}")
            if table.get('row_count_estimate') is not None:
                metadata.append(f"Rows: ~{table['row_count_estimate']:,}")
            if table.get('size_human'):
                metadata.append(f"Size: {table['size_human']}")

            if metadata:
                lines.append(f"\n*{' | '.join(metadata)}*")

            # Columns
            lines.append("\n### Columns")
            lines.append("\n| Column | Type | Nullable | Default | Description |")
            lines.append("|--------|------|----------|---------|-------------|")

            for col in table['columns']:
                nullable = "✓" if col['nullable'] else "✗"
                default = col['default'] or "-"
                description = col.get('description') or ""
                lines.append(f"| `{col['name']}` | {col['type']} | {nullable} | {default} | {description} |")

            # Indexes
            if table['indexes']:
                lines.append("\n### Indexes")
                for idx in table['indexes']:
                    idx_type = []
                    if idx['primary']:
                        idx_type.append("PRIMARY KEY")
                    elif idx['unique']:
                        idx_type.append("UNIQUE")
                    idx_type.append(idx['type'].upper())

                    cols = ', '.join([f"`{c}`" for c in idx['columns']])
                    lines.append(f"- **{idx['name']}** ({' '.join(idx_type)}): {cols}")

            # Constraints
            non_index_constraints = [c for c in table['constraints'] if c['type'] not in ('PRIMARY KEY', 'UNIQUE')]
            if non_index_constraints:
                lines.append("\n### Constraints")
                for const in non_index_constraints:
                    if const['type'] == 'CHECK':
                        lines.append(f"- **{const['name']}** (CHECK): {const['check_clause']}")
                    elif const['type'] == 'FOREIGN KEY':
                        cols = ', '.join([f"`{c}`" for c in const['columns']])
                        lines.append(f"- **{const['name']}** (FOREIGN KEY): {cols}")

        return '\n'.join(lines)


def main():
    """Main entry point for schema scanner"""
    parser = argparse.ArgumentParser(
        description='Scan PostgreSQL database schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan default 'public' schema
  %(prog)s --connection-string "postgresql://user:pass@localhost/dbname"

  # Scan specific schema with JSON output
  %(prog)s --connection-string $DB_URL --schema myschema --output-format json

  # Disable caching
  %(prog)s --connection-string $DB_URL --no-cache

  # List all available schemas
  %(prog)s --connection-string $DB_URL --list-schemas
        """
    )

    parser.add_argument(
        '--connection-string',
        required=True,
        help='PostgreSQL connection string (e.g., postgresql://user:pass@host/dbname)'
    )
    parser.add_argument(
        '--schema',
        default='public',
        help='Schema name to scan (default: public)'
    )
    parser.add_argument(
        '--output-format',
        choices=['markdown', 'json', 'compact'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--cache',
        action='store_true',
        dest='use_cache',
        default=True,
        help='Use caching (default: enabled)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_false',
        dest='use_cache',
        help='Disable caching'
    )
    parser.add_argument(
        '--cache-ttl',
        type=int,
        default=3600,
        help='Cache time-to-live in seconds (default: 3600)'
    )
    parser.add_argument(
        '--list-schemas',
        action='store_true',
        help='List all available schemas and exit'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)  # Quieter output

    try:
        # Connect to database
        conn = connect_to_database(args.connection_string)

        # List schemas if requested
        if args.list_schemas:
            schemas = get_all_schemas(conn)
            print("Available schemas:")
            for schema in schemas:
                print(f"  - {schema}")
            conn.close()
            return 0

        # Scan schema
        schema_data = scan_full_schema(
            conn,
            schema=args.schema,
            use_cache=args.use_cache,
            cache_ttl=args.cache_ttl,
            connection_string=args.connection_string
        )

        # Format and output
        output = format_schema_output(schema_data, args.output_format)
        print(output)

        conn.close()
        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
