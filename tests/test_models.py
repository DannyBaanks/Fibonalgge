from __future__ import annotations

import unittest

from fibonalgge.experiment import _fit_model, _score


class ModelSplitTests(unittest.TestCase):
    def test_markov_context_does_not_cross_sequences(self) -> None:
        train = {"a": [1, 0, 0], "b": [2, 2]}
        model = _fit_model("markov1", "a_mod3", train)
        self.assertNotIn((1, 2), model["table"])
        scored = _score(model, {"held_out": [0, 0, 1, 0]})
        self.assertEqual(scored["total"], 3)
        self.assertEqual(scored["correct"], 2)

    def test_scores_can_share_denominator(self) -> None:
        sequences = {"held_out": [0, 1, 1, 2, 0]}
        majority = _fit_model("majority", "a_mod3", {"train": [0, 1]})
        fibonacci = _fit_model("fibonacci_mod3", "a_mod3", {"train": [0, 1]})
        first = _score(majority, sequences, alignment_order=2)
        second = _score(fibonacci, sequences, alignment_order=2)
        self.assertEqual(first["total"], second["total"])
        self.assertEqual(first["total"], 3)

    def test_fibonacci_is_not_assumed(self) -> None:
        model = _fit_model("fibonacci_mod3", "a_mod3", {"train": [0, 1, 1, 2, 0, 2]})
        discovery = _score(model, {"train": [0, 1, 1, 2, 0, 2]})
        validation = _score(model, {"validation": [0, 1, 0, 0, 0]})
        self.assertTrue(discovery["exact"])
        self.assertFalse(validation["exact"])


if __name__ == "__main__":
    unittest.main()
