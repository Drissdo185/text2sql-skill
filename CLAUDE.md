# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code skill for PostgreSQL database interaction via natural language. The skill converts natural language requests into SQL queries with safety and validation features.

**Core workflow:** Schema exploration → Relationship analysis → SQL generation → Validation → Safe execution

## Script Architecture

The skill consists of five Python scripts. The main script is `db_init.py` which combines the others:

### 0. `scripts/db_init.py` - One-Command Database Initialization (RECOMMENDED)
**Purpose:** All-in-one script that combines schema scanning and relationship analysis

**Key implementation details:**
- Imports and calls functions from `schema_scanner.py` and `relationship_analyzer.py`
- Runs complete database discovery in single command
- Saves combined context to `/tmp/text2sql_context_<hash>.json`
- Context includes: schema metadata + relationships + foreign keys + many-to-many + graph
- Provides formatted summary of database structure

**Context file structure:**
```python
{
    'connection_info': {
        'masked_connection': 'postgresql://user:***@host/db',
        'schema': 'public',
        'initialized_at': '2024-01-01 12:00:00'
    },
    'schema': { ... },  # Full schema data from schema_scanner
    'relationships': {
        'foreign_keys': [...],
        'many_to_many': [...],
        'graph': {...}  # Adjacency list for path finding
    },
    'summary': {
        'total_tables': 15,
        'total_foreign_keys': 23,
        'tables': ['users', 'orders', ...]
    }
}
```

**When to use:**
- User runs `/db-init` command
- First-time database setup
- After schema changes to refresh context
- Load existing context with `--load` flag

**Functions:**
- `initialize_database()` - Main initialization pipeline
- `load_database_context()` - Load previously saved context
- `format_context_summary()` - Format context as readable markdown
- `get_db_context_path()` - Generate consistent cache path

### 1. `scripts/schema_scanner.py` - Database Schema Discovery
**Purpose:** Extract complete database metadata for query generation context

**Key implementation details:**
- Uses file-based caching (`/tmp/text2sql_schema_<hash>.json`) with 1-hour TTL
- Cache key is MD5 hash of masked connection string + schema name
- Queries `information_schema` and `pg_catalog` for complete metadata
- Returns hierarchical structure: tables → columns → indexes → constraints

**Data structure:**
```python
{
    'schema': 'public',
    'scanned_at': '2024-01-01 12:00:00',
    'table_count': 10,
    'tables': [
        {
            'name': 'users',
            'type': 'BASE TABLE',
            'size_bytes': 16384,
            'row_count_estimate': 1500,
            'columns': [...],
            'indexes': [...],
            'constraints': [...]
        }
    ]
}
```

**When to invalidate cache:** Schema changes (new tables, column modifications, index creation)

### 2. `scripts/relationship_analyzer.py` - Foreign Key Graph Analysis
**Purpose:** Auto-detect table relationships and generate intelligent JOINs

**Key implementation details:**
- Builds adjacency list graph from foreign key relationships
- Uses BFS (breadth-first search) to find shortest path between tables
- Detects many-to-many relationships via junction table heuristics:
  - Table has exactly 2 foreign keys
  - Column count ≤ 4 (the 2 FKs plus optional id/timestamp)

**Graph structure:**
```python
{
    'nodes': ['users', 'orders', 'products'],
    'adjacency': {
        'orders': [
            {'to': 'users', 'from_column': 'user_id', 'to_column': 'id'},
            {'to': 'products', 'from_column': 'product_id', 'to_column': 'id'}
        ]
    },
    'foreign_keys': [...],
    'many_to_many': [...]
}
```

**Path finding:** `find_path_between_tables()` returns list of join steps with column mappings

### 3. `scripts/sql_validator.py` - Query Validation and Optimization
**Purpose:** Validate SQL before execution with security and performance checks

**Validation pipeline:**
1. **Syntax validation** via sqlparse
2. **Schema validation** - verify tables/columns exist
3. **Security checks** - detect SQL injection patterns (semicolons, comments, DROP/DELETE after `;`)
4. **Optimization suggestions** - flag `SELECT *`, missing LIMIT, leading wildcards
5. **EXPLAIN integration** - parse JSON output for performance analysis

**EXPLAIN analysis:**
- Detects sequential scans on tables >1000 rows
- Flags nested loops with >100 iterations
- Returns estimated cost, rows, execution time (if ANALYZE)

### 4. `scripts/query_executor.py` - Safe Query Execution
**Purpose:** Execute queries with protection mechanisms

**Safety mechanisms:**
- **Read-only mode by default** - `conn.read_only = True` unless `--allow-writes`
- **Parameterized queries** - uses psycopg's parameter substitution (never string concatenation)
- **Result set limits** - default 1000 rows with truncation detection
- **Modification detection** - `is_modification_query()` checks for INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE

**Output formats:**
- `markdown` - GitHub-flavored markdown tables (default)
- `json` - Structured data with metadata
- `csv` - Standard CSV with headers
- `table` - ASCII grid tables via tabulate

## Common Development Tasks

### Recommended Workflow (Using /db-init)

```bash
# 1. Initialize database (RECOMMENDED FIRST STEP)
python scripts/db_init.py \
    --connection-string "postgresql://user:pass@localhost/db"

# This single command:
# - Scans complete schema
# - Analyzes all relationships
# - Detects many-to-many patterns
# - Saves context for future use

# 2. Generate SQL based on stored context
# (Claude uses the cached context from step 1)

# 3. Validate generated SQL
python scripts/sql_validator.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --sql "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id" \
    --explain

# 4. Execute safely
python scripts/query_executor.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --sql "SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id LIMIT 100" \
    --format markdown
```

### Alternative: Manual Step-by-Step Workflow

```bash
# 1. Scan schema (uses cache if available)
python scripts/schema_scanner.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --schema public \
    --output-format markdown

# 2. Analyze relationships
python scripts/relationship_analyzer.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --table1 orders \
    --table2 customers \
    --suggest-join

# 3. Validate generated SQL
python scripts/sql_validator.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --sql "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id" \
    --explain

# 4. Execute safely
python scripts/query_executor.py \
    --connection-string "postgresql://user:pass@localhost/db" \
    --sql "SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id LIMIT 100" \
    --format markdown
```

### Testing Individual Scripts

Each script supports `--help` for full CLI documentation:

```bash
python scripts/schema_scanner.py --help
python scripts/relationship_analyzer.py --help
python scripts/sql_validator.py --help
python scripts/query_executor.py --help
```

### Dependencies Installation

```bash
# Quick install
./setup/install.sh

# Manual install
pip install -r setup/requirements.txt
```

**Required packages:**
- `psycopg[binary]>=3.1.0` - PostgreSQL driver (not psycopg2!)
- `sqlparse>=0.4.4` - SQL parsing for validation
- `tabulate>=0.9.0` - Table formatting

## Architecture Patterns

### Connection String Masking
All scripts use `mask_connection_string()` to hide passwords in logs:
```python
# Input: postgresql://user:secret@localhost/db
# Output: postgresql://user:***@localhost/db
```

**Critical:** Never log raw connection strings. Always mask before logging/printing.

### Error Handling Strategy
- Scripts return exit codes: 0=success, 1=error, 130=interrupted
- Use try/except with `conn.rollback()` on query failures
- Validation failures return structured errors, not exceptions

### Parameterized Query Pattern
**ALWAYS use parameter substitution:**
```python
# CORRECT
cur.execute("SELECT * FROM users WHERE email = %(email)s", {'email': user_input})

# NEVER DO THIS
cur.execute(f"SELECT * FROM users WHERE email = '{user_input}'")
```

### Output Format Selection
Use appropriate format for context:
- **markdown** - User-facing output in Claude responses
- **json** - Programmatic processing or when structure matters
- **csv** - Data export for external tools
- **table** - Terminal/console display

## Security Considerations

### SQL Injection Prevention
1. **Parameterized queries only** - Use `%(name)s` placeholders with dict params
2. **Pattern detection** - Validator checks for dangerous patterns (`;DROP`, `--`, `/**/`)
3. **No string concatenation** - Never build SQL with f-strings or +

### Read-Only Enforcement
- Query executor defaults to `read_only=True` connection mode
- Modification queries require explicit `--allow-writes` flag
- `is_modification_query()` checks statement type before execution

### Connection String Security
- Mask passwords in all output via `mask_connection_string()`
- Use environment variables: `export DB_URL="postgresql://..."`
- Never commit connection strings to git

## Caching Strategy

**Schema cache location:** `/tmp/text2sql_schema_<hash>.json`

**Cache invalidation:**
```bash
# Force refresh
python scripts/schema_scanner.py --connection-string $DB_URL --no-cache

# Custom TTL (30 minutes)
python scripts/schema_scanner.py --connection-string $DB_URL --cache-ttl 1800
```

**When cache is stale:**
- Schema modifications (ALTER TABLE, CREATE/DROP TABLE)
- Index changes
- Constraint updates

**Cache key:** MD5 hash of `masked_connection_string:schema_name`

## Logging and Verbosity

All scripts support `--verbose` / `-v` flag:
- Default: Only warnings/errors (quiet operation)
- Verbose: DEBUG level with full stack traces

**Standard logging levels:**
- Default mode: `logging.WARNING`
- Verbose mode: `logging.DEBUG`
- Connection success: `logging.INFO`

## PostgreSQL-Specific Features

### Using EXPLAIN
- `--explain` - Shows query plan without execution
- `--analyze` - Executes query and returns actual metrics (use carefully!)
- Returns JSON format with cost, rows, execution time

### Schema Support
All scripts default to `public` schema but support `--schema` parameter:
```bash
python scripts/schema_scanner.py \
    --connection-string $DB_URL \
    --schema inventory \
    --list-schemas
```

### Data Type Handling
Schema scanner captures:
- Base types: `varchar(255)`, `integer`, `timestamp with time zone`
- Numeric precision: `numeric(10,2)` → precision=10, scale=2
- Character limits: `varchar(100)` → max_length=100

## Skill Integration (SKILL.md)

The `SKILL.md` file defines Claude Code skill triggers:
- Trigger phrases: "query the database", "show me tables", "generate SQL", etc.
- Workflows defined in SKILL.md should be followed for natural language processing
- Always run validation before execution
- Present SQL to user for approval before execution

## File Structure

```
text2sql-skill/
├── scripts/                    # Core Python scripts (main functionality)
│   ├── schema_scanner.py      # Database metadata extraction
│   ├── relationship_analyzer.py  # Foreign key graph + JOIN generation
│   ├── sql_validator.py       # Syntax/schema/security validation
│   └── query_executor.py      # Safe query execution engine
├── setup/
│   ├── requirements.txt       # Python dependencies
│   └── install.sh            # Installation automation
├── examples/                  # Query pattern documentation
│   ├── basic_queries.md      # SELECT, WHERE, GROUP BY patterns
│   └── complex_joins.md      # JOIN patterns and relationship queries
├── templates/
│   └── query_template.sql    # SQL query templates
├── SKILL.md                  # Claude Code skill definition
└── README.md                 # User documentation

```

## Common Pitfalls

1. **Don't use psycopg2** - This project requires psycopg v3 (`psycopg[binary]`)
2. **Cache staleness** - After schema changes, use `--no-cache` to refresh
3. **Result set limits** - Default 1000 rows; increase with `--limit` if needed
4. **Read-only violations** - Modification queries fail without `--allow-writes`
5. **Connection string exposure** - Always use `mask_connection_string()` before logging
6. **Multiple statements** - Scripts process one SQL statement at a time
7. **EXPLAIN ANALYZE** - Actually executes the query; use with caution on modification queries

## Extending the Skill

### Adding New Scripts
Follow the established pattern:
1. Use argparse for CLI with `--help` examples
2. Implement `mask_connection_string()` for safety
3. Return structured data (dict/list)
4. Support `--verbose` flag
5. Return proper exit codes
6. Add to SKILL.md workflows if user-facing

### Adding Output Formats
Update formatters in each script:
- Add new format to `choices=['markdown', 'json', 'csv', 'your_format']`
- Implement `format_results_your_format()` function
- Return string output

### Adding Validation Rules
Extend `sql_validator.py`:
- Add pattern to `check_sql_injection_risk()` for security
- Add check to `suggest_improvements()` for optimization
- Update EXPLAIN parser for new performance warnings
