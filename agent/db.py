"""Database connection and schema introspection."""

import duckdb
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Column:
    name: str
    dtype: str


@dataclass
class Table:
    schema: str
    name: str
    columns: list[Column]
    row_count: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"


class Warehouse:
    """DuckDB warehouse connection with schema introspection."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=True)
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str) -> list[tuple]:
        """Execute SQL and return results as list of tuples."""
        return self.conn.execute(sql).fetchall()

    def execute_df(self, sql: str):
        """Execute SQL and return results as list of dicts."""
        result = self.conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_schemas(self) -> list[str]:
        """Get list of user schemas (excludes system schemas)."""
        rows = self.execute("""
            SELECT DISTINCT table_schema 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema
        """)
        return [r[0] for r in rows]

    def get_tables(self, schema: str | None = None) -> list[Table]:
        """Get tables with their columns. Optionally filter by schema."""
        schema_filter = f"AND t.table_schema = '{schema}'" if schema else ""
        
        # Get tables
        tables_sql = f"""
            SELECT t.table_schema, t.table_name
            FROM information_schema.tables t
            WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog')
            {schema_filter}
            ORDER BY t.table_schema, t.table_name
        """
        table_rows = self.execute(tables_sql)
        
        tables = []
        for schema_name, table_name in table_rows:
            # Get columns for this table
            cols_sql = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """
            col_rows = self.execute(cols_sql)
            columns = [Column(name=c[0], dtype=c[1]) for c in col_rows]
            
            tables.append(Table(
                schema=schema_name,
                name=table_name,
                columns=columns
            ))
        
        return tables

    def get_table_sample(self, table: str, limit: int = 3) -> list[dict]:
        """Get sample rows from a table."""
        return self.execute_df(f"SELECT * FROM {table} LIMIT {limit}")

    def get_schema_summary(self, schemas: list[str] | None = None) -> str:
        """Generate a text summary of the schema for LLM context."""
        if schemas is None:
            schemas = self.get_schemas()  # Auto-detect all available schemas
        
        lines = ["DATABASE SCHEMA:", ""]
        
        for schema in schemas:
            tables = self.get_tables(schema=schema)
            if not tables:
                continue
                
            lines.append(f"Schema: {schema}")
            lines.append("-" * 40)
            
            for table in tables:
                # Get row count
                count = self.execute(f"SELECT COUNT(*) FROM {table.full_name}")[0][0]
                lines.append(f"\n{table.full_name} ({count:,} rows)")
                
                for col in table.columns:
                    lines.append(f"  - {col.name}: {col.dtype}")
            
            lines.append("")
        
        return "\n".join(lines)


def get_default_warehouse() -> Warehouse:
    """Get warehouse connection using default path."""
    # Find the warehouse relative to this file
    agent_dir = Path(__file__).parent
    project_root = agent_dir.parent
    db_path = project_root / "warehouse" / "data.duckdb"
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    return Warehouse(db_path)
