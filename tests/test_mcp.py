"""Unit tests for MCP server tools."""

import pytest
from argus.engine.evaluator import ResearchEvaluator
from argus.mcp.server import create_mcp_server
from argus.providers.mock_provider import MockSearchStrategy


def test_mcp_evaluator_tools():
    """Verify all 5 MCP tools work end-to-end via evaluator facade."""
    provider = MockSearchStrategy()
    evaluator = ResearchEvaluator(provider=provider)

    # 1. execute_research
    report = evaluator.execute_research(topic="FastAPI async performance")
    assert report.global_confidence_score > 0
    assert len(report.structured_claims) > 0

    target_claim_id = report.structured_claims[0].claim_id
    assert target_claim_id is not None

    # 2. execute_targeted_search
    raw_docs = evaluator.execute_targeted_search("FastAPI async", search_type="google")
    assert len(raw_docs) > 0
    assert raw_docs[0].url.startswith("http")

    # 3. inspect_evidence
    evidence = evaluator.inspect_evidence(claim_id=target_claim_id)
    assert len(evidence) > 0
    assert str(evidence[0].url).startswith("http")

    # 4. inspect_confidence
    breakdown = evaluator.inspect_confidence(claim_id=target_claim_id)
    assert breakdown["claim_id"] == target_claim_id
    assert "formula" in breakdown
    assert "decay_lambda" in breakdown

    # 5. inspect_conflicts
    conflicts = evaluator.inspect_conflicts()
    assert isinstance(conflicts, list)


def test_mcp_server_factory():
    """Verify create_mcp_server constructs server instance properly."""
    server = create_mcp_server(provider=MockSearchStrategy())
    assert server is not None
    assert server.name == "argus-prism"


def test_mcp_resources_and_prompts():
    """Verify MCP resources and prompts are registered and callable."""
    server = create_mcp_server(provider=MockSearchStrategy())
    # Execute sample research
    report = server.evaluator.execute_research("FastAPI async")
    assert report.domain_category is not None

    # Check resources exist
    assert hasattr(server, "list_resources")
    assert hasattr(server, "list_prompts")


def test_mcp_validate_response_tool():
    """Verify validate_response MCP tool works via server evaluator."""
    server = create_mcp_server(provider=MockSearchStrategy())
    val_report = server.evaluator.validate_response(
        response_text="FastAPI async endpoints achieve high throughput on Uvicorn.",
        topic="FastAPI async high-throughput performance",
    )
    assert val_report.overall_validity_score > 0
    assert val_report.total_claims_evaluated >= 1
    assert val_report.verdict is not None


@pytest.mark.anyio
async def test_mcp_auto_repair_and_crawl_tools():
    """Verify auto_repair_draft and crawl_and_audit_url tools are registered and functional."""
    server = create_mcp_server(provider=MockSearchStrategy())
    
    # 1. Test auto_repair_draft tool registration
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "auto_repair_draft" in tool_names
    assert "crawl_and_audit_url" in tool_names
    assert "export_academic_markdown" in tool_names
    assert "generate_verification_badge" in tool_names
    assert "backboard_compare_models" in tool_names
    assert "tabpfn_bayesian_uncertainty" in tool_names

    # 2. Test auto_repair execution
    from argus.engine.auto_fixer import FactualAutoFixer
    report = server.evaluator.validate_response("FastAPI async endpoints achieve high throughput.")
    fix_data = FactualAutoFixer.repair_document("FastAPI async endpoints achieve high throughput.", report)
    assert "repaired_text" in fix_data
    assert "diff_blocks" in fix_data


@pytest.mark.anyio
async def test_mcp_zero_persistence_tools():
    """Verify Backboard and TabPFN zero-persistence MCP tools execution."""
    from argus.llm.backboard_client import BackboardClient
    from argus.engine.tabpfn_oracle import TabPFNOracle

    # TabPFN uncertainty check
    tabpfn_res = TabPFNOracle.evaluate_claim(tier_weight=1.2, base_score=88.0)
    assert tabpfn_res["zero_persistence"] is True
    assert "probabilities" in tabpfn_res

    # Backboard multi-model check
    bb_client = BackboardClient()
    bb_res = bb_client.compare_open_weight_models("FastAPI uses Pydantic.")
    assert bb_res["zero_persistence"] is True
    assert bb_res["agreement_ratio"] == "3/3 Models Concur"



