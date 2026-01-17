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
1. When the user asks a question, write a DuckDB SQL query to answer it
2. Use the marts schema tables for analysis (they're the cleanest, most complete data)
3. Always qualify table names with schema (e.g., marts.fct_orders)
4. Return ONLY the SQL query, no explanation, no markdown code blocks
5. If you can't answer the question with the available data, explain why

TIPS:
- fct_orders has order line items with customer and product info denormalized
- dim_customers has customer details and segments
- dim_products has product catalog with prices and margins
- Dates are in transaction_date column
- Revenue is in the 'total' column, quantity sold is in 'quantity'
"""


class Agent:
    """Text-to-SQL agent using configurable LLM provider."""

    def __init__(self, warehouse: Warehouse | None = None, llm: LLMProvider | None = None):
        self.warehouse = warehouse or get_default_warehouse()
        self.llm = llm or get_llm_provider()
        self._schema_cache: str | None = None

    @property
    def schema_summary(self) -> str:
        if self._schema_cache is None:
            self._schema_cache = self.warehouse.get_schema_summary(["marts"])
        return self._schema_cache

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(schema=self.schema_summary)

    def generate_sql(self, question: str) -> str:
        """Convert a natural language question to SQL."""
        return self.llm.complete(self._get_system_prompt(), question)

    def query(self, question: str) -> dict:
        """Answer a question: generate SQL, execute, return results."""
        # Generate SQL
        sql = self.generate_sql(question)
        
        # Clean up SQL (remove markdown code blocks if present)
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        sql = sql.strip()
        
        # Execute
        try:
            results = self.warehouse.execute_df(sql)
            return {
                "question": question,
                "sql": sql,
                "results": results,
                "error": None
            }
        except Exception as e:
            return {
                "question": question,
                "sql": sql,
                "results": None,
                "error": str(e)
            }

    def chat(self, question: str) -> str:
        """Full conversational response to a question."""
        result = self.query(question)
        
        if result["error"]:
            return f"I tried this SQL:\n```sql\n{result['sql']}\n```\n\nBut got an error: {result['error']}"
        
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
