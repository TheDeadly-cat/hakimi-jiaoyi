"""Canonical Python product definitions. JSON/Node use the generated projection."""
from __future__ import annotations

CAPABILITY_ROWS = (('product_capability_catalog', 'Supported'),
 ('market_data_research', 'Supported'),
 ('historical_backtest', 'Supported'),
 ('research_reporting', 'Supported'),
 ('dataset_snapshot_import', 'Supported'),
 ('research_replay', 'Supported'),
 ('research_report_read', 'Supported'),
 ('strategy_catalog', 'Supported'),
 ('local_research_terminal', 'Experimental'),
 ('parameter_optimization', 'Archived'),
 ('paper_execution', 'Archived'),
 ('live_execution', 'Archived'),
 ('order_entry', 'Disabled'))

CLI_BINDINGS = (('snapshot-import', 'dataset_snapshot_import'),
 ('research', 'historical_backtest'),
 ('replay', 'research_replay'),
 ('report-show', 'research_report_read'),
 ('backtest', 'historical_backtest'),
 ('capabilities', 'product_capability_catalog'),
 ('list-strategies', 'strategy_catalog'),
 ('optimize', 'parameter_optimization'),
 ('paper', 'paper_execution'))

def build_product_capability_definition() -> dict:
    """Return a detached definition; this is not an execution permission API."""
    return {
        "$schema": "./product-capabilities.schema.json",
        "definition_schema_version": "product-capability-definition-v1",
        "catalog": {
            "schema_version": "product-capability-catalog-v2",
            "product_mode": "research_only",
            "authority": {
                "schema_version": "capability-v1", "product_mode": "research_only",
                "research_only": True, "paper_allowed": False, "live_allowed": False,
            },
            "capabilities": [{"name": name, "status": status} for name, status in CAPABILITY_ROWS],
            "cli_bindings": [{"command": command, "capability": capability} for command, capability in CLI_BINDINGS],
        },
    }
