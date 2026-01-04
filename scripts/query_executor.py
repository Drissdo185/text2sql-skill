#!/usr/bin/env python3
"""
Query Executor for Text2SQL Skill
Safely executes SQL queries with formatted output
"""

import argparse
import csv
import io
import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import psycopg
except ImportError:
    print("Error: psycopg library not found. Please install it:")
    print("  pip install 'psycopg[binary]'")
    sys.exit(1)

try:
    from tabulate import tabulate
except ImportError:
    print("Error: tabulate library not found. Please install it:")
    print("  pip install tabulate")
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


def connect_to_database(connection_string: str, read_only: bool = True) -> psycopg.Connection:
    """
    Establish connection to PostgreSQL database

    Args:
        connection_string: PostgreSQL connection string
        read_only: Whether to open in read-only mode (default: True)

    Returns:
        Database connection object
    """
    try:
        logger.info(f"Connecting to database: {mask_connection_string(connection_string)}")
        conn = psycopg.connect(connection_string)

        # Set read-only mode if requested
        if read_only:
            conn.read_only = True
            logger.info("Connection opened in READ-ONLY mode")
        else:
            logger.warning("Connection opened in READ-WRITE mode")

        return conn
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise


def is_modification_query(sql: str) -> bool:
    """
    Check if SQL query modifies data

    Args:
        sql: SQL query

    Returns:
        True if query modifies data (INSERT, UPDATE, DELETE, etc.)
    """
    sql_upper = sql.strip().upper()
    modification_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']

    for keyword in modification_keywords:
        if sql_upper.startswith(keyword):
            return True

    return False


def execute_query(
    conn: psycopg.Connection,
    sql: str,
    params: Optional[Dict] = None,
    max_rows: int = 1000
) -> Dict:
    """
    Execute SQL query and return results

    Args:
        conn: Database connection
        sql: SQL query
        params: Query parameters for parameterized queries
        max_rows: Maximum number of rows to return (default: 1000)

    Returns:
        Dictionary with query results:
        {
            'success': bool,
            'rows': List[Dict] or None,
            'row_count': int,
            'columns': List[str],
            'execution_time_ms': float,
            'truncated': bool,
            'error': str or None
        }
    """
    start_time = time.time()

    result = {
        'success': False,
        'rows': None,
        'row_count': 0,
        'columns': [],
        'execution_time_ms': 0,
        'truncated': False,
        'error': None
    }

    try:
        with conn.cursor() as cur:
            # Execute query
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)

            # Check if query returns results
            if cur.description:
                # SELECT query - fetch results
                column_names = [desc[0] for desc in cur.description]
                result['columns'] = column_names

                # Fetch rows with limit
                rows = cur.fetchmany(max_rows + 1)

                # Check if results were truncated
                if len(rows) > max_rows:
                    result['truncated'] = True
                    rows = rows[:max_rows]

                # Convert to list of dictionaries
                result['rows'] = [
                    dict(zip(column_names, row))
                    for row in rows
                ]
                result['row_count'] = len(result['rows'])

            else:
                # INSERT/UPDATE/DELETE query - get affected rows
                result['row_count'] = cur.rowcount if cur.rowcount >= 0 else 0

            conn.commit()
            result['success'] = True

    except Exception as e:
        conn.rollback()
        result['error'] = str(e)
        logger.error(f"Query execution failed: {e}")

    finally:
        execution_time = (time.time() - start_time) * 1000
        result['execution_time_ms'] = execution_time

    return result


def format_results_table(results: Dict) -> str:
    """
    Format results as ASCII table

    Args:
        results: Query results dictionary

    Returns:
        Formatted ASCII table string
    """
    if not results['success']:
        return f"Error: {results['error']}"

    if not results['rows']:
        return f"Query executed successfully. {results['row_count']} row(s) affected."

    # Create table
    table = tabulate(
        results['rows'],
        headers='keys',
        tablefmt='grid',
        numalign='right',
        stralign='left'
    )

    output = [table]

    # Add metadata
    output.append("")
    output.append(f"Rows returned: {results['row_count']}")

    if results['truncated']:
        output.append(f"⚠️  Results truncated (showing first {results['row_count']} rows)")

    output.append(f"Execution time: {results['execution_time_ms']:.2f} ms")

    return '\n'.join(output)


def format_results_json(results: Dict) -> str:
    """
    Format results as JSON

    Args:
        results: Query results dictionary

    Returns:
        JSON string
    """
    # Create clean output structure
    output = {
        'success': results['success'],
        'execution_time_ms': results['execution_time_ms']
    }

    if results['success']:
        output['data'] = results['rows']
        output['row_count'] = results['row_count']
        output['truncated'] = results['truncated']
    else:
        output['error'] = results['error']

    return json.dumps(output, indent=2, default=str)


def format_results_csv(results: Dict) -> str:
    """
    Format results as CSV

    Args:
        results: Query results dictionary

    Returns:
        CSV string
    """
    if not results['success']:
        return f"Error: {results['error']}"

    if not results['rows']:
        return ""

    # Create CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=results['columns'])

    writer.writeheader()
    for row in results['rows']:
        writer.writerow(row)

    return output.getvalue()


def format_results_markdown(results: Dict) -> str:
    """
    Format results as Markdown table

    Args:
        results: Query results dictionary

    Returns:
        Markdown table string
    """
    if not results['success']:
        return f"**Error:** {results['error']}"

    if not results['rows']:
        return f"*Query executed successfully. {results['row_count']} row(s) affected.*"

    # Create markdown table
    table = tabulate(
        results['rows'],
        headers='keys',
        tablefmt='github',
        numalign='right',
        stralign='left'
    )

    output = [table]
    output.append("")
    output.append(f"*{results['row_count']} row(s) returned in {results['execution_time_ms']:.2f} ms*")

    if results['truncated']:
        output.append(f"*⚠️  Results truncated*")

    return '\n'.join(output)


def execute_with_explain(
    conn: psycopg.Connection,
    sql: str,
    params: Optional[Dict] = None,
    analyze: bool = False
) -> Dict:
    """
    Execute query with EXPLAIN ANALYZE

    Args:
        conn: Database connection
        sql: SQL query
        params: Query parameters
        analyze: Whether to actually execute (EXPLAIN ANALYZE)

    Returns:
        Dictionary with query results and execution plan
    """
    # First run EXPLAIN
    explain_cmd = "EXPLAIN (FORMAT JSON, VERBOSE)"
    if analyze:
        explain_cmd = "EXPLAIN (FORMAT JSON, ANALYZE, VERBOSE)"

    explain_sql = f"{explain_cmd} {sql}"

    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(explain_sql, params)
            else:
                cur.execute(explain_sql)

            explain_result = cur.fetchone()[0]

        # Then execute the actual query if ANALYZE wasn't used
        if not analyze:
            query_result = execute_query(conn, sql, params)
        else:
            query_result = {
                'success': True,
                'rows': [],
                'row_count': 0,
                'columns': [],
                'execution_time_ms': explain_result[0].get('Execution Time', 0),
                'truncated': False,
                'error': None
            }

        return {
            'success': True,
            'query_result': query_result,
            'explain': explain_result[0]
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def execute_safe(
    conn: psycopg.Connection,
    sql: str,
    params: Optional[Dict] = None,
    max_rows: int = 1000,
    allow_writes: bool = False
) -> Dict:
    """
    Execute query with safety checks

    Args:
        conn: Database connection
        sql: SQL query
        params: Query parameters
        max_rows: Maximum rows to return
        allow_writes: Whether to allow modification queries

    Returns:
        Query results dictionary
    """
    # Check if query modifies data
    if is_modification_query(sql) and not allow_writes:
        return {
            'success': False,
            'rows': None,
            'row_count': 0,
            'columns': [],
            'execution_time_ms': 0,
            'truncated': False,
            'error': "Modification queries not allowed. Use --allow-writes flag to enable."
        }

    return execute_query(conn, sql, params, max_rows)


def main():
    """Main entry point for query executor"""
    parser = argparse.ArgumentParser(
        description='Execute SQL queries safely with formatted output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute simple SELECT query
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users LIMIT 10"

  # Execute with parameters (safe from SQL injection)
  %(prog)s --connection-string $DB_URL \\
    --sql "SELECT * FROM users WHERE created_at > %(date)s" \\
    --params '{"date": "2024-01-01"}'

  # Output as JSON
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users LIMIT 5" --format json

  # Execute with EXPLAIN
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users WHERE id = 123" --explain

  # Allow modification queries (dangerous!)
  %(prog)s --connection-string $DB_URL \\
    --sql "UPDATE users SET status = 'active' WHERE id = 123" \\
    --allow-writes

  # Read SQL from file
  %(prog)s --connection-string $DB_URL --sql-file query.sql
        """
    )

    parser.add_argument(
        '--connection-string',
        required=True,
        help='PostgreSQL connection string'
    )
    parser.add_argument(
        '--sql',
        help='SQL query to execute'
    )
    parser.add_argument(
        '--sql-file',
        help='File containing SQL query'
    )
    parser.add_argument(
        '--params',
        help='Query parameters as JSON (for parameterized queries)'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv', 'markdown'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Maximum number of rows to return (default: 1000)'
    )
    parser.add_argument(
        '--explain',
        action='store_true',
        help='Run EXPLAIN to show query plan'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Run EXPLAIN ANALYZE (executes query!)'
    )
    parser.add_argument(
        '--allow-writes',
        action='store_true',
        help='Allow INSERT/UPDATE/DELETE queries (default: read-only)'
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
        # Get SQL query
        if args.sql:
            sql = args.sql
        elif args.sql_file:
            with open(args.sql_file, 'r') as f:
                sql = f.read()
        else:
            print("Error: Either --sql or --sql-file is required")
            return 1

        # Parse parameters if provided
        params = None
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --params: {e}")
                return 1

        # Connect to database
        read_only = not args.allow_writes
        conn = connect_to_database(args.connection_string, read_only=read_only)

        # Execute query
        if args.explain or args.analyze:
            result = execute_with_explain(conn, sql, params, analyze=args.analyze)

            if result['success']:
                # Show query results
                if args.format == 'table':
                    output = format_results_table(result['query_result'])
                elif args.format == 'json':
                    output = json.dumps(result, indent=2, default=str)
                elif args.format == 'csv':
                    output = format_results_csv(result['query_result'])
                else:  # markdown
                    output = format_results_markdown(result['query_result'])

                print(output)

                # Show execution plan
                print("\n## Execution Plan\n")
                print(f"**Planning Time:** {result['explain'].get('Planning Time', 0):.2f} ms")

                if result['explain'].get('Execution Time'):
                    print(f"**Execution Time:** {result['explain']['Execution Time']:.2f} ms")

                print(f"**Total Cost:** {result['explain']['Plan'].get('Total Cost', 0):.2f}")
                print(f"**Estimated Rows:** {result['explain']['Plan'].get('Plan Rows', 0):,}")
            else:
                print(f"Error: {result['error']}")
                return 1

        else:
            result = execute_safe(conn, sql, params, args.limit, args.allow_writes)

            # Format output
            if args.format == 'table':
                output = format_results_table(result)
            elif args.format == 'json':
                output = format_results_json(result)
            elif args.format == 'csv':
                output = format_results_csv(result)
            else:  # markdown
                output = format_results_markdown(result)

            print(output)

        conn.close()

        # Return exit code based on success
        return 0 if result['success'] else 1

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
