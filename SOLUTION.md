# Solution

for this takehome i was tasked to build a CLI agent that can answer ad-hoc questions about a data warehouse using natural language.

## quick start

```bash
# set up your api key (get one free at https://console.groq.com/keys)
cp .env.example .env
# edit .env and add your GROQ_API_KEY

# run the agent
uv run agent
```

the agent will start an interactive session where you can ask questions like:
- "how much revenue did we make in 2024?"
- "what are the top 5 products by sales?"
- "which two products are most frequently bought together?"
- "are there any anomalies with how we sell products?"

## my approach

when i first received this project i took a look at the codebase structure - theres airflow dags for ingestion, dbt models for transformation, and a duckdb warehouse with the final data. i ran the setup script to get everything initialized and then poked around the warehouse to understand what data i was working with.

after reading the instructions i noticed the key requirement was to keep the implementation generic enough to work with other data platforms. this meant i couldnt hardcode knowledge about this specific e-commerce dataset - the agent needed to discover the schema dynamically.

### dynamic schema discovery

i started by building out the database layer (`agent/db.py`). this handles connecting to duckdb and introspecting the schema using `information_schema`. the key method is `get_schema_summary()` which generates a text description of all tables and columns that gets passed to the llm:

```python
def get_schema_summary(self, schemas):
    # queries information_schema.tables and columns
    # returns human-readable schema for llm context
```

this means if you swap out the duckdb warehouse for a different database, the agent will automatically discover the new schema and adapt its queries.

### swappable llm providers

i wanted to make it easy to swap between providers since the instructions said no particular requirements around model providers. ended up with a simple interface:

```python
class LLMProvider(ABC):
    def complete(self, system: str, user: str) -> str:
        pass
```

with implementations for groq, openai, and anthropic. you just set `LLM_PROVIDER=groq` in your `.env` and it uses that one. groq is the default since it has a free tier.

### error handling with retry

the llm sometimes generates bad sql, especially for complex queries. instead of just failing i added retry logic that sends the error back to the llm and asks it to fix the query:

```python
def _fix_sql(self, question: str, sql: str, error: str) -> str:
    hint = _get_error_hint(error)  # categorizes the error type
    prompt = FIX_SQL_PROMPT.format(question=question, sql=sql, error=error, hint=hint)
    fixed_sql = self.llm.complete(self._get_system_prompt(), prompt)
    return self._clean_sql(fixed_sql)
```

i also added error categorization so the llm gets helpful hints like "check column names" or "use fully qualified table names" depending on what went wrong. this makes the self-correction much more effective.

### the cli

for the cli (`agent/cli.py`) i used click for the command structure and rich for the formatting. wanted it to look nice with a banner and loading animation. the default command starts an interactive repl where you can keep asking questions.

## testing

i added pytest tests that cover:
- error hint generation (6 tests)
- database operations like connecting and querying (5 tests)  
- sql cleaning to remove markdown code blocks (3 tests)
- end-to-end integration with the llm (2 tests)

run tests with:
```bash
uv run pytest tests/ -v
```

## tools i used

i used cursor with claude opus 4.5 for most of the coding. it was especially helpful for the rich cli formatting and figuring out the error categorization logic. when i ran into issues with the loading animation not rendering correctly it helped me debug the escape codes.

also used uv for package management - first time using it and its way faster than pip. `uv run agent` just works without messing with virtual environments.

## if i had more time

the main tradeoff i made was keeping everything simple and generic rather than adding specialized tools for complex queries. the instructions mentioned questions like "which products are bought together" (market basket analysis) and "are there anomalies" (anomaly detection) - i considered adding specialized sql templates for these but decided against it since that would make the agent less generic. the current approach relies on the llm being smart enough to figure out the right sql based on the schema.

if i had more time id add:

- **conversation memory** - so you can ask follow-up questions like "break that down by month" without restating context
- **query caching** - to avoid regenerating sql for common questions
- **streaming responses** - for better ux on longer answers
- **export to csv/json** - let users save query results to files
- **better visualization** - render charts in the terminal for numeric results

## project structure

```
agent/
├── cli.py      # interactive cli with rich formatting
├── agent.py    # core agent logic (question → sql → answer)
├── db.py       # database connection + schema introspection
└── llm.py      # llm provider abstraction (groq/openai/anthropic)

tests/
└── test_agent.py   # pytest tests
```

overall i think the design hits the right balance between functionality and simplicity. the architecture is clean, its easy to swap llm providers or databases, and the error handling makes it resilient to bad sql generation.
