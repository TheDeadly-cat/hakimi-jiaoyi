"""Upstream type contract for completed rows in correlation matrix replay."""

from copy import deepcopy
import unittest

from exchange_terminal.services import strategy_correlation_return_replay as replay
from tests import test_strategy_correlation_return_replay as replay_fixtures


def _reseal(document, hash_field):
    document[hash_field] = replay._canonical_hash(
        {
            key: value
            for key, value in document.items()
            if key != hash_field
        }
    )


class StrategyCorrelationReturnReplayCompleteAliasContractTests(
    unittest.TestCase
):
    def test_all_resealed_complete_bool_int_aliases_are_blocked(self):
        fixture = replay_fixtures.StrategyCorrelationReturnReplayTests()
        fixture.setUp()
        completed = fixture._input()
        document = replay.build_correlation_matrix_replay(
            completed,
            fixture.preregistration,
        )
        self.assertEqual(
            replay.verify_correlation_matrix_replay(document)["status"],
            "PASS",
        )

        attacked = 0
        for dataset_index, dataset in enumerate(
            document["completed_price_input"]["datasets"]
        ):
            for row_index, row in enumerate(dataset["price_rows"]):
                self.assertIs(row["complete"], True)
                candidate = deepcopy(document)
                candidate["completed_price_input"]["datasets"][dataset_index][
                    "price_rows"
                ][row_index]["complete"] = 1
                _reseal(candidate["completed_price_input"], "input_hash")
                _reseal(candidate, "replay_hash")
                verification = replay.verify_correlation_matrix_replay(
                    candidate
                )
                self.assertEqual(
                    verification,
                    {
                        "status": "BLOCK",
                        "blockers": ["correlation_replay_input_invalid"],
                    },
                )
                attacked += 1

        self.assertEqual(attacked, 305)


if __name__ == "__main__":
    unittest.main()
