from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from fibonalgge.classic import MEM_SIZE, Machine, TailModel, load_cells, rotate
from fibonalgge.experiment import default_corpus, run_case, terminal_parity
from fibonalgge.oracle import run_mb_ref

ROOT = Path(__file__).resolve().parents[1]
PUREEPOCH = (ROOT / "../Malbolge-PureEpoch").resolve()
MB_REF = (ROOT / "../BolgeForge/mb_ref").resolve()


class PrimitiveTests(unittest.TestCase):
    def test_rotation_is_ten_trit_rotation(self) -> None:
        for value in range(MEM_SIZE):
            rotated = value
            for _ in range(10):
                rotated = rotate(rotated)
            self.assertEqual(rotated, value)


class IndependentVMParityTests(unittest.TestCase):
    def reference_module(self):
        path = PUREEPOCH / "baseline/epoch_probe.py"
        spec = importlib.util.spec_from_file_location("fibonalgge_epoch_probe", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_prefixes_against_pureepoch_machine(self) -> None:
        reference = self.reference_module()
        cases = {case.name: case for case in default_corpus()}
        for name, budget in (("hello", 5000), ("truth_1", 2000), ("sort2", 5000), ("clock", 5000)):
            with self.subTest(case=name):
                case = cases[name]
                source = (ROOT / case.relative_path).read_bytes()
                ours = Machine.from_source(source, case.payload)
                theirs = reference.Machine(reference.load(source), case.payload)
                for _ in range(budget):
                    if ours.terminal != "RUNNING" or theirs.terminal != "RUNNING":
                        break
                    ours.tick()
                    theirs.tick()
                    self.assertEqual((ours.a, ours.c, ours.d, ours.input_cursor, ours.steps),
                                     (theirs.a, theirs.c, theirs.d, theirs.input_cursor, theirs.steps))
                    self.assertEqual(bytes(ours.output), theirs.output)
                    if ours.steps % 250 == 0:
                        self.assertEqual(ours.mem, theirs.mem)
                self.assertEqual(ours.mem, theirs.mem)
                self.assertEqual(ours.terminal, theirs.terminal)

    def test_hello_against_c_oracle(self) -> None:
        case = next(case for case in default_corpus() if case.name == "hello")
        program = (ROOT / case.relative_path).resolve()
        oracle = run_mb_ref(MB_REF, program, case.payload, case.max_steps)
        machine = Machine.from_source(program.read_bytes(), case.payload)
        machine.run(case.max_steps)
        self.assertEqual(machine.terminal, "HALT")
        self.assertEqual(bytes(machine.output).hex(), oracle["output_hex"])
        self.assertEqual(bytes(machine.output), b"Hello, world.")

    def test_initial_receipt_is_not_final_alias(self) -> None:
        case = next(case for case in default_corpus() if case.name == "hello")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            result = run_case(ROOT, case, Path(directory), MB_REF)
        self.assertEqual(result["initial_memory_sha256"], result["checkpoints"][0]["memory_sha256"])
        self.assertNotEqual(result["initial_memory_sha256"], result["python"]["memory_sha256"])

    def test_stall_reason_cannot_be_mixed(self) -> None:
        oracle = {"terminal": "STALL", "stderr_utf8": "NONPRINTABLE_PC: cell 0"}
        self.assertTrue(terminal_parity("NONPRINTABLE_PC", oracle))
        self.assertFalse(terminal_parity("INVALID_ENCRYPTION", oracle))


if __name__ == "__main__":
    unittest.main()
