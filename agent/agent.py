"""LLM agent for text-to-SQL queries."""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from .db import Warehouse, get_default_warehouse
from .llm import LLMProvider, get_llm_provider

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


SYSTEM_PROMPT = """You are a data analyst assistant. You help users query a data warehouse by converting their questions into SQL.

{schema}

INSTRUCTIONS:
1. Analyze the schema to understand what data is available
2. Write a SQL query to answer the user's question
3. Always qualify table names with schema (e.g., schema_name.table_name)
4. Return ONLY the SQL query, no explanation, no markdown code blocks
5. If you can't answer with the available data, say so

TIPS:
- Infer meaning from table and column names
- Tables with "fact" or transaction data typically have metrics to aggregate
- Tables with "dim" or entity data are usually for grouping/filtering
- Use JOINs when combining data from multiple tables
"""

FIX_SQL_PROMPT = """The SQL query you generated failed with this error:

Error: {error}

{hint}

Original question: {question}

Failed SQL:
```sql
{sql}
```

Please fix the SQL query. Return ONLY the corrected SQL, no explanation."""


def _get_error_hint(error: str) -> str:
    """Get a helpful hint based on the error type."""
    error_lower = error.lower()
    
    if "column" in error_lower and "not found" in error_lower:
        return "Hint: Check that all column names exist in the schema. Use the exact column names."
    elif "table" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
        return "Hint: Use fully qualified table names like schema_name.table_name."
    elif "syntax" in error_lower:
        return "Hint: Check SQL syntax. DuckDB uses standard SQL."
    elif "type" in error_lower and ("mismatch" in error_lower or "cannot" in error_lower):
        return "Hint: Check data types. You may need to cast values."
    elif "ambiguous" in error_lower:
        return "Hint: Qualify ambiguous column names with table aliases."
    else:
        return "Hint: Review the schema and ensure the query matches the available tables and columns."


class Agent:
    """Text-to-SQL agent using configurable LLM provider."""

    def __init__(self, warehouse: Warehouse | None = None, llm: LLMProvider | None = None, max_retries: int = 2):
        self.warehouse = warehouse or get_default_warehouse()
        self.llm = llm or get_llm_provider()
        self.max_retries = max_retries
        self._schema_cache: str | None = None

    @property
    def schema_summary(self) -> str:
        if self._schema_cache is None:
            # Use configured schemas or auto-detect
            default_schemas = os.environ.get("AGENT_SCHEMAS", "").split(",") if os.environ.get("AGENT_SCHEMAS") else None
            self._schema_cache = self.warehouse.get_schema_summary(default_schemas)
        return self._schema_cache

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(schema=self.schema_summary)

    def _clean_sql(self, sql: str) -> str:
        """Remove markdown code blocks and clean up SQL."""
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            # Remove first line (```sql) and last line (```)
            if lines[-1].strip() == "```":
                sql = "\n".join(lines[1:-1])
            else:
                sql = "\n".join(lines[1:])
        return sql.strip()

    def generate_sql(self, question: str) -> str:
        """Convert a natural language question to SQL."""
        sql = self.llm.complete(self._get_system_prompt(), question)
        return self._clean_sql(sql)

    def _fix_sql(self, question: str, sql: str, error: str) -> str:
        """Ask the LLM to fix a failed SQL query."""
        hint = _get_error_hint(error)
        prompt = FIX_SQL_PROMPT.format(question=question, sql=sql, error=error, hint=hint)
        fixed_sql = self.llm.complete(self._get_system_prompt(), prompt)
        return self._clean_sql(fixed_sql)

    def query(self, question: str) -> dict:
        """Answer a question: generate SQL, execute, return results with retry on error."""
        sql = self.generate_sql(question)
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                results = self.warehouse.execute_df(sql)
                return {
                    "question": question,
                    "sql": sql,
                    "results": results,
                    "error": None,
                    "retries": attempt
                }
            except Exception as e:
                last_error = str(e)
                
                if attempt < self.max_retries:
                    # Try to fix the SQL
                    sql = self._fix_sql(question, sql, last_error)
                else:
                    # Out of retries
                    return {
                        "question": question,
                        "sql": sql,
                        "results": None,
                        "error": last_error,
                        "retries": attempt
                    }
        
        # Should never reach here, but just in case
        return {
            "question": question,
            "sql": sql,
            "results": None,
            "error": last_error,
            "retries": self.max_retries
        }

    def chat(self, question: str) -> str:
        """Full conversational response to a question."""
        result = self.query(question)
        
        if result["error"]:
            retries = result.get("retries", 0)
            retry_msg = f" (tried {retries + 1} times)" if retries > 0 else ""
            return f"I tried this SQL{retry_msg}:\n```sql\n{result['sql']}\n```\n\nBut got an error: {result['error']}\n\nTry rephrasing your question or ask for something simpler."
        
        # Format results nicely
        if not result["results"]:
            return f"Query executed but returned no results.\n\nSQL:\n```sql\n{result['sql']}\n```"
        
        # Ask LLM to summarize the results
        summary_prompt = f"""The user asked: "{question}"

I ran this SQL:
```sql
{result['sql']}
```

Results (showing up to 20 rows):
{json.dumps(result['results'][:20], indent=2, default=str)}

Please provide a clear, concise answer to the user's question based on these results. Include key numbers and insights. If the data shows interesting patterns, mention them."""

        answer = self.llm.complete("You are a helpful data analyst.", summary_prompt)
        
        # Include the SQL for transparency
        return f"{answer}\n\n---\n*SQL used:*\n```sql\n{result['sql']}\n```"
