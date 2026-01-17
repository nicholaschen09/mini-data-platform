"""Tests for the data agent."""

import pytest
from unittest.mock import Mock, patch
from agent.db import Warehouse, Column, Table
from agent.agent import Agent, _get_error_hint


class TestErrorHints:
    """Test error hint generation."""
    
    def test_column_not_found_hint(self):
        error = "Column 'foo' not found in table"
        hint = _get_error_hint(error)
        assert "column" in hint.lower()
    
    def test_table_not_found_hint(self):
        error = "Table 'bar' does not exist"
        hint = _get_error_hint(error)
        assert "table" in hint.lower() or "marts" in hint.lower()
    
    def test_syntax_error_hint(self):
        error = "Syntax error at position 42"
        hint = _get_error_hint(error)
        assert "syntax" in hint.lower()
    
    def test_type_mismatch_hint(self):
        error = "Type mismatch: cannot compare VARCHAR and INTEGER"
        hint = _get_error_hint(error)
        assert "type" in hint.lower() or "cast" in hint.lower()
    
    def test_ambiguous_column_hint(self):
        error = "Ambiguous column reference 'id'"
        hint = _get_error_hint(error)
        assert "ambiguous" in hint.lower() or "alias" in hint.lower()
    
    def test_generic_error_hint(self):
        error = "Something went wrong"
        hint = _get_error_hint(error)
        assert "schema" in hint.lower()


class TestWarehouse:
    """Test database operations."""
    
    def test_warehouse_connects(self):
        """Test that warehouse can connect to database."""
        from agent.db import get_default_warehouse
        warehouse = get_default_warehouse()
        assert warehouse.conn is not None
        warehouse.close()
    
    def test_get_schemas(self):
        """Test that we can retrieve schemas."""
        from agent.db import get_default_warehouse
        warehouse = get_default_warehouse()
        schemas = warehouse.get_schemas()
        assert "marts" in schemas
        warehouse.close()
    
    def test_get_tables(self):
        """Test that we can retrieve tables from marts schema."""
        from agent.db import get_default_warehouse
        warehouse = get_default_warehouse()
        tables = warehouse.get_tables(schema="marts")
        table_names = [t.name for t in tables]
        assert "fct_orders" in table_names
        assert "dim_customers" in table_names
        assert "dim_products" in table_names
        warehouse.close()
    
    def test_execute_simple_query(self):
        """Test executing a simple SQL query."""
        from agent.db import get_default_warehouse
        warehouse = get_default_warehouse()
        results = warehouse.execute("SELECT COUNT(*) FROM marts.fct_orders")
        assert len(results) == 1
        assert results[0][0] > 0  # Should have some orders
        warehouse.close()
    
    def test_schema_summary_contains_tables(self):
        """Test that schema summary includes expected content."""
        from agent.db import get_default_warehouse
        warehouse = get_default_warehouse()
        summary = warehouse.get_schema_summary(["marts"])
        assert "fct_orders" in summary
        assert "dim_customers" in summary
        assert "dim_products" in summary
        warehouse.close()


class TestAgentSQLCleaning:
    """Test SQL cleaning functionality."""
    
    def test_clean_sql_with_markdown(self):
        """Test removing markdown code blocks."""
        from agent.agent import Agent
        
        # Mock the LLM to avoid API calls
        with patch('agent.agent.get_llm_provider'):
            agent = Agent.__new__(Agent)
            agent._schema_cache = "test schema"
            
            sql = "```sql\nSELECT * FROM test\n```"
            cleaned = agent._clean_sql(sql)
            assert cleaned == "SELECT * FROM test"
    
    def test_clean_sql_without_markdown(self):
        """Test that clean SQL passes through."""
        from agent.agent import Agent
        
        with patch('agent.agent.get_llm_provider'):
            agent = Agent.__new__(Agent)
            agent._schema_cache = "test schema"
            
            sql = "SELECT * FROM test"
            cleaned = agent._clean_sql(sql)
            assert cleaned == "SELECT * FROM test"
    
    def test_clean_sql_strips_whitespace(self):
        """Test that whitespace is stripped."""
        from agent.agent import Agent
        
        with patch('agent.agent.get_llm_provider'):
            agent = Agent.__new__(Agent)
            agent._schema_cache = "test schema"
            
            sql = "  SELECT * FROM test  \n"
            cleaned = agent._clean_sql(sql)
            assert cleaned == "SELECT * FROM test"


class TestAgentIntegration:
    """Integration tests that require LLM API key."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("os").environ.get("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_agent_can_answer_simple_question(self):
        """Test that agent can answer a simple revenue question."""
        import os
        from agent.agent import Agent
        
        agent = Agent()
        result = agent.query("How many orders are there in total?")
        
        assert result["error"] is None
        assert result["results"] is not None
        assert len(result["results"]) > 0
    
    @pytest.mark.skipif(
        not pytest.importorskip("os").environ.get("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_agent_generates_valid_sql(self):
        """Test that agent generates syntactically valid SQL."""
        import os
        from agent.agent import Agent
        
        agent = Agent()
        sql = agent.generate_sql("Count the number of customers")
        
        # Should contain SELECT and FROM
        assert "SELECT" in sql.upper()
        assert "FROM" in sql.upper()
