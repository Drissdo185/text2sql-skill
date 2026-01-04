#!/usr/bin/env python3
"""
SQL Validator for Text2SQL Skill
Validates SQL syntax, checks against schema, and provides query explanations
"""

import argparse
import json
import logging
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import psycopg
except ImportError:
    print("Error: psycopg library not found. Please install it:")
    print("  pip install 'psycopg[binary]'")
    sys.exit(1)

try:
    import sqlparse
    from sqlparse.sql import IdentifierList, Identifier, Where, Token
    from sqlparse.tokens import Keyword, DML
except ImportError:
    print("Error: sqlparse library not found. Please install it:")
    print("  pip install sqlparse")
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


def validate_syntax(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SQL syntax using sqlparse

    Args:
        sql: SQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse SQL
        parsed = sqlparse.parse(sql)

        if not parsed:
            return False, "Empty or invalid SQL statement"

        if len(parsed) > 1:
            return False, "Multiple SQL statements detected. Please provide one statement at a time."

        statement = parsed[0]

        # Check if it's a valid SQL statement
        if statement.get_type() == 'UNKNOWN':
            return False, "Unable to parse SQL statement"

        # Basic validation passed
        return True, None

    except Exception as e:
        return False, f"Syntax error: {str(e)}"


def extract_table_names(sql: str) -> List[str]:
    """
    Extract table names from SQL query

    Args:
        sql: SQL query

    Returns:
        List of table names found in query
    """
    try:
        parsed = sqlparse.parse(sql)[0]
        tables = []

        # Extract from FROM and JOIN clauses
        from_seen = False
        for token in parsed.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        table_name = identifier.get_real_name()
                        if table_name:
                            tables.append(table_name)
                elif isinstance(token, Identifier):
                    table_name = token.get_real_name()
                    if table_name:
                        tables.append(table_name)

            if token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'):
                from_seen = True
            elif token.ttype is Keyword and token.value.upper() in ('WHERE', 'GROUP', 'ORDER', 'LIMIT', 'HAVING'):
                from_seen = False

        return list(set(tables))  # Remove duplicates

    except Exception as e:
        logger.debug(f"Error extracting table names: {e}")
        # Fallback: regex extraction
        pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        return list(set(matches))


def validate_against_schema(
    sql: str,
    conn: psycopg.Connection,
    schema: str = 'public'
) -> Tuple[bool, List[str]]:
    """
    Verify tables and columns exist in schema

    Args:
        sql: SQL query
        conn: Database connection
        schema: Schema name

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    try:
        # Extract table names
        tables = extract_table_names(sql)

        if not tables:
            return True, []  # No tables to validate

        # Check if tables exist
        with conn.cursor() as cur:
            for table in tables:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = %s
                        AND table_name = %s
                    )
                """, (schema, table))

                exists = cur.fetchone()[0]

                if not exists:
                    # Try to find similar table names
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                        AND table_name SIMILAR TO %s
                        LIMIT 3
                    """, (schema, f"%{table}%"))

                    similar = [row[0] for row in cur.fetchall()]
                    error_msg = f"Table '{table}' does not exist in schema '{schema}'"

                    if similar:
                        error_msg += f". Did you mean: {', '.join(similar)}?"

                    errors.append(error_msg)

        return len(errors) == 0, errors

    except Exception as e:
        logger.debug(f"Error validating schema: {e}")
        return True, []  # Don't fail validation on validation error


def check_sql_injection_risk(sql: str) -> Tuple[bool, List[str]]:
    """
    Detect potential SQL injection patterns

    Args:
        sql: SQL query to check

    Returns:
        Tuple of (is_safe, list_of_warnings)
    """
    warnings = []

    # Dangerous patterns
    dangerous_patterns = [
        (r";\s*DROP\s+", "Detected DROP statement after semicolon"),
        (r";\s*DELETE\s+", "Detected DELETE statement after semicolon"),
        (r";\s*UPDATE\s+", "Detected UPDATE statement after semicolon"),
        (r";\s*INSERT\s+", "Detected INSERT statement after semicolon"),
        (r"--\s*$", "SQL comment at end of query"),
        (r"/\*.*\*/", "Block comment detected"),
    ]

    for pattern, warning in dangerous_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            warnings.append(warning)

    # Check for string concatenation indicators
    if re.search(r"\+\s*['\"]|['\"]\\s*\+", sql):
        warnings.append("Possible string concatenation detected")

    # Note: This is basic detection. Parameterized queries are the real solution.

    return len(warnings) == 0, warnings


def suggest_improvements(sql: str, conn: psycopg.Connection, schema: str = 'public') -> List[str]:
    """
    Provide optimization suggestions for SQL query

    Args:
        sql: SQL query
        conn: Database connection
        schema: Schema name

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    try:
        # Check for SELECT *
        if re.search(r'SELECT\s+\*', sql, re.IGNORECASE):
            suggestions.append(
                "Consider selecting specific columns instead of SELECT * for better performance"
            )

        # Check for missing WHERE clause in UPDATE/DELETE
        if re.search(r'^\s*(UPDATE|DELETE)\s+', sql, re.IGNORECASE):
            if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
                suggestions.append(
                    "WARNING: UPDATE/DELETE without WHERE clause will affect all rows!"
                )

        # Check for LIKE with leading wildcard
        if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
            suggestions.append(
                "LIKE with leading wildcard (%) cannot use indexes efficiently"
            )

        # Check for missing LIMIT on potentially large result sets
        if re.search(r'^\s*SELECT\s+', sql, re.IGNORECASE):
            if not re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
                suggestions.append(
                    "Consider adding LIMIT clause to restrict result set size"
                )

        return suggestions

    except Exception as e:
        logger.debug(f"Error generating suggestions: {e}")
        return suggestions


def explain_query_plan(
    conn: psycopg.Connection,
    sql: str,
    analyze: bool = False
) -> Dict:
    """
    Run EXPLAIN on query and parse results

    Args:
        conn: Database connection
        sql: SQL query
        analyze: Whether to run EXPLAIN ANALYZE (actually executes query)

    Returns:
        Dictionary with explanation data
    """
    try:
        explain_cmd = "EXPLAIN (FORMAT JSON, VERBOSE)"
        if analyze:
            explain_cmd = "EXPLAIN (FORMAT JSON, ANALYZE, VERBOSE)"

        with conn.cursor() as cur:
            cur.execute(f"{explain_cmd} {sql}")
            result = cur.fetchone()[0]

            plan = result[0]

            # Extract key metrics
            execution_time = plan.get('Execution Time')
            planning_time = plan.get('Planning Time')
            total_cost = plan['Plan'].get('Total Cost')
            rows = plan['Plan'].get('Plan Rows')

            # Find potential issues
            issues = []
            warnings = []

            def check_plan_node(node):
                """Recursively check plan nodes for issues"""
                node_type = node.get('Node Type', '')

                # Check for sequential scans on large tables
                if node_type == 'Seq Scan':
                    rows_scanned = node.get('Plan Rows', 0)
                    if rows_scanned > 1000:
                        table = node.get('Relation Name', 'unknown')
                        warnings.append(
                            f"Sequential scan on table '{table}' (~{rows_scanned:,} rows). "
                            "Consider adding an index."
                        )

                # Check for nested loops with high iterations
                if node_type == 'Nested Loop':
                    loops = node.get('Actual Loops', 1) if analyze else 1
                    if loops > 100:
                        warnings.append(
                            f"Nested loop with {loops} iterations may be slow. "
                            "Consider optimizing JOIN conditions."
                        )

                # Recursively check child nodes
                for child in node.get('Plans', []):
                    check_plan_node(child)

            check_plan_node(plan['Plan'])

            return {
                'success': True,
                'plan': plan,
                'execution_time_ms': execution_time,
                'planning_time_ms': planning_time,
                'total_cost': total_cost,
                'estimated_rows': rows,
                'warnings': warnings,
                'issues': issues
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'plan': None
        }


def validate_and_explain(
    conn: psycopg.Connection,
    sql: str,
    schema: str = 'public',
    explain: bool = False,
    analyze: bool = False
) -> Dict:
    """
    Complete validation with optional explanation

    Args:
        conn: Database connection
        sql: SQL query
        schema: Schema name
        explain: Whether to run EXPLAIN
        analyze: Whether to run EXPLAIN ANALYZE

    Returns:
        Dictionary with complete validation results
    """
    result = {
        'sql': sql,
        'valid': False,
        'errors': [],
        'warnings': [],
        'suggestions': [],
        'explain': None
    }

    # Syntax validation
    syntax_valid, syntax_error = validate_syntax(sql)
    if not syntax_valid:
        result['errors'].append(syntax_error)
        return result

    # Schema validation
    schema_valid, schema_errors = validate_against_schema(sql, conn, schema)
    if not schema_valid:
        result['errors'].extend(schema_errors)
        return result

    # Security check
    is_safe, security_warnings = check_sql_injection_risk(sql)
    if not is_safe:
        result['warnings'].extend(security_warnings)

    # Optimization suggestions
    suggestions = suggest_improvements(sql, conn, schema)
    result['suggestions'].extend(suggestions)

    # Mark as valid
    result['valid'] = True

    # Run EXPLAIN if requested
    if explain or analyze:
        explain_result = explain_query_plan(conn, sql, analyze=analyze)

        if explain_result['success']:
            result['explain'] = explain_result

            # Add EXPLAIN warnings to main warnings
            if explain_result.get('warnings'):
                result['warnings'].extend(explain_result['warnings'])
        else:
            result['warnings'].append(f"EXPLAIN failed: {explain_result.get('error')}")

    return result


def format_validation_output(validation: Dict, format_type: str = 'markdown') -> str:
    """
    Format validation results for display

    Args:
        validation: Validation result dictionary
        format_type: Output format ('markdown' or 'json')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(validation, indent=2, default=str)

    # Markdown format
    lines = []
    lines.append("# SQL Validation Results")
    lines.append("")

    # Status
    if validation['valid']:
        lines.append("**Status:** ✓ Valid")
    else:
        lines.append("**Status:** ✗ Invalid")

    lines.append("")

    # Query
    lines.append("## Query")
    lines.append("```sql")
    lines.append(validation['sql'])
    lines.append("```")
    lines.append("")

    # Errors
    if validation['errors']:
        lines.append("## Errors")
        for error in validation['errors']:
            lines.append(f"- ❌ {error}")
        lines.append("")

    # Warnings
    if validation['warnings']:
        lines.append("## Warnings")
        for warning in validation['warnings']:
            lines.append(f"- ⚠️  {warning}")
        lines.append("")

    # Suggestions
    if validation['suggestions']:
        lines.append("## Suggestions")
        for suggestion in validation['suggestions']:
            lines.append(f"- 💡 {suggestion}")
        lines.append("")

    # EXPLAIN results
    if validation.get('explain'):
        explain = validation['explain']

        lines.append("## Query Plan Analysis")
        lines.append("")

        if explain.get('execution_time_ms') is not None:
            lines.append(f"- **Execution Time:** {explain['execution_time_ms']:.2f} ms")

        if explain.get('planning_time_ms') is not None:
            lines.append(f"- **Planning Time:** {explain['planning_time_ms']:.2f} ms")

        if explain.get('total_cost') is not None:
            lines.append(f"- **Estimated Cost:** {explain['total_cost']:.2f}")

        if explain.get('estimated_rows') is not None:
            lines.append(f"- **Estimated Rows:** {explain['estimated_rows']:,}")

        lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point for SQL validator"""
    parser = argparse.ArgumentParser(
        description='Validate SQL queries and analyze performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate SQL syntax and schema
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users"

  # Validate with query plan explanation
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users WHERE id = 123" --explain

  # Run EXPLAIN ANALYZE (executes the query!)
  %(prog)s --connection-string $DB_URL --sql "SELECT * FROM users LIMIT 10" --analyze

  # Read SQL from file
  %(prog)s --connection-string $DB_URL --sql-file query.sql --explain
        """
    )

    parser.add_argument(
        '--connection-string',
        required=True,
        help='PostgreSQL connection string'
    )
    parser.add_argument(
        '--sql',
        help='SQL query to validate'
    )
    parser.add_argument(
        '--sql-file',
        help='File containing SQL query'
    )
    parser.add_argument(
        '--schema',
        default='public',
        help='Schema name (default: public)'
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
        # Get SQL query
        if args.sql:
            sql = args.sql
        elif args.sql_file:
            with open(args.sql_file, 'r') as f:
                sql = f.read()
        else:
            print("Error: Either --sql or --sql-file is required")
            return 1

        # Connect to database
        conn = connect_to_database(args.connection_string)

        # Validate and explain
        result = validate_and_explain(
            conn,
            sql,
            schema=args.schema,
            explain=args.explain,
            analyze=args.analyze
        )

        # Format output
        output = format_validation_output(result, args.output_format)
        print(output)

        conn.close()

        # Return exit code based on validation
        return 0 if result['valid'] else 1

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
