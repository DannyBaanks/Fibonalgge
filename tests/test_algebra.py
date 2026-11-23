from __future__ import annotations

import random
import unittest

from fibonalgge.algebra import analyze_pair_graph, crz_algebra, predict_trit, trit_sequence, xlat2_analysis
from fibonalgge.classic import MEM_SIZE, TailModel, crazy, naive_memory


class CrazyAlgebraTests(unittest.TestCase):
    def test_canonical_table_and_order(self) -> None:
        expected = ((1, 1, 2), (0, 0, 2), (0, 2, 1))
        report = crz_algebra()
        self.assertEqual(tuple(map(tuple, report["table"])), expected)
        self.assertEqual(crazy(0, 1) % 3, 1)
        self.assertEqual(crazy(1, 0) % 3, 0)
        self.assertFalse(report["commutative"])
        self.assertFalse(report["associative"])
        self.assertEqual(report["associativity_counterexample_count"], 15)
        self.assertEqual(report["left_identities"], [])
        self.assertEqual(report["right_identities"], [])
        self.assertEqual(report["left_absorbing"], [])
        self.assertEqual(report["right_absorbing"], [])
        self.assertEqual(report["idempotent_values"], [])

    def test_xlat2_has_an_exact_phase_representation(self) -> None:
        report = xlat2_analysis()
        self.assertEqual(sorted(report["cycle_lengths"]), [2, 4, 5, 6, 9, 68])
        self.assertEqual(report["joint_period_lcm"], 3060)
        self.assertEqual(report["exhaustive_checks"], 94 * 3061)
        self.assertEqual(report["mismatches"], [])

    def test_pair_graph_is_fully_characterized(self) -> None:
        graph, cycles = analyze_pair_graph()
        self.assertEqual(len(graph), 9)
        self.assertEqual(sorted(len(cycle) for cycle in cycles), [2, 2, 3])
        self.assertEqual(max(info["transient"] for info in graph.values()), 1)
        self.assertEqual({state for state, info in graph.items() if info["transient"]}, {(0, 0), (1, 1)})
        for state, info in graph.items():
            x, y = state
            self.assertEqual(info["next"], (y, crazy(y, x) % 3))

    def test_constant_time_prediction_all_pairs(self) -> None:
        for x in range(3):
            for y in range(3):
                sequence = trit_sequence((x, y), 200)
                self.assertEqual([predict_trit((x, y), i) for i in range(200)], sequence)


class TailModelTests(unittest.TestCase):
    def test_all_nine_uniform_trit_pairs_full_memory(self) -> None:
        uniform = MEM_SIZE // 2
        for x in range(3):
            for y in range(3):
                with self.subTest(pair=(x, y)):
                    cells = [x * uniform, y * uniform]
                    self.assertEqual(TailModel.from_cells(cells).fill_memory(), naive_memory(cells))

    def test_generated_sequence_is_periodic_from_g0(self) -> None:
        uniform = MEM_SIZE // 2
        for x in range(3):
            for y in range(3):
                model = TailModel.from_cells([x * uniform, y * uniform])
                generated = list(model.generated_values(24))
                self.assertEqual(generated[6:], generated[:-6])
                self.assertEqual(tuple(generated[:6]), model.cycle)

    def test_seeded_nonuniform_cases_full_memory(self) -> None:
        rng = random.Random(0xF1B0)
        for length in (2, 3, 10, 100):
            for _ in range(2):
                cells = [rng.randrange(MEM_SIZE) for _ in range(length)]
                with self.subTest(length=length, cells=cells):
                    self.assertEqual(TailModel.from_cells(cells).fill_memory(), naive_memory(cells))

    def test_far_positions_and_source_preservation(self) -> None:
        cells = [59048, 0, 12345, 6789]
        model = TailModel.from_cells(cells)
        self.assertEqual(model.cycle.__len__(), 6)
        for index in range(200):
            self.assertEqual(model.value_at(len(cells) + index), list(model.generated_values(200))[index])
        for index in range(1, 100):
            self.assertEqual(model.value_at(len(cells) + index + 6), model.value_at(len(cells) + index))


if __name__ == "__main__":
    unittest.main()
