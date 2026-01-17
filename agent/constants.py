"""Constants and configuration for the agent."""

# Retry configuration
MAX_RETRIES = 2

# Query limits
DEFAULT_SAMPLE_LIMIT = 3
MAX_RESULTS_TO_SUMMARIZE = 20
MAX_LLM_TOKENS = 1024

# System schemas to exclude from introspection
SYSTEM_SCHEMAS = ("information_schema", "pg_catalog")
