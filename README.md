# Text2SQL Claude Code Skill

A production-ready Claude Code skill that converts natural language to SQL queries for PostgreSQL databases. This skill provides comprehensive database schema investigation, intelligent relationship analysis, SQL validation, query optimization, and safe query execution.

## Features

- **Schema Investigation**: Automatically explore database structure, tables, columns, indexes, and constraints
- **Relationship Analysis**: Detect foreign keys, many-to-many relationships, and generate intelligent JOINs
- **SQL Validation**: Validate syntax, check against schema, detect SQL injection risks
- **Query Optimization**: EXPLAIN/EXPLAIN ANALYZE integration with performance suggestions
- **Safe Execution**: Read-only mode by default, parameterized queries, result set limits
- **Multiple Output Formats**: Markdown, JSON, CSV, and ASCII tables
- **Smart Caching**: 1-hour schema cache for improved performance

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database (local or remote)
- pip package manager

### Quick Install

```bash
# Clone or download this repository
cd text2sql-skill

# Run installation script
chmod +x setup/install.sh
./setup/install.sh
```

The installer will:
1. Check your Python version
2. Optionally create a virtual environment
3. Install all required dependencies
4. Verify PostgreSQL client libraries

### Manual Installation

```bash
# Install dependencies
pip install -r setup/requirements.txt

# Verify installation
python scripts/schema_scanner.py --help
```

## Quick Start

### 1. Initialize your database (RECOMMENDED)

**The fastest way to get started is with the all-in-one database initializer:**

```bash
# Initialize database - scans schema + analyzes relationships in one command
python scripts/db_init.py \
    --connection-string "postgresql://user:password@localhost:5432/mydb"
```

This will:
- Connect to your database
- Scan complete schema (tables, columns, indexes, constraints)
- Analyze all relationships and foreign keys
- Detect many-to-many relationships
- Cache everything for future queries

**Output:**
```
DATABASE INITIALIZATION
============================================================

[1/3] Scanning database schema...
✓ Found 15 tables

[2/3] Analyzing table relationships...
✓ Found 23 foreign key relationships
✓ Detected 2 many-to-many relationships

[3/3] Building database context...
✓ Context saved to: /tmp/text2sql_context_abc123.json

INITIALIZATION COMPLETE
============================================================
Database is ready for natural language queries!
```

After initialization, Claude Code can answer questions like:
- "Show me all customers who ordered in the last month"
- "Find the top 10 best-selling products"
- "List all orders with customer and product details"

---

### 2. Alternative: Manual exploration (if you prefer step-by-step)

#### Set up your database connection

```bash
# Option 1: Use environment variable (recommended)
export DB_URL="postgresql://user:password@localhost:5432/mydb"

# Option 2: Pass connection string directly (see examples below)
```

#### Explore your database schema

```bash
# List all tables with details
python scripts/schema_scanner.py --connection-string $DB_URL

# List all schemas available
python scripts/schema_scanner.py --connection-string $DB_URL --list-schemas

# Scan a specific schema
python scripts/schema_scanner.py --connection-string $DB_URL --schema myschema
```

### 3. Understand table relationships

```bash
# Show all foreign key relationships
python scripts/relationship_analyzer.py --connection-string $DB_URL

# Suggest JOIN between two tables
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --table1 orders \
    --table2 customers \
    --suggest-join

# Detect many-to-many relationships
python scripts/relationship_analyzer.py --connection-string $DB_URL --detect-m2m
```

### 4. Validate and optimize SQL queries

```bash
# Validate a query
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE email = 'test@example.com'"

# Get query performance analysis with EXPLAIN
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM orders WHERE status = 'pending'" \
    --explain
```

### 5. Execute queries safely

```bash
# Execute a SELECT query
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 10" \
    --format markdown

# Execute with parameters (safe from SQL injection)
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE created_at > %(date)s" \
    --params '{"date": "2024-01-01"}' \
    --format json
```

## Usage with Claude Code

This skill is designed to work seamlessly with Claude Code.

### Getting Started with Claude Code

**First time?** Run the `/db-init` command in Claude Code:

```
/db-init
```

Claude will:
1. Ask for your database connection string
2. Initialize complete database context (schema + relationships)
3. Store it for future queries
4. Show you a summary of your database structure

**After initialization**, you can ask Claude anything in natural language:

1. Claude uses the cached database context
2. Generates appropriate SQL based on schema and relationships
3. Validates the query for syntax, security, and performance
4. Executes safely and formats results

### Example Interactions

**You:** `/db-init`

**Claude:** "I'll help you initialize the database connection. Please provide your PostgreSQL connection string..."
(After you provide it, Claude scans schema, analyzes relationships, and shows summary)

**You:** "Show me all the tables in my database"

**Claude:** (Uses cached context to present formatted table list with metadata)

**You:** "Find all orders from customers in California placed in the last month"

**Claude:** (Uses relationship graph to generate JOIN, validates, and executes)

**You:** "Why is this query slow? SELECT * FROM orders WHERE status = 'pending'"

**Claude:** (Runs EXPLAIN ANALYZE and provides optimization suggestions)

## Scripts Reference

### schema_scanner.py

Extracts complete database schema information.

**Options:**
```
--connection-string TEXT    PostgreSQL connection string (required)
--schema TEXT               Schema name (default: public)
--output-format CHOICE      Output format: markdown, json, compact (default: markdown)
--cache / --no-cache        Enable/disable caching (default: enabled)
--cache-ttl INTEGER         Cache TTL in seconds (default: 3600)
--list-schemas              List all available schemas
--verbose, -v               Enable verbose logging
```

**Examples:**
```bash
# Basic schema scan
python scripts/schema_scanner.py --connection-string $DB_URL

# JSON output without caching
python scripts/schema_scanner.py \
    --connection-string $DB_URL \
    --output-format json \
    --no-cache

# Scan specific schema with verbose output
python scripts/schema_scanner.py \
    --connection-string $DB_URL \
    --schema inventory \
    --verbose
```

### relationship_analyzer.py

Detects and analyzes table relationships.

**Options:**
```
--connection-string TEXT    PostgreSQL connection string (required)
--schema TEXT               Schema name (default: public)
--table1 TEXT               First table for JOIN suggestion
--table2 TEXT               Second table for JOIN suggestion
--suggest-join              Suggest JOIN pattern between table1 and table2
--generate-join TABLE...    Generate multi-table JOIN query
--detect-m2m                Detect many-to-many relationships
--output-format CHOICE      Output format: markdown, json (default: markdown)
--verbose, -v               Enable verbose logging
```

**Examples:**
```bash
# Show all relationships
python scripts/relationship_analyzer.py --connection-string $DB_URL

# Suggest JOIN between orders and customers
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --table1 orders \
    --table2 customers \
    --suggest-join

# Generate multi-table JOIN
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --generate-join orders customers products

# Find many-to-many relationships
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --detect-m2m \
    --output-format json
```

### sql_validator.py

Validates SQL queries and provides performance insights.

**Options:**
```
--connection-string TEXT    PostgreSQL connection string (required)
--sql TEXT                  SQL query to validate
--sql-file PATH             File containing SQL query
--schema TEXT               Schema name (default: public)
--explain                   Run EXPLAIN to show query plan
--analyze                   Run EXPLAIN ANALYZE (executes query!)
--output-format CHOICE      Output format: markdown, json (default: markdown)
--verbose, -v               Enable verbose logging
```

**Examples:**
```bash
# Validate query syntax and schema
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE id = 123"

# Validate with performance analysis
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM orders WHERE status = 'pending'" \
    --explain

# Validate query from file
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql-file query.sql \
    --analyze
```

### query_executor.py

Executes SQL queries safely with formatted output.

**Options:**
```
--connection-string TEXT    PostgreSQL connection string (required)
--sql TEXT                  SQL query to execute
--sql-file PATH             File containing SQL query
--params JSON               Query parameters as JSON
--format CHOICE             Output format: table, json, csv, markdown (default: markdown)
--limit INTEGER             Max rows to return (default: 1000)
--explain                   Run EXPLAIN to show query plan
--analyze                   Run EXPLAIN ANALYZE
--allow-writes              Allow INSERT/UPDATE/DELETE queries
--verbose, -v               Enable verbose logging
```

**Examples:**
```bash
# Execute simple query
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 10"

# Execute with parameters (safe!)
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE status = %(status)s" \
    --params '{"status": "active"}' \
    --format json

# Execute with EXPLAIN
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM orders WHERE created_at > '2024-01-01'" \
    --explain \
    --limit 100

# Execute modification query (dangerous!)
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "UPDATE users SET status = 'inactive' WHERE last_login < '2023-01-01'" \
    --allow-writes
```

## Security Best Practices

### 1. Connection Strings

**DO:**
- Use environment variables: `export DB_URL="postgresql://..."`
- Use `.env` files (not committed to git)
- Use connection string URIs

**DON'T:**
- Hardcode passwords in scripts
- Commit credentials to version control
- Share connection strings in chat logs

### 2. SQL Injection Prevention

**DO:**
```bash
# Use parameterized queries
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE email = %(email)s" \
    --params '{"email": "user@example.com"}'
```

**DON'T:**
```bash
# Never concatenate user input!
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users WHERE email = 'user@example.com'"
```

### 3. Read-Only by Default

All query execution is read-only by default. To execute modification queries:

```bash
# Requires explicit --allow-writes flag
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "DELETE FROM users WHERE id = 123" \
    --allow-writes
```

### 4. Result Set Limits

Queries are limited to 1000 rows by default to prevent memory issues:

```bash
# Customize limit
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM large_table" \
    --limit 100
```

## Performance Optimization

### Schema Caching

Schema information is cached for 1 hour by default:

```bash
# Use cache (default)
python scripts/schema_scanner.py --connection-string $DB_URL --cache

# Force refresh
python scripts/schema_scanner.py --connection-string $DB_URL --no-cache

# Custom cache TTL (30 minutes)
python scripts/schema_scanner.py --connection-string $DB_URL --cache-ttl 1800
```

Cache files are stored in `/tmp/text2sql_schema_*.json`

### Query Performance Analysis

Use EXPLAIN to understand query performance:

```bash
# Get query plan (doesn't execute query)
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "YOUR_QUERY" \
    --explain

# Get actual execution metrics (executes query!)
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "YOUR_QUERY" \
    --analyze
```

Look for:
- **Sequential scans** on large tables → add indexes
- **High cost** operations → optimize query structure
- **Many rows scanned** → add WHERE clauses
- **Nested loops** with high iterations → optimize JOINs

## Troubleshooting

### Connection Issues

**Error:** "Connection failed"

**Solutions:**
1. Verify database is running: `pg_isready -h localhost -p 5432`
2. Check connection string format: `postgresql://user:password@host:port/database`
3. Verify network access: `telnet host port`
4. Check credentials: `psql -h host -U user -d database`

### Permission Errors

**Error:** "Permission denied"

**Solutions:**
1. Verify user has database access: `GRANT CONNECT ON DATABASE mydb TO myuser;`
2. Check table permissions: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO myuser;`
3. Try read-only operations first
4. Contact database administrator

### Schema Not Found

**Error:** "Table not found" or "Schema not found"

**Solutions:**
1. List available schemas: `--list-schemas`
2. Run schema scanner to see all tables
3. Specify schema explicitly: `--schema myschema`
4. Check spelling and case sensitivity

### Performance Issues

**Symptom:** Slow queries

**Solutions:**
1. Run EXPLAIN to analyze query plan
2. Add indexes on frequently filtered columns
3. Reduce result set with WHERE clauses
4. Use LIMIT to restrict rows
5. Avoid SELECT * (specify needed columns)
6. Check for missing indexes on JOIN columns

## Output Formats

### Markdown (Default)
Best for human readability, great for displaying to users.

```bash
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 5" \
    --format markdown
```

### JSON
Best for programmatic processing, API integration.

```bash
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 5" \
    --format json
```

### CSV
Best for data export, spreadsheet import.

```bash
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 5" \
    --format csv > users.csv
```

### Table (ASCII)
Best for terminal display, compact view.

```bash
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql "SELECT * FROM users LIMIT 5" \
    --format table
```

## Advanced Usage

### Multi-Schema Queries

```bash
# Scan different schemas
python scripts/schema_scanner.py \
    --connection-string $DB_URL \
    --schema inventory

python scripts/schema_scanner.py \
    --connection-string $DB_URL \
    --schema analytics
```

### Complex JOIN Generation

```bash
# Auto-generate JOIN for multiple tables
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --generate-join orders customers products order_items
```

### Query from File

```bash
# Validate query from file
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql-file complex_query.sql \
    --explain

# Execute query from file
python scripts/query_executor.py \
    --connection-string $DB_URL \
    --sql-file query.sql \
    --format json
```

### Batch Operations

```bash
# Export multiple tables
for table in users orders products; do
    python scripts/query_executor.py \
        --connection-string $DB_URL \
        --sql "SELECT * FROM $table" \
        --format csv > "${table}.csv"
done
```

## Examples

See the `examples/` directory for more detailed examples:
- `examples/basic_queries.md` - Simple SELECT, WHERE, ORDER BY, LIMIT
- `examples/complex_joins.md` - Multi-table JOINs, subqueries, CTEs

## Contributing

This is a Claude Code skill. To improve it:

1. Enhance the Python scripts in `scripts/`
2. Update `SKILL.md` with new capabilities
3. Add examples to `examples/`
4. Update this README with new features

## License

MIT License - feel free to use and modify as needed.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the examples in `examples/`
3. Check script help: `python scripts/schema_scanner.py --help`
4. File an issue on GitHub

## Changelog

### Version 1.0.0 (2026-01-04)
- Initial release
- PostgreSQL support
- Schema scanning with caching
- Relationship analysis and JOIN generation
- SQL validation with EXPLAIN integration
- Safe query execution with multiple output formats
- Security features: read-only mode, parameterized queries, result limits
