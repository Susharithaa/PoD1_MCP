"""Feature checklist tests for the requested report."""

from __future__ import annotations

from pathlib import Path

import pytest

from config import settings
from utils.masking import mask_sensitive


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_generic_api_tool_hub_includes_expense_specific_integration():
    router_text = _read("backend/routers/domain.py").lower() + _read("backend/routers/mcp.py").lower()
    assert "expense-reports" in router_text
    assert "expense.get_application_info" in router_text


def test_transportation_cost_and_reimbursement_domain_model_ui_and_connector_present():
    domain_schema = _read("backend/schemas/domain.py")
    expenses_ui = _read("frontend/src/pages/Expenses.jsx")
    domain_router = _read("backend/routers/domain.py")
    assert "TransportationCostIn" in domain_schema
    assert "ExpenseReportOut" in domain_schema
    assert "Transportation reimbursement workspace" in expenses_ui
    assert "@router.post(\"/expense-reports\"" in domain_router


def test_concrete_target_rest_api_connector_present():
    domain_router = _read("backend/routers/domain.py")
    assert "@router.get(\"/application-info\"" in domain_router
    assert "@router.post(\"/expense-reports\"" in domain_router
    assert "@router.post(\"/file-download\"" in domain_router


def test_fixed_mcp_tool_set_present():
    mcp_router = _read("backend/routers/mcp.py")
    assert "expense.get_application_info" in mcp_router
    assert "expense.list_reports" in mcp_router
    assert "expense.download_file" in mcp_router


def test_normalized_expense_application_shape_present():
    domain_schema = _read("backend/schemas/domain.py")
    assert "TransportationCostOut" in domain_schema
    assert "ExpenseReportOut" in domain_schema


def test_local_http_dev_setup_exists_and_no_tls_deployment_config_present():
    main_py = _read("backend/main.py")
    assert 'app.mount("/testing"' in main_py
    assert "https" not in main_py.lower()
    assert "ssl_certfile" not in main_py.lower()
    assert "ssl_keyfile" not in main_py.lower()


def test_read_only_mode_enforcement_missing():
    assert settings.read_only_mode is False or settings.read_only_mode is None


def test_dry_run_mode_found_for_tool_execution():
    orchestrator = _read("backend/orchestrator/tool_orchestrator.py")
    assert "dry_run" in orchestrator.lower()


def test_sla_budget_and_five_second_timeout_present():
    orchestrator = _read("backend/orchestrator/tool_orchestrator.py")
    assert "5000" in orchestrator or "5.0" in orchestrator
    assert "TOOL_TIMEOUT_S  = 5.0" in orchestrator
    assert "max_tool_execution_ms" in orchestrator


def test_emergency_stop_and_safe_mode_control_present():
    safety = _read("backend/utils/safety.py")
    assert "emergency_stop" in safety
    assert "dry_run_tools" in safety


def test_request_trace_id_middleware_and_propagation_present():
    observability = _read("backend/utils/observability.py")
    assert "request_id" in observability.lower()
    assert "x-request-id" in observability.lower()


def test_document_and_result_masking_layer_present():
    masking = _read("backend/utils/masking.py")
    assert "mask_sensitive" in masking
    assert "[REDACTED]" in masking or "SECRET_PATTERNS" in masking


def test_explicit_dev_stg_prod_config_separation_present():
    config_py = _read("backend/config.py")
    assert ".env.dev" in config_py
    assert ".env.stg" in config_py
    assert ".env.prod" in config_py


def test_incident_response_aggregation_workflow_and_ui_present():
    admin_router = _read("backend/routers/admin_ext.py")
    admin_ui = _read("frontend/src/pages/Admin.jsx")
    assert "incident" in admin_router.lower()
    assert "incident" in admin_ui.lower()


def test_masking_layer_is_actually_present_to_inform_report():
    masked = mask_sensitive({"token": "abc", "nested": {"authorization": "Bearer x"}})
    assert masked["token"] == "[REDACTED]"
    assert masked["nested"]["authorization"] == "[REDACTED]"


@pytest.mark.parametrize(
    "path, expected",
    [
        ("frontend/src/pages/Expenses.jsx", "Target REST File Download"),
        ("backend/routers/domain.py", "expense-reports"),
        ("backend/routers/mcp.py", "expense.get_application_info"),
    ],
)
def test_reported_paths_have_target_content(path, expected):
    text = _read(path)
    assert expected in text
