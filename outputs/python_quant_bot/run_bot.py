from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.cli import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    LEGACY_OPTIMIZE_ENABLED,
    LEGACY_PAPER_ENABLED,
    REPORT_DIR,
    SUMMARY_FIELDS,
    build_product_capability_catalog,
    command_backtest,
    command_capabilities,
    command_list_strategies,
    command_optimize,
    command_paper,
    load_stack,
    main,
    product_capability_status_for_cli_command,
    supported_cli_commands,
)


if __name__ == "__main__":
    main()
