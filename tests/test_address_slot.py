from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

from fibonalgge.address_slot import (
    M,
    MASK_ALL_ONES,
    P,
    S,
    build_default_targets,
    build_one_cycle,
    model_exhaustive,
    model_sequence,
    run_image,
    trits,
    validate_one_cycle,
    wrong_store_value,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNNER = (
    ROOT.parent / "MALBOLGE-MB-DATABASE" / "runners" / "malbolge-original" / "malbolge"
)


class AddressSlotAlgebraTests(unittest.TestCase):
    def test_exhaustive_exact_write_and_rearm(self) -> None:
        report = model_exhaustive()
        self.assertTrue(report["exact_write_ok"], report["write_failures"][:3])
        self.assertTrue(report["rearm_ok"], report["rearm_failures"][:3])
        self.assertEqual(report["domain"], 59049)

    def test_repeated_model_cycle(self) -> None:
        report = model_sequence(build_default_targets())
        self.assertTrue(report["all_ok"], report)
        self.assertEqual(report["cycles"], 2)

    def test_targets_are_high_and_payloads_buildable(self) -> None:
        for target in build_default_targets():
            self.assertGreater(target, 126)
            self.assertTrue(all(t in (1, 2) for t in trits(target - 1)))


class AddressSlotImageTests(unittest.TestCase):
    def test_one_cycle_positive_for_two_destinations(self) -> None:
        for target in build_default_targets():
            with self.subTest(target=target):
                built = build_one_cycle(target)
                report = validate_one_cycle(built)
                self.assertTrue(report["ok"], [k for k, v in report["checks"].items() if not v])
                self.assertEqual(report["terminal"], "HALT")
                self.assertEqual(report["output_hex"], f"{built.expected_output:02x}")
                self.assertEqual(report["final"]["slot"], built.slot_value)
                self.assertEqual(report["final"]["payload"], built.slot_value)
                self.assertEqual(report["final"]["mask"], MASK_ALL_ONES)
                self.assertEqual(report["final"]["sentinel"], 42)
                jump = report["jump_events"][0]
                self.assertEqual(jump["c_after"], target)
                self.assertEqual(jump["c_encrypt"], built.slot_value)

    def test_negative_control_lands_elsewhere(self) -> None:
        for target in build_default_targets():
            with self.subTest(target=target):
                built = build_one_cycle(target, store_value=wrong_store_value(target))
                report = validate_one_cycle(built, negative=True)
                self.assertTrue(report["ok"], [k for k, v in report["checks"].items() if not v])
                jump = report["jump_events"][0]
                self.assertNotEqual(jump["c_after"], target)
                self.assertEqual(jump["c_after"], built.slot_value + 1)

    def test_slot_and_payload_neighbours_are_isolated(self) -> None:
        built = build_one_cycle(build_default_targets()[0])
        machine, _ = run_image(built.image)
        self.assertEqual(machine.mem[M], MASK_ALL_ONES)
        self.assertEqual(machine.mem[S], built.slot_value)
        self.assertEqual(machine.mem[P], built.slot_value)
        self.assertEqual(machine.mem[built.sentinel_addr], 42)

    @unittest.skipUnless(ORIGINAL_RUNNER.exists(), "runner C original no disponible")
    def test_original_c_runner_parity(self) -> None:
        for target in build_default_targets():
            built = build_one_cycle(target)
            path = Path("/tmp") / f"fibonalgge-e02-{target}.mb"
            path.write_bytes(built.image)
            completed = subprocess.run(
                [str(ORIGINAL_RUNNER), str(path), "100000"],
                input=b"",
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            # El runner original añade un salto de línea al imprimir la salida.
            output = completed.stdout.rstrip(b"\n")
            self.assertEqual(output, bytes([built.expected_output]))
            self.assertIn(b"status: HALTED", completed.stderr)
