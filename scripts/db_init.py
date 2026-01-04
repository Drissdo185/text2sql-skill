#!/usr/bin/env python3
"""
Database Initialization Script for Text2SQL Skill
Combines schema scanning and relationship analysis for comprehensive database discovery
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

try:
    import psycopg
except ImportError:
    print("Error: psycopg library not found. Please install it:")
    print("  pip install 'psycopg[binary]'")
    sys.exit(1)

# Import functions from other scripts
import os
sys.path.insert(0, os.path.dirname(__file__))

from schema_scanner import (
    connect_to_database,
    mask_connection_string,
    scan_full_schema,
    get_all_schemas
)
from relationship_analyzer import (
    get_foreign_keys,
    detect_many_to_many,
    build_relationship_graph
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_context_path(connection_string: str) -> str:
    """
    Get path for storing database context

    Args:
        connection_string: Database connection string

    Returns:
        Path to context file
    """
    import hashlib
    masked = mask_connection_string(connection_string)
    hash_obj = hashlib.md5(masked.encode())
    context_hash = hash_obj.hexdigest()[:12]

    return f"/tmp/text2sql_context_{context_hash}.json"


def initialize_database(
    connection_string: str,
    schema: str = 'public',
    use_cache: bool = True,
    cache_ttl: int = 3600
) -> Dict:
    """
    Initialize database by scanning schema and analyzing relationships

    Args:
        connection_string: PostgreSQL connection string
        schema: Schema name (default: 'public')
        use_cache: Whether to use caching
        cache_ttl: Cache TTL in seconds

    Returns:
        Complete database context dictionary
    """
    logger.info("=" * 60)
    logger.info("DATABASE INITIALIZATION")
    logger.info("=" * 60)
    logger.info("")

    # Connect to database
    logger.info(f"Connecting to: {mask_connection_string(connection_string)}")
    conn = connect_to_database(connection_string)

    # Get database metadata
    logger.info(f"Scanning schema: {schema}")
    logger.info("")

    # Step 1: Scan schema
    logger.info("[1/3] Scanning database schema...")
    schema_data = scan_full_schema(
        conn,
        schema=schema,
        use_cache=use_cache,
        cache_ttl=cache_ttl,
        connection_string=connection_string
    )

    tables_found = schema_data['table_count']
    logger.info(f"✓ Found {tables_found} tables")

    # Step 2: Analyze relationships
    logger.info("")
    logger.info("[2/3] Analyzing table relationships...")
    foreign_keys = get_foreign_keys(conn, schema)
    many_to_many = detect_many_to_many(conn, schema)
    relationship_graph = build_relationship_graph(conn, schema)

    logger.info(f"✓ Found {len(foreign_keys)} foreign key relationships")
    logger.info(f"✓ Detected {len(many_to_many)} many-to-many relationships")

    # Step 3: Build context
    logger.info("")
    logger.info("[3/3] Building database context...")

    context = {
        'connection_info': {
            'masked_connection': mask_connection_string(connection_string),
            'schema': schema,
            'initialized_at': schema_data['scanned_at']
        },
        'schema': schema_data,
        'relationships': {
            'foreign_keys': foreign_keys,
            'many_to_many': many_to_many,
            'graph': relationship_graph
        },
        'summary': {
            'total_tables': tables_found,
            'total_foreign_keys': len(foreign_keys),
            'total_many_to_many': len(many_to_many),
            'tables': [table['name'] for table in schema_data['tables']]
        }
    }

    # Save context
    context_path = get_db_context_path(connection_string)
    with open(context_path, 'w') as f:
        json.dump(context, f, indent=2, default=str)

    logger.info(f"✓ Context saved to: {context_path}")

    conn.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("INITIALIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Database is ready for natural language queries!")
    logger.info("")

    return context


def load_database_context(connection_string: str) -> Optional[Dict]:
    """
    Load previously initialized database context

    Args:
        connection_string: Database connection string

    Returns:
        Database context or None if not found
    """
    context_path = get_db_context_path(connection_string)

    if not os.path.exists(context_path):
        return None

    try:
        with open(context_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load context: {e}")
        return None


def format_context_summary(context: Dict) -> str:
    """
    Format database context as readable summary

    Args:
        context: Database context dictionary

    Returns:
        Formatted markdown string
    """
    lines = []
    lines.append("# Database Context Summary")
    lines.append("")

    # Connection info
    info = context['connection_info']
    lines.append(f"**Database:** {info['masked_connection']}")
    lines.append(f"**Schema:** {info['schema']}")
    lines.append(f"**Initialized:** {info['initialized_at']}")
    lines.append("")

    # Summary stats
    summary = context['summary']
    lines.append("## Statistics")
    lines.append(f"- **Tables:** {summary['total_tables']}")
    lines.append(f"- **Foreign Keys:** {summary['total_foreign_keys']}")
    lines.append(f"- **Many-to-Many Relationships:** {summary['total_many_to_many']}")
    lines.append("")

    # Tables
    lines.append("## Available Tables")
    for table_name in summary['tables']:
        # Find table details
        table_data = next(
            (t for t in context['schema']['tables'] if t['name'] == table_name),
            None
        )
        if table_data:
            row_count = table_data.get('row_count_estimate', 0)
            col_count = len(table_data.get('columns', []))
            lines.append(f"- **{table_name}** ({col_count} columns, ~{row_count:,} rows)")

    lines.append("")

    # Key relationships
    if context['relationships']['foreign_keys']:
        lines.append("## Key Relationships")

        # Group by source table
        from collections import defaultdict
        by_table = defaultdict(list)
        for fk in context['relationships']['foreign_keys']:
            by_table[fk['from_table']].append(fk)

        for table_name in sorted(by_table.keys())[:5]:  # Show first 5
            lines.append(f"### {table_name}")
            for fk in by_table[table_name][:3]:  # Show first 3 FKs per table
                lines.append(f"- `{fk['from_column']}` → `{fk['to_table']}.{fk['to_column']}`")

        if len(by_table) > 5:
            lines.append(f"\n*... and {len(by_table) - 5} more tables with relationships*")

    lines.append("")

    # Many-to-many
    if context['relationships']['many_to_many']:
        lines.append("## Many-to-Many Relationships")
        for m2m in context['relationships']['many_to_many']:
            lines.append(f"- **{m2m['table1']}** ↔ **{m2m['table2']}** (via `{m2m['junction_table']}`)")
        lines.append("")

    lines.append("---")
    lines.append("*Ready to process natural language queries!*")

    return '\n'.join(lines)


def main():
    """Main entry point for database initialization"""
    parser = argparse.ArgumentParser(
        description='Initialize database for Text2SQL queries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database
  %(prog)s --connection-string "postgresql://user:pass@localhost/dbname"

  # Initialize specific schema
  %(prog)s --connection-string $DB_URL --schema inventory

  # Force refresh (ignore cache)
  %(prog)s --connection-string $DB_URL --no-cache

  # Load existing context
  %(prog)s --connection-string $DB_URL --load
        """
    )

    parser.add_argument(
        '--connection-string',
        required=True,
        help='PostgreSQL connection string'
    )
    parser.add_argument(
        '--schema',
        default='public',
        help='Schema name (default: public)'
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
        help='Cache TTL in seconds (default: 3600)'
    )
    parser.add_argument(
        '--load',
        action='store_true',
        help='Load existing context without re-scanning'
    )
    parser.add_argument(
        '--output-format',
        choices=['summary', 'json'],
        default='summary',
        help='Output format (default: summary)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    try:
        # Load existing context if requested
        if args.load:
            context = load_database_context(args.connection_string)
            if not context:
                print("No existing context found. Run without --load to initialize.")
                return 1
            print(f"Loaded context from: {get_db_context_path(args.connection_string)}")
        else:
            # Initialize database
            context = initialize_database(
                args.connection_string,
                schema=args.schema,
                use_cache=args.use_cache,
                cache_ttl=args.cache_ttl
            )

        # Output results
        if args.output_format == 'json':
            print(json.dumps(context, indent=2, default=str))
        else:
            print(format_context_summary(context))

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
