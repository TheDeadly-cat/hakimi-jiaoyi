from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.cli import (  # noqa: E402
    LEGACY_OPTIMIZE_ENABLED,
    LEGACY_PAPER_ENABLED,
    build_product_capability_catalog,
    command_backtest,
    command_optimize,
    command_paper,
    main,
    supported_cli_commands,
)
from hakimi_research.product_capabilities import product_capability_status_for_cli_command  # noqa: E402


if __name__ == "__main__":
    main()
