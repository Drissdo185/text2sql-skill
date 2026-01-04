---
name: text2sql
description: >
  Converts natural language to SQL queries for PostgreSQL databases.
  Provides database schema investigation, relationship analysis, SQL validation,
  query explanation, and safe query execution with multiple output formats.
triggers:
  - "/db-init"
  - "initialize database"
  - "connect to database"
  - "query the database"
  - "show me tables"
  - "generate SQL"
  - "check query"
  - "validate SQL"
  - "explain query"
  - "database schema"
  - "table relationships"
  - "JOIN"
  - "foreign keys"
---

# Text2SQL Skill

This skill enables you to interact with PostgreSQL databases using natural language. You can explore database schemas, understand table relationships, generate SQL queries, validate queries for correctness and performance, and execute queries safely.

## When to Use This Skill

Use this skill when users:
- **Run `/db-init` command** - Initialize database connection and scan schema (RECOMMENDED FIRST STEP)
- Want to connect to a PostgreSQL database for the first time
- Want to query a PostgreSQL database using natural language
- Need to explore database structure (tables, columns, relationships)
- Ask to generate SQL from natural language descriptions
- Want to validate or optimize SQL queries
- Need to understand query performance (EXPLAIN)
- Want to understand table relationships and foreign keys
- Ask about how to JOIN tables together

**Important:** For best results, always run `/db-init` first to give Claude complete understanding of your database structure.

## Available Scripts

### 0. Database Initializer (`scripts/db_init.py`)
**Purpose:** One-command database initialization combining schema scanning and relationship analysis

**When to use:**
- User runs `/db-init` command
- User asks to "initialize database" or "connect to database"
- First-time database setup
- After database schema changes

**Key capabilities:**
- Asks user for database connection string
- Scans complete database schema
- Analyzes all table relationships
- Detects many-to-many relationships
- Stores complete context for future queries
- Provides summary of database structure

**Example usage:**
```bash
# Initialize database (will ask for connection details)
python scripts/db_init.py \
    --connection-string "postgresql://user:pass@localhost/dbname"

# Initialize specific schema
python scripts/db_init.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --schema inventory

# Load existing context
python scripts/db_init.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --load
```

**Context storage:**
- Saves to: `/tmp/text2sql_context_<hash>.json`
- Contains: Schema metadata, relationships, foreign keys, many-to-many relationships
- Used by Claude for intelligent query generation

### 1. Schema Scanner (`scripts/schema_scanner.py`)
**Purpose:** Extract complete database schema information

**When to use:**
- User asks "what tables are in the database?"
- Before generating queries (to understand available tables/columns)
- When user wants to explore database structure
- To understand data types and constraints

**Key capabilities:**
- Lists all tables with metadata (row counts, sizes)
- Shows column details (name, type, nullable, defaults)
- Displays indexes and constraints
- Caches results for performance (1-hour TTL)
- Outputs in markdown, JSON, or compact format

**Example usage:**
```bash
python scripts/schema_scanner.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --schema public \
    --output-format markdown
```

### 2. Relationship Analyzer (`scripts/relationship_analyzer.py`)
**Purpose:** Detect and analyze table relationships for intelligent JOIN generation

**When to use:**
- User asks "how are these tables related?"
- Before generating multi-table queries
- When user wants to JOIN tables but doesn't know the relationship
- To detect many-to-many relationships

**Key capabilities:**
- Extracts all foreign key relationships
- Detects many-to-many relationships (junction tables)
- Suggests JOIN patterns between any two tables
- Generates multi-table JOIN queries
- Finds shortest path between tables through relationships

**Example usage:**
```bash
# Suggest JOIN between two tables
python scripts/relationship_analyzer.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --table1 orders \
    --table2 customers \
    --suggest-join

# Generate multi-table JOIN
python scripts/relationship_analyzer.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --generate-join orders customers products
```

### 3. SQL Validator (`scripts/sql_validator.py`)
**Purpose:** Validate SQL syntax, check against schema, and provide performance insights

**When to use:**
- Before executing any generated SQL
- User asks "is this query correct?"
- User wants to optimize a slow query
- To check for SQL injection risks
- To get query performance analysis

**Key capabilities:**
- Validates SQL syntax using sqlparse
- Checks tables and columns exist in schema
- Detects potential SQL injection patterns
- Provides optimization suggestions
- Runs EXPLAIN/EXPLAIN ANALYZE for performance analysis
- Identifies missing indexes and full table scans

**Example usage:**
```bash
# Validate query
python scripts/sql_validator.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --sql "SELECT * FROM users WHERE id = 123" \
    --validate

# Validate with EXPLAIN
python scripts/sql_validator.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --sql "SELECT * FROM users WHERE email = 'test@example.com'" \
    --explain
```

### 4. Query Executor (`scripts/query_executor.py`)
**Purpose:** Execute SQL queries safely with formatted output

**When to use:**
- After validating a query and user approves execution
- User explicitly asks to run a query
- User wants to see query results

**Key capabilities:**
- Executes queries with parameterized parameters (SQL injection safe)
- Read-only mode by default (requires --allow-writes for modifications)
- Limits result sets to prevent memory issues (default: 1000 rows)
- Multiple output formats: table, JSON, CSV, markdown
- Includes execution time in output
- Supports EXPLAIN ANALYZE

**Example usage:**
```bash
# Execute SELECT query
python scripts/query_executor.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --sql "SELECT * FROM users LIMIT 10" \
    --format markdown

# Execute with parameters (safe from SQL injection)
python scripts/query_executor.py \
    --connection-string "postgresql://user:pass@localhost/dbname" \
    --sql "SELECT * FROM users WHERE created_at > %(date)s" \
    --params '{"date": "2024-01-01"}' \
    --format json
```

## Recommended Workflows

### Workflow 0: Database Initialization (RECOMMENDED FIRST STEP)
When user runs `/db-init` or asks to "initialize database" or "connect to database":

**This workflow combines schema scanning and relationship analysis into a single step and stores the context for future queries.**

1. **Ask user for database connection details:**
   - Prompt: "Please provide your PostgreSQL connection string"
   - Format: `postgresql://username:password@host:port/database`
   - Example: `postgresql://postgres:password@localhost:5432/mydb`
   - Security note: Remind user credentials are only used for queries and not stored

2. **Run database initialization:**
   ```bash
   python scripts/db_init.py \
       --connection-string "USER_PROVIDED_CONNECTION_STRING"
   ```

3. **The script will automatically:**
   - Connect to the database
   - Scan the complete schema (all tables, columns, indexes, constraints)
   - Analyze all foreign key relationships
   - Detect many-to-many relationships (junction tables)
   - Build a relationship graph for intelligent JOIN generation
   - Save complete context to `/tmp/text2sql_context_<hash>.json`

4. **Present initialization summary to user:**
   - Total number of tables found
   - Number of relationships detected
   - List of available tables
   - Key relationships overview
   - Many-to-many relationships

5. **Confirmation message:**
   "Database initialized successfully! I now have complete understanding of your database structure and relationships. You can ask me to:"
   - "Show me all customers who ordered products in the last month"
   - "Find the top 10 products by revenue"
   - "List all orders with customer and product details"
   - Or any other natural language query!

**Important notes:**
- The context is cached and reused for subsequent queries in the same session
- If database schema changes, run `/db-init` again to refresh
- Context includes complete schema + relationships for intelligent query generation
- Connection string is masked in all output for security

**When to re-run initialization:**
- First time using the skill with a database
- After schema changes (new tables, columns, relationships)
- When switching to a different database
- When you want to refresh cached information

### Workflow 1: Database Exploration
When user wants to explore a database:

1. **Scan the schema:**
   ```bash
   python scripts/schema_scanner.py --connection-string $DB_URL
   ```

2. **Analyze relationships:**
   ```bash
   python scripts/relationship_analyzer.py --connection-string $DB_URL
   ```

3. **Present schema overview** to user with:
   - List of tables
   - Column details for key tables
   - Relationships between tables
   - Any many-to-many relationships

### Workflow 2: Query Generation
When user describes a query in natural language:

1. **Scan schema** (if not already cached):
   ```bash
   python scripts/schema_scanner.py --connection-string $DB_URL
   ```

2. **If query involves multiple tables, analyze relationships:**
   ```bash
   python scripts/relationship_analyzer.py \
       --connection-string $DB_URL \
       --table1 orders --table2 customers --suggest-join
   ```

3. **Generate SQL query** based on schema knowledge and user requirements

4. **Validate the query:**
   ```bash
   python scripts/sql_validator.py \
       --connection-string $DB_URL \
       --sql "YOUR_GENERATED_SQL" \
       --explain
   ```

5. **Present query to user** with:
   - The SQL code
   - Validation results
   - Performance insights
   - Any warnings or suggestions

6. **If user approves, execute:**
   ```bash
   python scripts/query_executor.py \
       --connection-string $DB_URL \
       --sql "YOUR_VALIDATED_SQL" \
       --format markdown \
       --limit 100
   ```

### Workflow 3: Query Optimization
When user has a slow query:

1. **Validate and explain:**
   ```bash
   python scripts/sql_validator.py \
       --connection-string $DB_URL \
       --sql "USER_QUERY" \
       --explain
   ```

2. **Analyze EXPLAIN output** for:
   - Sequential scans on large tables
   - Missing indexes
   - Inefficient JOINs
   - High cost operations

3. **Suggest improvements:**
   - Add indexes on frequently filtered columns
   - Rewrite query to use indexes
   - Add WHERE clauses to reduce rows scanned
   - Use LIMIT to restrict result sets

4. **Validate improved query:**
   ```bash
   python scripts/sql_validator.py \
       --connection-string $DB_URL \
       --sql "IMPROVED_QUERY" \
       --explain
   ```

5. **Compare before/after metrics** (execution time, cost, rows scanned)

## Security Guidelines

**CRITICAL SECURITY RULES:**

1. **Never expose credentials:**
   - Always mask connection strings in output
   - Never print passwords or sensitive information
   - Use environment variables for credentials when possible

2. **Always use parameterized queries:**
   - NEVER concatenate user input into SQL strings
   - Always use the `--params` flag for dynamic values
   - Example (SAFE):
     ```bash
     --sql "SELECT * FROM users WHERE email = %(email)s" \
     --params '{"email": "user@example.com"}'
     ```
   - Example (UNSAFE - NEVER DO THIS):
     ```bash
     --sql "SELECT * FROM users WHERE email = 'user@example.com'"
     ```

3. **Validate before execution:**
   - Always run `sql_validator.py` before executing queries
   - Check for SQL injection warnings
   - Review modification queries carefully

4. **Default to read-only:**
   - Query executor is read-only by default
   - Requires explicit `--allow-writes` flag for INSERT/UPDATE/DELETE
   - Always warn user before executing modification queries

5. **Limit result sets:**
   - Use `--limit` parameter to restrict rows returned
   - Default limit is 1000 rows
   - Warn user if results are truncated

## Output Format Selection

Choose appropriate format based on use case:

- **Markdown** (default): Best for displaying to users, readable, well-formatted
- **JSON**: Best for programmatic processing, integration with other tools
- **CSV**: Best for data export, spreadsheet import
- **Table**: Best for terminal display, compact view

## Error Handling

When errors occur:

1. **Connection errors:**
   - Check if database is reachable
   - Verify connection string format
   - Check authentication credentials
   - Suggest user verify database is running

2. **Schema errors (table/column not found):**
   - Run schema scanner to see available tables
   - Suggest similar table names (did you mean?)
   - Check if user specified correct schema

3. **Syntax errors:**
   - Show clear error message
   - Highlight problematic part of query
   - Suggest corrections when possible

4. **Permission errors:**
   - Check if user has necessary privileges
   - Suggest running in read-only mode
   - Verify connection user has access to schema

## Caching Behavior

The schema scanner caches results for performance:

- **Cache location:** `/tmp/text2sql_schema_<hash>.json`
- **Cache TTL:** 1 hour (default)
- **Cache invalidation:** Use `--no-cache` to force refresh
- **When to refresh:**
  - Schema has changed (tables added/removed)
  - Column types or constraints modified
  - New indexes created

## Example Interactions

### Example 0: User runs /db-init (FIRST TIME SETUP)
**User:** "/db-init" or "initialize database" or "connect to database"

**You should:**
1. **Ask for connection details:**
   "I'll help you initialize the database connection. Please provide your PostgreSQL connection string in this format:

   `postgresql://username:password@host:port/database`

   For example:
   - Local database: `postgresql://postgres:password@localhost:5432/mydb`
   - Remote database: `postgresql://user:pass@db.example.com:5432/production`

   Your credentials will only be used for queries and are not stored."

2. **After user provides connection string, run initialization:**
   ```bash
   python scripts/db_init.py \
       --connection-string "USER_PROVIDED_CONNECTION_STRING"
   ```

3. **The script will output:**
   - Connection confirmation
   - Schema scanning progress
   - Relationship analysis results
   - Summary of discovered structure

4. **Present the summary to user:**
   "Database initialized successfully! Here's what I found:

   📊 **Database Summary**
   - **Tables:** 15 tables discovered
   - **Relationships:** 23 foreign key relationships
   - **Many-to-Many:** 2 junction tables detected

   📋 **Available Tables:**
   - customers (8 columns, ~1,500 rows)
   - orders (12 columns, ~5,200 rows)
   - products (10 columns, ~850 rows)
   - order_items (6 columns, ~12,000 rows)
   ... [and more]

   🔗 **Key Relationships:**
   - orders → customers (via customer_id)
   - order_items → orders (via order_id)
   - order_items → products (via product_id)

   I now have complete understanding of your database structure! You can ask me things like:
   - 'Show me all customers who ordered in the last month'
   - 'Find the top 10 best-selling products'
   - 'List all orders with customer and product details'
   - Or any other question about your data!"

5. **Store the connection string** for use in subsequent queries (masked in logs)

**Important:** The database context is now cached and will be reused for all subsequent queries. If your schema changes, run `/db-init` again to refresh.

### Example 1: User wants to see all tables
**User:** "Show me all the tables in my database"

**You should:**
1. Run schema scanner:
   ```bash
   python scripts/schema_scanner.py \
       --connection-string $DB_URL \
       --output-format markdown
   ```
2. Present the formatted schema output to user
3. Highlight key tables and their purposes

### Example 2: User wants to generate a query
**User:** "Find all orders from customers in California"

**You should:**
1. Scan schema (if not cached)
2. Identify relevant tables (orders, customers)
3. Analyze relationship between orders and customers:
   ```bash
   python scripts/relationship_analyzer.py \
       --connection-string $DB_URL \
       --table1 orders --table2 customers --suggest-join
   ```
4. Generate SQL:
   ```sql
   SELECT o.*
   FROM orders o
   JOIN customers c ON o.customer_id = c.id
   WHERE c.state = 'CA'
   ```
5. Validate:
   ```bash
   python scripts/sql_validator.py \
       --connection-string $DB_URL \
       --sql "SELECT o.* FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.state = 'CA'" \
       --explain
   ```
6. Present SQL to user with validation results
7. If approved, execute with parameterized query:
   ```bash
   python scripts/query_executor.py \
       --connection-string $DB_URL \
       --sql "SELECT o.* FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.state = %(state)s" \
       --params '{"state": "CA"}' \
       --format markdown
   ```

### Example 3: User wants to optimize a slow query
**User:** "Why is this query slow? SELECT * FROM orders WHERE status = 'pending'"

**You should:**
1. Validate with EXPLAIN:
   ```bash
   python scripts/sql_validator.py \
       --connection-string $DB_URL \
       --sql "SELECT * FROM orders WHERE status = 'pending'" \
       --explain
   ```
2. Analyze EXPLAIN output for issues
3. Provide specific suggestions:
   - "The query is doing a sequential scan on the orders table"
   - "Consider creating an index: CREATE INDEX idx_orders_status ON orders(status)"
   - "If you only need specific columns, avoid SELECT *"
4. Show optimized version:
   ```sql
   SELECT id, customer_id, created_at, total
   FROM orders
   WHERE status = 'pending'
   LIMIT 1000
   ```

## Advanced Features

### Detecting Many-to-Many Relationships
Use relationship analyzer to detect junction tables:
```bash
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --detect-m2m
```

This identifies patterns like:
- users ↔ roles (through user_roles junction table)
- products ↔ categories (through product_categories)
- students ↔ courses (through enrollments)

### Multi-Table JOIN Generation
Generate complex multi-table JOINs automatically:
```bash
python scripts/relationship_analyzer.py \
    --connection-string $DB_URL \
    --generate-join orders customers products order_items
```

The analyzer finds the shortest path through foreign keys and generates appropriate JOIN clauses.

### Query Performance Analysis
Use EXPLAIN ANALYZE for detailed performance insights:
```bash
python scripts/sql_validator.py \
    --connection-string $DB_URL \
    --sql "YOUR_QUERY" \
    --analyze
```

This actually executes the query and provides:
- Actual execution time
- Rows scanned vs rows returned
- Index usage
- Join performance
- Bottlenecks and optimization opportunities

## Limitations

Current limitations to be aware of:
- **PostgreSQL only:** Currently supports PostgreSQL databases
- **Single statement:** Scripts process one SQL statement at a time
- **Result size limits:** Default 1000 rows (configurable with --limit)
- **Cache staleness:** Schema cache may be stale if schema changes frequently
- **No transaction management:** Each query runs in its own transaction
- **Read-only default:** Write operations require explicit flag

## Tips for Best Results

1. **🚀 RUN `/db-init` FIRST** - Initialize database to give Claude complete understanding of schema and relationships
2. **Always scan schema first** before generating queries (or use cached context from /db-init)
3. **Use relationship analyzer** for multi-table queries (automatically done in /db-init)
4. **Validate queries** before execution
5. **Use parameterized queries** for dynamic values
6. **Limit result sets** to avoid overwhelming output
7. **Cache schema** for better performance on repeated queries
8. **Read-only by default** to prevent accidental data modification
9. **Use EXPLAIN** to understand query performance
10. **Present queries to user** for approval before execution
11. **Mask connection strings** in all output
12. **Re-run /db-init** after schema changes to refresh context

## Troubleshooting

### "Connection failed" error
- Verify database is running and accessible
- Check connection string format: `postgresql://user:password@host:port/database`
- Ensure network connectivity to database server
- Verify credentials are correct

### "Table not found" error
- Run schema scanner to see available tables
- Check if table is in a different schema
- Verify table name spelling

### "Permission denied" error
- Check if database user has necessary privileges
- Try read-only operations first
- Contact database administrator for access

### Performance issues
- Use `--explain` to analyze query plan
- Check for missing indexes
- Reduce result set size with LIMIT
- Optimize WHERE clauses

---

**Remember:** Always prioritize security and user safety. Validate queries, use parameterized parameters, default to read-only mode, and never expose credentials in output.
