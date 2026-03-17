#!/usr/bin/env python3
"""
MCP Server for CCS PostgreSQL Database.

This server provides tools to interact with the CCS PostgreSQL database,
allowing Claude to query schema information, execute queries, and manage data.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from contextlib import asynccontextmanager
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP, Context
import os
import json

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ccs")

# Enums
class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


# Database connection management using lifespan
@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage database connection pool across requests."""
    # Initialize connection pool on startup
    print(f"Connecting to CCS database at {DATABASE_URL}", file=open('/dev/stderr', 'w'))
    try:
        # Store connection info in lifespan state
        connection_params = psycopg2.extensions.parse_dsn(DATABASE_URL)
        yield {
            "connection_params": connection_params
        }
    finally:
        # Cleanup on shutdown
        pass


# Initialize MCP server
mcp = FastMCP("ccs_mcp", lifespan=app_lifespan)


# Helper functions
def _get_connection(connection_params: Dict[str, Any]):
    """Get a database connection."""
    return psycopg2.connect(**connection_params)


def _format_results(results: List[Dict[str, Any]], total: int, params_offset: int, params_limit: int) -> Dict[str, Any]:
    """Format query results with pagination info."""
    count = len(results)
    return {
        "total": total,
        "count": count,
        "offset": params_offset,
        "limit": params_limit,
        "has_more": total > params_offset + count,
        "next_offset": params_offset + count if total > params_offset + count else None,
        "rows": results
    }


def _format_output(data: Any, response_format: ResponseFormat) -> str:
    """Format output based on requested format."""
    if response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, default=str)
    else:
        # Markdown format for human readability
        if isinstance(data, list):
            if not data:
                return "No results found."

            if isinstance(data[0], dict):
                # Table format for list of dicts
                headers = list(data[0].keys())
                lines = ["| " + " | ".join(headers) + " |"]
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for row in data[:20]:  # Show first 20 rows
                    values = [str(row[h]) for h in headers]
                    lines.append("| " + " | ".join(values) + " |")
                if len(data) > 20:
                    lines.append(f"\n*...and {len(data) - 20} more rows*")
                return "\n".join(lines)

        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                lines.append(f"**{key}**: {value}")
            return "\n".join(lines)

        return str(data)


def _handle_db_error(e: Exception) -> str:
    """Format database error messages clearly."""
    error_str = str(e)
    return f"Error: Database operation failed - {error_str}\n\nPlease check your SQL syntax and permissions."


# Input models
class ListTablesInput(BaseModel):
    """Input model for listing tables."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    schema_name: Optional[str] = Field(
        default="public",
        description="Schema name to list tables from (default: public)",
        min_length=1,
        max_length=100
    )
    limit: Optional[int] = Field(
        default=50,
        description="Maximum number of tables to return",
        ge=1,
        le=200
    )
    offset: Optional[int] = Field(
        default=0,
        description="Number of tables to skip for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown for human-readable, json for machine-readable"
    )


class DescribeTableInput(BaseModel):
    """Input model for describing a table structure."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    table_name: str = Field(
        ...,
        description="Name of the table to describe",
        min_length=1,
        max_length=100
    )
    schema_name: Optional[str] = Field(
        default="public",
        description="Schema name containing the table (default: public)",
        min_length=1,
        max_length=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown for human-readable, json for machine-readable"
    )


class QueryInput(BaseModel):
    """Input model for executing SELECT queries."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    sql: str = Field(
        ...,
        description="SELECT SQL query to execute. Must be a SELECT statement for read-only access.",
        min_length=1
    )
    limit: Optional[int] = Field(
        default=50,
        description="Maximum number of rows to return",
        ge=1,
        le=500
    )
    offset: Optional[int] = Field(
        default=0,
        description="Number of rows to skip for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown for human-readable, json for machine-readable"
    )


class ExecuteInput(BaseModel):
    """Input model for executing write operations (INSERT, UPDATE, DELETE, CREATE, etc)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    sql: str = Field(
        ...,
        description="SQL statement to execute (INSERT, UPDATE, DELETE, CREATE TABLE, etc)",
        min_length=1
    )


class GetSchemaInfoInput(BaseModel):
    """Input model for getting complete schema information."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    schema_name: Optional[str] = Field(
        default="public",
        description="Schema name to get info for (default: public)",
        min_length=1,
        max_length=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown for human-readable, json for machine-readable"
    )


# Tool definitions

@mcp.tool(
    name="ccs_list_tables",
    annotations={
        "title": "List Database Tables",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ccs_list_tables(params: ListTablesInput, ctx: Context) -> str:
    """List all tables in the specified database schema.

    This tool retrieves information about all tables available in the database schema,
    including table names and their sizes. It supports pagination for large schemas.

    Args:
        params: Validated input parameters containing:
            - schema_name (str): Schema name to list tables from (default: "public")
            - limit (int): Maximum number of tables to return (default: 50)
            - offset (int): Number of tables to skip for pagination (default: 0)
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: Formatted list of tables with pagination information

    Examples:
        - Use when: "Show me all tables in the database" → schema_name="public"
        - Use when: "List tables in public schema" → schema_name="public"
    """
    try:
        connection_params = ctx.request_context.lifespan_state["connection_params"]
        conn = _get_connection(connection_params)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get table list
                cur.execute("""
                    SELECT
                        table_name,
                        pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name
                    OFFSET %s LIMIT %s;
                """, (params.schema_name, params.offset, params.limit))
                results = list(cur.fetchall())

                # Get total count
                cur.execute("""
                    SELECT COUNT(*) as total
                    FROM information_schema.tables
                    WHERE table_schema = %s;
                """, (params.schema_name,))
                total = cur.fetchone()["total"]

            conn.commit()
        finally:
            conn.close()

        formatted = _format_results(results, total, params.offset, params.limit)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(formatted, indent=2)
        else:
            lines = [f"# Tables in schema: {params.schema_name}", ""]
            lines.append(f"Found {total} tables (showing {len(results)})")
            lines.append("")
            for table in results:
                lines.append(f"- **{table['table_name']}** - {table['size']}")
            lines.append("")
            if formatted["has_more"]:
                lines.append(f"*More tables available, use offset={formatted['next_offset']} to see next page*")
            return "\n".join(lines)

    except Exception as e:
        return _handle_db_error(e)


@mcp.tool(
    name="ccs_describe_table",
    annotations={
        "title": "Describe Table Structure",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ccs_describe_table(params: DescribeTableInput, ctx: Context) -> str:
    """Get detailed structure information about a specific table including columns, types, and constraints.

    This tool retrieves the complete schema information for a table including:
    - Column names and data types
    - Whether columns allow NULL values
    - Primary key constraints
    - Foreign key constraints
    - Default values

    Args:
        params: Validated input parameters containing:
            - table_name (str): Name of the table to describe
            - schema_name (str): Schema name containing the table (default: "public")
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: Formatted table structure information

    Examples:
        - Use when: "Show me the structure of the sales_invoice table" → table_name="sales_invoice"
        - Use when: "What columns are in the users table?" → table_name="users"
    """
    try:
        connection_params = ctx.request_context.lifespan_state["connection_params"]
        conn = _get_connection(connection_params)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get column information
                cur.execute("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """, (params.schema_name, params.table_name))
                columns = list(cur.fetchall())

                if not columns:
                    return f"Table '{params.schema_name}.{params.table_name}' not found."

                # Get primary key info
                cur.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                      AND tc.table_schema = %s
                      AND tc.table_name = %s;
                """, (params.schema_name, params.table_name))
                pk_columns = [row["column_name"] for row in cur.fetchall()]

                # Get foreign key info
                cur.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_schema AS foreign_table_schema,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                      ON ccu.constraint_name = tc.constraint_name
                     AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema = %s
                      AND tc.table_name = %s;
                """, (params.schema_name, params.table_name))
                fk_info = list(cur.fetchall())

            conn.commit()
        finally:
            conn.close()

        result = {
            "table_name": params.table_name,
            "schema_name": params.schema_name,
            "columns": columns,
            "primary_keys": pk_columns,
            "foreign_keys": fk_info
        }

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2)
        else:
            lines = [f"# Table: {params.schema_name}.{params.table_name}", ""]
            lines.append("## Columns")
            lines.append("")
            lines.append("| Column | Type | Nullable | Default |")
            lines.append("|--------|------|---------|---------|")
            for col in columns:
                dtype = col["data_type"]
                if col["character_maximum_length"]:
                    dtype = f"{dtype}({col['character_maximum_length']})"
                nullable = "YES" if col["is_nullable"] == "YES" else "NO"
                default = col["column_default"] or ""
                lines.append(f"| {col['column_name']} | {dtype} | {nullable} | {default} |")
            lines.append("")

            if pk_columns:
                lines.append("## Primary Key")
                lines.append(", ".join(pk_columns))
                lines.append("")

            if fk_info:
                lines.append("## Foreign Keys")
                for fk in fk_info:
                    lines.append(f"- **{fk['column_name']}** → {fk['foreign_table_schema']}.{fk['foreign_table_name']}.{fk['foreign_column_name']}")
                lines.append("")

            return "\n".join(lines)

    except Exception as e:
        return _handle_db_error(e)


@mcp.tool(
    name="ccs_query",
    annotations={
        "title": "Execute Read-Only Query",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ccs_query(params: QueryInput, ctx: Context) -> str:
    """Execute a read-only SELECT query and return the results.

    This tool is for SELECT queries only. It does not allow modifying the database.
    Use ccs_execute for INSERT, UPDATE, DELETE, CREATE, etc.

    Args:
        params: Validated input parameters containing:
            - sql (str): SELECT SQL query to execute. Must start with SELECT.
            - limit (int): Maximum number of rows to return (default: 50, max: 500)
            - offset (int): Number of rows to skip for pagination (default: 0)
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: Query results formatted according to response_format

    Notes:
        - Only SELECT statements are allowed for security
        - Use LIMIT and OFFSET for pagination
        - Maximum 500 rows per query

    Examples:
        - Use when: "Find all invoices from January" → sql="SELECT * FROM invoices WHERE month = 'January'"
        - Use when: "Count total records per status" → sql="SELECT status, COUNT(*) FROM sales GROUP BY status"
    """
    try:
        # Security check - only allow SELECT
        sql_clean = params.sql.strip().lower()
        if not sql_clean.startswith("select"):
            return "Error: Only SELECT queries are allowed in ccs_query. Use ccs_execute for write operations."

        connection_params = ctx.request_context.lifespan_state["connection_params"]
        conn = _get_connection(connection_params)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Apply limit if not already in query
                query = params.sql
                if "limit" not in sql_clean:
                    query = f"{query.rstrip(';')} LIMIT {params.limit} OFFSET {params.offset}"

                cur.execute(query)
                rows = list(cur.fetchall())

                # Try to get total count for pagination
                total = len(rows)
                if "limit" in sql_clean.lower():
                    # If user already applied limit, we can't get accurate total
                    total = len(rows)

            conn.commit()
        finally:
            conn.close()

        formatted = _format_results(rows, total, params.offset, params.limit)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(formatted, indent=2, default=str)
        else:
            if not rows:
                return "Query executed successfully, no results returned."

            return _format_output(rows, ResponseFormat.MARKDOWN)

    except Exception as e:
        return _handle_db_error(e)


@mcp.tool(
    name="ccs_execute",
    annotations={
        "title": "Execute Write Operation",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def ccs_execute(params: ExecuteInput, ctx: Context) -> str:
    """Execute a SQL statement that modifies the database (INSERT, UPDATE, DELETE, CREATE, etc).

    This tool allows executing any SQL statement that changes the database including:
    - CREATE TABLE / ALTER TABLE
    - INSERT / UPDATE / DELETE
    - CREATE INDEX
    - DROP statements

    Args:
        params: Validated input parameters containing:
            - sql (str): SQL statement to execute

    Returns:
        str: Success message with number of rows affected or error message

    Examples:
        - Use when: "Create a new table called invoices with these columns..." → sql="CREATE TABLE ..."
        - Use when: "Update status to processed for id=123" → sql="UPDATE invoices SET status = 'processed' WHERE id = 123"
        - Use when: "Insert a new record" → sql="INSERT INTO table (...) VALUES (...)"
    """
    try:
        connection_params = ctx.request_context.lifespan_state["connection_params"]
        conn = _get_connection(connection_params)
        try:
            with conn.cursor() as cur:
                cur.execute(params.sql)
                rows_affected = cur.rowcount
            conn.commit()
        finally:
            conn.close()

        return f"✅ Successfully executed.\n\nRows affected: {rows_affected}"

    except Exception as e:
        return _handle_db_error(e)


@mcp.tool(
    name="ccs_get_schema_info",
    annotations={
        "title": "Get Complete Schema Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def ccs_get_schema_info(params: GetSchemaInfoInput, ctx: Context) -> str:
    """Get complete schema information for all tables including table names and row counts.

    This tool provides an overview of the entire schema with row counts for each table.
    It's useful for getting a complete picture of what's in the database.

    Args:
        params: Validated input parameters containing:
            - schema_name (str): Schema name to get info for (default: "public")
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: Complete schema information with table names, estimated row counts
    """
    try:
        connection_params = ctx.request_context.lifespan_state["connection_params"]
        conn = _get_connection(connection_params)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        n.nspname AS schema_name,
                        c.relname AS table_name,
                        c.reltuples::bigint AS estimated_rows,
                        pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s
                      AND c.relkind = 'r'
                    ORDER BY c.relname;
                """, (params.schema_name,))
                tables = list(cur.fetchall())

            conn.commit()
        finally:
            conn.close()

        result = {
            "schema_name": params.schema_name,
            "tables": tables,
            "total_tables": len(tables)
        }

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2)
        else:
            lines = [f"# Schema Information: {params.schema_name}", ""]
            lines.append(f"**Total tables: {len(tables)}**")
            lines.append("")
            lines.append("| Table | Estimated Rows | Size |")
            lines.append("|-------|----------------|------|")
            for table in tables:
                rows = f"{table['estimated_rows']:,}" if table['estimated_rows'] >= 0 else "unknown"
                lines.append(f"| {table['table_name']} | {rows} | {table['total_size']} |")
            lines.append("")
            return "\n".join(lines)

    except Exception as e:
        return _handle_db_error(e)


if __name__ == "__main__":
    mcp.run()
