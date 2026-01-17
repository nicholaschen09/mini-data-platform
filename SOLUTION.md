# solution



https://github.com/user-attachments/assets/410e01a8-3dcb-4ee0-b195-399c1e2fd3e0



for this takehome i was tasked to build a CLI agent that can answer ad-hoc questions about a data warehouse using natural language.

## my approach

when i first got the project i explored the codebase - airflow dags for ingestion, dbt models for transformations, and a duckdb warehouse with the final data. ran the setup script to populate everything and queried the warehouse to see what tables existed.

the key requirement that stood out was keeping the implementation generic enough to plug into other data platforms. this meant i couldnt hardcode anything about this specific e-commerce dataset.

### how it works

1. user asks a question in natural language
2. agent fetches the database schema from `information_schema` at runtime
3. schema gets injected into the llm prompt so it knows what tables/columns exist
4. llm generates a sql query based on the discovered schema
5. agent executes the sql against the database
6. if the query fails, agent sends the error back to the llm to fix it (up to 2 retries)
7. results get sent back to the llm to summarize in plain english
8. user gets a natural language answer with the sql shown for transparency

### key design decisions

**dynamic schema discovery** - the db layer (`agent/db.py`) queries `information_schema.tables` and `information_schema.columns` to build a text summary of all available data. no table names are hardcoded anywhere in the codebase. you can point this at a completely different database and the agent will adapt.

**generic prompts** - the system prompt avoids mentioning specific tables. instead it gives general guidance like "infer meaning from column names" and "fact tables typically have metrics to aggregate, dim tables are for grouping". the llm figures out what `fct_orders` and `dim_customers` mean from context.

**swappable llm providers** - created an abstract `LLMProvider` interface with implementations for groq (default), openai, and anthropic. switching providers is just changing an env var. groq is default because it has a free tier.

**error self-correction** - llms sometimes generate bad sql. instead of failing immediately, the agent categorizes the error (missing column, bad table name, syntax error, type mismatch) and asks the llm to fix it with a specific hint. this makes complex queries much more reliable.

**interactive repl** - instead of a one-shot command, the default mode is an interactive session where you can keep asking questions. took inspiration from claude code's interface - theres a banner, sample questions to get started, and a simple loading bar while waiting for responses. felt more natural for exploratory data analysis than running separate commands.

### architecture

```
agent/
├── cli.py      # interactive repl with rich formatting
├── agent.py    # text-to-sql pipeline with retry logic  
├── db.py       # schema introspection via information_schema
└── llm.py      # provider abstraction (groq/openai/anthropic)

tests/
└── test_agent.py   # 16 pytest tests
```

## if i had more time

there are several features i would add to make this more production-ready:

**conversation memory** - right now each question is independent. with memory you could ask "how much revenue in 2024?" then follow up with "break that down by month" or "compare to 2023" without repeating context. would probably use a simple message history that gets included in the prompt.

**streaming responses** - for longer answers the user stares at a loading bar. streaming the llm output token-by-token would feel more responsive.

**export to csv/json** - let users save query results to files. useful for when they want to do further analysis in excel or another tool.

**better error messages** - when the llm cant figure out how to answer a question, give more helpful suggestions like "try asking about X instead" based on what data is actually available.

**query history** - save past questions and answers so users can recall or re-run previous queries.

## testing

16 tests covering:
- error hint generation (6 tests)
- database operations (5 tests)
- sql cleaning (3 tests)
- end-to-end with llm (2 tests)

```bash
uv run pytest tests/ -v
```

## steps to run

1. clone the repo and cd into it:
```bash
git clone <repo-url>
cd mini-data-platform
```

2. run the setup script to populate the warehouse:
```bash
./setup.sh
```

3. create your `.env` file with an api key:
```bash
cp .env.example .env
# edit .env and add: GROQ_API_KEY=gsk_your_key_here
# get a free key at https://console.groq.com/keys
```

4. run the agent:
```bash
uv run agent
```

5. ask questions:
```
> how much revenue did we make in 2024?
> what are the top 5 products by sales?
> which customers have the highest lifetime value?
```

6. to run a single question without the repl:
```bash
uv run agent ask "how much revenue in 2024?"
```

7. to just see the generated sql without executing:
```bash
uv run agent sql "show monthly revenue trends"
```
