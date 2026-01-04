#!/usr/bin/env python3
"""
Relationship Analyzer for Text2SQL Skill
Detects and analyzes table relationships for intelligent JOIN generation
"""

import argparse
import json
import logging
import sys
from collections import defaultdict, deque
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
    """Mask password in connection string for safe display"""
    try:
        parsed = urlparse(conn_str)
        if parsed.password:
            return conn_str.replace(parsed.password, '***')
        return conn_str
    except Exception:
        return "***connection string***"


def connect_to_database(connection_string: str) -> psycopg.Connection:
    """Establish connection to PostgreSQL database"""
    try:
        logger.info(f"Connecting to database: {mask_connection_string(connection_string)}")
        conn = psycopg.connect(connection_string)
        return conn
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise


def get_foreign_keys(conn: psycopg.Connection, schema: str = 'public') -> List[Dict]:
    """
    Extract all foreign key relationships in schema

    Args:
        conn: Database connection
        schema: Schema name (default: 'public')

    Returns:
        List of foreign key relationship dictionaries
    """
    query = """
        SELECT
            tc.constraint_name,
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = %s
        ORDER BY tc.table_name, tc.constraint_name
    """

    foreign_keys = []
    with conn.cursor() as cur:
        cur.execute(query, (schema,))
        for row in cur.fetchall():
            constraint_name, table_name, column_name, foreign_table_name, foreign_column_name, update_rule, delete_rule = row
            foreign_keys.append({
                'constraint_name': constraint_name,
                'from_table': table_name,
                'from_column': column_name,
                'to_table': foreign_table_name,
                'to_column': foreign_column_name,
                'on_update': update_rule,
                'on_delete': delete_rule
            })

    return foreign_keys


def detect_many_to_many(conn: psycopg.Connection, schema: str = 'public') -> List[Dict]:
    """
    Identify junction tables indicating many-to-many relationships

    A junction table typically:
    - Has a composite primary key
    - Has exactly 2 foreign keys
    - May have only FK columns or a few additional columns

    Args:
        conn: Database connection
        schema: Schema name (default: 'public')

    Returns:
        List of many-to-many relationship dictionaries
    """
    foreign_keys = get_foreign_keys(conn, schema)

    # Group foreign keys by table
    fk_by_table = defaultdict(list)
    for fk in foreign_keys:
        fk_by_table[fk['from_table']].append(fk)

    many_to_many = []

    for table_name, fks in fk_by_table.items():
        # Junction table typically has exactly 2 foreign keys
        if len(fks) == 2:
            # Check if table has minimal columns (mostly just FKs)
            query = """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
            """

            with conn.cursor() as cur:
                cur.execute(query, (schema, table_name))
                column_count = cur.fetchone()[0]

            # If column count is 2-4 (the 2 FKs plus maybe id and timestamp), likely a junction table
            if column_count <= 4:
                many_to_many.append({
                    'junction_table': table_name,
                    'table1': fks[0]['to_table'],
                    'table1_column': fks[0]['to_column'],
                    'table2': fks[1]['to_table'],
                    'table2_column': fks[1]['to_column'],
                    'junction_column1': fks[0]['from_column'],
                    'junction_column2': fks[1]['from_column']
                })

    return many_to_many


def build_relationship_graph(conn: psycopg.Connection, schema: str = 'public') -> Dict:
    """
    Build a graph of all table relationships

    Args:
        conn: Database connection
        schema: Schema name (default: 'public')

    Returns:
        Dictionary representing relationship graph:
        {
            'nodes': [table names],
            'edges': [{from, to, columns}],
            'foreign_keys': [fk details],
            'many_to_many': [m2m details]
        }
    """
    foreign_keys = get_foreign_keys(conn, schema)
    many_to_many = detect_many_to_many(conn, schema)

    # Build adjacency list
    adjacency = defaultdict(list)
    nodes = set()

    for fk in foreign_keys:
        from_table = fk['from_table']
        to_table = fk['to_table']

        nodes.add(from_table)
        nodes.add(to_table)

        adjacency[from_table].append({
            'to': to_table,
            'from_column': fk['from_column'],
            'to_column': fk['to_column'],
            'constraint': fk['constraint_name']
        })

        # Add reverse relationship
        adjacency[to_table].append({
            'to': from_table,
            'from_column': fk['to_column'],
            'to_column': fk['from_column'],
            'constraint': fk['constraint_name'],
            'reverse': True
        })

    return {
        'nodes': sorted(list(nodes)),
        'adjacency': dict(adjacency),
        'foreign_keys': foreign_keys,
        'many_to_many': many_to_many
    }


def find_path_between_tables(
    graph: Dict,
    start_table: str,
    end_table: str
) -> Optional[List[Dict]]:
    """
    Find shortest path between two tables using BFS

    Args:
        graph: Relationship graph from build_relationship_graph()
        start_table: Starting table name
        end_table: Target table name

    Returns:
        List of join steps or None if no path exists
        Each step: {'from': table1, 'to': table2, 'on': {'from_col': ..., 'to_col': ...}}
    """
    if start_table not in graph['adjacency'] or end_table not in graph['adjacency']:
        return None

    if start_table == end_table:
        return []

    # BFS to find shortest path
    queue = deque([(start_table, [])])
    visited = {start_table}

    while queue:
        current_table, path = queue.popleft()

        for edge in graph['adjacency'][current_table]:
            next_table = edge['to']

            if next_table in visited:
                continue

            new_path = path + [{
                'from': current_table,
                'to': next_table,
                'from_column': edge.get('from_column'),
                'to_column': edge.get('to_column'),
                'constraint': edge.get('constraint'),
                'reverse': edge.get('reverse', False)
            }]

            if next_table == end_table:
                return new_path

            visited.add(next_table)
            queue.append((next_table, new_path))

    return None


def suggest_join_pattern(
    conn: psycopg.Connection,
    table1: str,
    table2: str,
    schema: str = 'public'
) -> Dict:
    """
    Suggest JOIN SQL for connecting two tables

    Args:
        conn: Database connection
        table1: First table name
        table2: Second table name
        schema: Schema name (default: 'public')

    Returns:
        Dictionary with join suggestion:
        {
            'success': bool,
            'path': [join steps] or None,
            'sql': generated SQL or None,
            'explanation': human-readable explanation
        }
    """
    graph = build_relationship_graph(conn, schema)
    path = find_path_between_tables(graph, table1, table2)

    if not path:
        return {
            'success': False,
            'path': None,
            'sql': None,
            'explanation': f"No foreign key relationship found between '{table1}' and '{table2}'"
        }

    # Generate SQL
    sql_parts = [f"FROM {path[0]['from']}"]

    for step in path:
        join_type = "JOIN"
        on_clause = f"{step['from']}.{step['from_column']} = {step['to']}.{step['to_column']}"
        sql_parts.append(f"{join_type} {step['to']} ON {on_clause}")

    sql = '\n'.join(sql_parts)

    # Generate explanation
    if len(path) == 1:
        explanation = f"Direct relationship: {table1}.{path[0]['from_column']} → {table2}.{path[0]['to_column']}"
    else:
        steps = []
        for step in path:
            steps.append(f"{step['from']} → {step['to']}")
        explanation = f"Path through {len(path)} tables: {' → '.join([s.split(' → ')[0] for s in steps] + [path[-1]['to']])}"

    return {
        'success': True,
        'path': path,
        'sql': sql,
        'explanation': explanation
    }


def generate_join_query(
    conn: psycopg.Connection,
    tables: List[str],
    schema: str = 'public',
    select_all: bool = False
) -> Dict:
    """
    Generate multi-table JOIN query based on relationships

    Args:
        conn: Database connection
        tables: List of table names to join
        schema: Schema name (default: 'public')
        select_all: Whether to SELECT * from all tables (default: False)

    Returns:
        Dictionary with generated query:
        {
            'success': bool,
            'sql': generated SQL or None,
            'explanation': human-readable explanation,
            'paths': join paths used
        }
    """
    if len(tables) < 2:
        return {
            'success': False,
            'sql': None,
            'explanation': "Need at least 2 tables to generate JOIN",
            'paths': []
        }

    graph = build_relationship_graph(conn, schema)

    # Find path connecting all tables (start with first table, connect to others)
    base_table = tables[0]
    all_paths = []
    joined_tables = {base_table}

    for target_table in tables[1:]:
        # Try to find path from any already-joined table to the target
        path = None
        for joined_table in joined_tables:
            path = find_path_between_tables(graph, joined_table, target_table)
            if path:
                break

        if not path:
            return {
                'success': False,
                'sql': None,
                'explanation': f"Cannot find path from {base_table} to {target_table}",
                'paths': all_paths
            }

        all_paths.extend(path)

        # Add all tables in path to joined set
        for step in path:
            joined_tables.add(step['to'])

    # Remove duplicate joins (if same table appears in multiple paths)
    unique_joins = []
    seen_joins = set()

    for step in all_paths:
        join_key = (step['from'], step['to'], step['from_column'], step['to_column'])
        if join_key not in seen_joins:
            unique_joins.append(step)
            seen_joins.add(join_key)

    # Generate SQL
    if select_all:
        select_clause = "SELECT *"
    else:
        # Select primary columns from each table
        select_clause = "SELECT\n    " + ",\n    ".join([f"{t}.*" for t in tables])

    sql_parts = [select_clause, f"FROM {base_table}"]

    for step in unique_joins:
        join_type = "JOIN"
        on_clause = f"{step['from']}.{step['from_column']} = {step['to']}.{step['to_column']}"
        sql_parts.append(f"{join_type} {step['to']} ON {on_clause}")

    sql = '\n'.join(sql_parts)

    explanation = f"Generated JOIN connecting {len(tables)} tables using {len(unique_joins)} relationships"

    return {
        'success': True,
        'sql': sql,
        'explanation': explanation,
        'paths': unique_joins
    }


def format_relationships_output(
    foreign_keys: List[Dict],
    many_to_many: List[Dict],
    format_type: str = 'markdown'
) -> str:
    """
    Format relationship data for display

    Args:
        foreign_keys: List of foreign key relationships
        many_to_many: List of many-to-many relationships
        format_type: Output format ('markdown' or 'json')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps({
            'foreign_keys': foreign_keys,
            'many_to_many': many_to_many
        }, indent=2)

    # Markdown format
    lines = []
    lines.append("# Database Relationships")
    lines.append("")

    # Foreign Keys
    lines.append(f"## Foreign Keys ({len(foreign_keys)})")
    lines.append("")

    if foreign_keys:
        # Group by source table
        by_table = defaultdict(list)
        for fk in foreign_keys:
            by_table[fk['from_table']].append(fk)

        for table_name in sorted(by_table.keys()):
            lines.append(f"### {table_name}")
            for fk in by_table[table_name]:
                arrow = "→"
                lines.append(
                    f"- `{fk['from_column']}` {arrow} `{fk['to_table']}.{fk['to_column']}` "
                    f"(ON DELETE: {fk['on_delete']}, ON UPDATE: {fk['on_update']})"
                )
            lines.append("")
    else:
        lines.append("*No foreign keys found*")
        lines.append("")

    # Many-to-Many
    lines.append(f"## Many-to-Many Relationships ({len(many_to_many)})")
    lines.append("")

    if many_to_many:
        for m2m in many_to_many:
            lines.append(f"### {m2m['table1']} ↔ {m2m['table2']}")
            lines.append(f"- Junction table: `{m2m['junction_table']}`")
            lines.append(
                f"- {m2m['table1']}.{m2m['table1_column']} ← "
                f"{m2m['junction_table']}.{m2m['junction_column1']}"
            )
            lines.append(
                f"- {m2m['table2']}.{m2m['table2_column']} ← "
                f"{m2m['junction_table']}.{m2m['junction_column2']}"
            )
            lines.append("")
    else:
        lines.append("*No many-to-many relationships detected*")
        lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point for relationship analyzer"""
    parser = argparse.ArgumentParser(
        description='Analyze PostgreSQL table relationships',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all foreign key relationships
  %(prog)s --connection-string "postgresql://user:pass@localhost/dbname"

  # Suggest JOIN between two tables
  %(prog)s --connection-string $DB_URL --table1 orders --table2 customers --suggest-join

  # Generate multi-table JOIN
  %(prog)s --connection-string $DB_URL --generate-join orders customers products

  # Detect many-to-many relationships
  %(prog)s --connection-string $DB_URL --detect-m2m
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
        '--table1',
        help='First table name (for JOIN suggestion)'
    )
    parser.add_argument(
        '--table2',
        help='Second table name (for JOIN suggestion)'
    )
    parser.add_argument(
        '--suggest-join',
        action='store_true',
        help='Suggest JOIN pattern between table1 and table2'
    )
    parser.add_argument(
        '--generate-join',
        nargs='+',
        metavar='TABLE',
        help='Generate multi-table JOIN query'
    )
    parser.add_argument(
        '--detect-m2m',
        action='store_true',
        help='Detect many-to-many relationships'
    )
    parser.add_argument(
        '--output-format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
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
        logger.setLevel(logging.WARNING)

    try:
        # Connect to database
        conn = connect_to_database(args.connection_string)

        # Suggest JOIN between two tables
        if args.suggest_join:
            if not args.table1 or not args.table2:
                print("Error: --suggest-join requires --table1 and --table2")
                return 1

            result = suggest_join_pattern(conn, args.table1, args.table2, args.schema)

            if args.output_format == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(f"# JOIN Suggestion: {args.table1} → {args.table2}\n")
                print(f"**{result['explanation']}**\n")

                if result['success']:
                    print("```sql")
                    print(result['sql'])
                    print("```")
                else:
                    print("*No direct relationship found*")

        # Generate multi-table JOIN
        elif args.generate_join:
            result = generate_join_query(conn, args.generate_join, args.schema)

            if args.output_format == 'json':
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"# Multi-Table JOIN\n")
                print(f"**{result['explanation']}**\n")

                if result['success']:
                    print("```sql")
                    print(result['sql'])
                    print("```")
                else:
                    print(f"*Error: {result['explanation']}*")

        # Detect many-to-many
        elif args.detect_m2m:
            many_to_many = detect_many_to_many(conn, args.schema)

            if args.output_format == 'json':
                print(json.dumps({'many_to_many': many_to_many}, indent=2))
            else:
                output = format_relationships_output([], many_to_many)
                print(output)

        # Default: show all relationships
        else:
            foreign_keys = get_foreign_keys(conn, args.schema)
            many_to_many = detect_many_to_many(conn, args.schema)

            output = format_relationships_output(foreign_keys, many_to_many, args.output_format)
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
