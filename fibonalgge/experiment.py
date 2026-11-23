"""MAL-E01: corpus, trazas, oráculo y falsación fuera de muestra."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import time
from typing import Callable, Iterable, Iterator, Sequence

from .algebra import algebra_report, analyze_pair_graph, predict_trit, trit_sequence
from .classic import (
    CRZ_TABLE,
    MEM_SIZE,
    Machine,
    TailModel,
    VALID_OPS,
    crazy,
    crz_trit,
    load_cells,
    memory_bytes,
    memory_sha256,
    naive_memory,
)
from .oracle import run_mb_ref

SCHEMA = "fibonalgge-mal-e01/v1"


@dataclass(frozen=True, slots=True)
class CorpusCase:
    name: str
    relative_path: str
    payload_hex: str
    split: str
    max_steps: int

    @property
    def payload(self) -> bytes:
        return bytes.fromhex(self.payload_hex)


def default_corpus() -> list[CorpusCase]:
    """Separación por programa; dos inputs de truth quedan en el mismo split."""
    return [
        CorpusCase("hello", "../BolgeForge/reference/malbolge_org/hello_world.mal", "", "discovery", 5000),
        CorpusCase("sort2", "../Malbolge-PureEpoch/candidates/sort2_real.mal", "3231", "discovery", 5000),
        CorpusCase("cat", "../Malbolge-PureEpoch/candidates/cat_real.mal", "4669620a", "discovery", 20000),
        CorpusCase("clock", "../Malbolge-PureEpoch/candidates/reloj_carry.mal", "", "discovery", 5000),
        CorpusCase("add", "../Malbolge-PureEpoch/candidates/add_real.mal", "3131", "discovery", 5000),
        CorpusCase("rot13", "../BolgeForge/reference/malbolge_org/rot13.mal", b"Hello, Malbolge!\n".hex(), "validation", 20000),
        CorpusCase("truth_0", "../Malbolge-PureEpoch/baseline/truth_machine_classic_90b.mal", "30", "validation", 5000),
        CorpusCase("truth_1", "../Malbolge-PureEpoch/baseline/truth_machine_classic_90b.mal", "31", "validation", 5000),
        CorpusCase("rev", "../Malbolge-PureEpoch/candidates/rev_real.mal", "616263", "validation", 5000),
        CorpusCase("rule90", "../Malbolge-PureEpoch/candidates/boss4_v3_ca.mal", "", "validation", 5000),
        CorpusCase("bottles", "../BolgeForge/reference/malbolge_org/99_bottles.mal", "", "validation", 20000),
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_provenance(path: Path) -> dict:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        ).stdout.strip()

    counting = subprocess.Popen(
        ["git", "-C", str(path), "ls-files", "--others", "--exclude-standard"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert counting.stdout is not None
    untracked_count = sum(1 for _ in counting.stdout)
    counting.stdout.close()
    counting_rc = counting.wait()
    return {
        "path": str(path),
        "head": git("rev-parse", "HEAD"),
        "tracked_status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
        "untracked_count": untracked_count,
        "untracked_count_returncode": counting_rc,
    }


def environment(repo_root: Path) -> dict:
    repos = {
        "fibonalgge": repo_root,
        "bolgeforge": (repo_root / "../BolgeForge").resolve(),
        "pureepoch": (repo_root / "../Malbolge-PureEpoch").resolve(),
        "database": (repo_root / "../MALBOLGE-MB-DATABASE").resolve(),
        "malbolge": (repo_root / "../MALBOLGE").resolve(),
        "genealogy_parent": (repo_root / "..").resolve(),
    }
    oracle = repos["bolgeforge"] / "mb_ref"
    code_paths = [repo_root / "mal_e01.py"]
    for directory in ("fibonalgge", "tests", "tools"):
        code_paths.extend(sorted((repo_root / directory).glob("*.py")))
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "executed_source_sha256": {
            path.relative_to(repo_root).as_posix(): sha256_file(path) for path in code_paths
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "zig": subprocess.run(["zig", "version"], capture_output=True, text=True, check=False).stdout.strip(),
        "repositories": {name: git_provenance(path) for name, path in repos.items()},
        "oracle": {
            "path": str(oracle),
            "binary_sha256": sha256_file(oracle),
            "source_sha256": sha256_file(oracle.parent / "oracle/mb_ref.c"),
        },
    }


def pilot(repo_root: Path, cases: Sequence[CorpusCase]) -> dict:
    """Prueba exhaustiva por trit y paridad de palabra/memoria."""
    started = time.perf_counter()
    graph, _ = analyze_pair_graph()
    trit_checks = 0
    trit_mismatches = []
    for pair in sorted(graph):
        sequence = trit_sequence(pair, 80)
        for index, expected in enumerate(sequence):
            actual = predict_trit(pair, index)
            trit_checks += 1
            if actual != expected:
                trit_mismatches.append({"pair": pair, "index": index, "expected": expected, "actual": actual})

    uniform = MEM_SIZE // 2  # suma 3^0..3^9 = 29524
    memory_cases: list[tuple[str, list[int]]] = []
    for x in range(3):
        for y in range(3):
            memory_cases.append((f"uniform_{x}{y}", [x * uniform, y * uniform]))
    for case in cases:
        source = (repo_root / case.relative_path).read_bytes()
        memory_cases.append((case.name, load_cells(source)))
    memory_mismatches = []
    memory_hashes = []
    for name, cells in memory_cases:
        expected = naive_memory(cells)
        model = TailModel.from_cells(cells)
        actual = model.fill_memory()
        if actual != expected:
            index = next(i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1])
            memory_mismatches.append({"case": name, "index": index, "actual": actual[index], "expected": expected[index]})
        memory_hashes.append({
            "case": name,
            "source_cells": len(cells),
            "naive_sha256": memory_sha256(expected),
            "fast_sha256": memory_sha256(actual),
            "equal": actual == expected,
        })

    # Comparación de trabajo para la última celda de una cola casi completa.
    # La revisión adversarial fijó el período desde G0: bastan seis palabras.
    cells = [33, 34]
    tail_cells = MEM_SIZE - len(cells)
    def conventional_last() -> int:
        mem = list(cells)
        for _ in range(tail_cells):
            mem.append(crazy(mem[-1], mem[-2]))
        return mem[-1]
    def model_last() -> int:
        model = TailModel.from_cells(cells)
        return model.value_at(MEM_SIZE - 1)
    assert conventional_last() == model_last()
    conventional_times = []
    model_times = []
    for _ in range(5):
        tick = time.perf_counter()
        conventional_last()
        conventional_times.append(time.perf_counter() - tick)
        tick = time.perf_counter()
        model_last()
        model_times.append(time.perf_counter() - tick)

    return {
        "algebra": algebra_report(),
        "trit_prediction": {
            "checks": trit_checks,
            "positions_per_pair": 80,
            "mismatches": trit_mismatches,
            "pass": not trit_mismatches,
        },
        "memory_parity": {
            "cases": len(memory_cases),
            "uniform_pair_cases": 9,
            "real_program_cases": len(memory_cases) - 9,
            "cells_per_case": MEM_SIZE,
            "mismatches": memory_mismatches,
            "pass": not memory_mismatches,
            "hashes": memory_hashes,
        },
        "acceleration": {
            "target": "M[59048] para N=2",
            "conventional_crazy_word_calls": tail_cells,
            "model_crazy_word_calls": 6,
            "call_reduction_ratio": tail_cells / 6,
            "conventional_seconds": conventional_times,
            "model_seconds": model_times,
            "conventional_median_seconds": statistics.median(conventional_times),
            "model_median_seconds": statistics.median(model_times),
            "measured_speedup_median_ratio": statistics.median(conventional_times) / statistics.median(model_times),
        },
        "representation": {
            "tail_cells": tail_cells,
            "random_access_cache_cells": 6,
            "generative_seed_cells": 2,
            "tail_to_cache_ratio": tail_cells / 6,
            "note": "La tabla crz y el algoritmo compartidos no se contabilizan como ahorro; no es un claim de compresión universal.",
        },
        "wall_seconds": time.perf_counter() - started,
        "classification": "DEMONSTRATED" if not trit_mismatches and not memory_mismatches else "FALSIFIED",
    }


def _snapshot(machine: Machine) -> bytes:
    return memory_bytes(machine.mem)


def terminal_parity(python_terminal: str, oracle: dict) -> bool:
    """Exige la misma causa concreta de STALL, no sólo el exit code 3."""
    if python_terminal in {"NONPRINTABLE_PC", "INVALID_ENCRYPTION"}:
        return oracle["terminal"] == "STALL" and oracle["stderr_utf8"].startswith(python_terminal + ":")
    return python_terminal == oracle["terminal"]


def run_case(repo_root: Path, case: CorpusCase, run_dir: Path, oracle_path: Path, checkpoint_interval: int = 5000) -> dict:
    started = time.perf_counter()
    program = (repo_root / case.relative_path).resolve()
    source = program.read_bytes()
    cells = load_cells(source)
    model = TailModel.from_cells(cells)
    initial = model.fill_memory()
    # La VM usa el modelo rápido, pero cada programa se compara íntegramente con el literal.
    naive = naive_memory(cells)
    if initial != naive:
        raise AssertionError(f"inicialización divergente en {case.name}")
    initial_memory_sha256 = memory_sha256(initial)
    machine = Machine(mem=initial.copy(), payload=case.payload)
    trace_path = run_dir / "traces" / f"{case.name}.jsonl.gz"
    snapshot_dir = run_dir / "snapshots" / case.name
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    checkpoints: list[dict] = []
    raw_trace_bytes = 0
    trace_digest = hashlib.sha256()
    last_checkpoint = -1

    def checkpoint(label: str, vm: Machine) -> None:
        blob = _snapshot(vm)
        path = snapshot_dir / f"{label}.u16le.bin.gz"
        with gzip.GzipFile(filename=str(path), mode="wb", compresslevel=9, mtime=0) as compressed:
            compressed.write(blob)
        checkpoints.append({
            "label": label,
            "steps": vm.steps,
            "events": vm.events,
            "a": vm.a,
            "c": vm.c,
            "d": vm.d,
            "input_cursor": vm.input_cursor,
            "output_length": len(vm.output),
            "output_sha256": hashlib.sha256(vm.output).hexdigest(),
            "memory_sha256": hashlib.sha256(blob).hexdigest(),
            "snapshot_path": str(path.relative_to(run_dir)),
            "snapshot_gzip_sha256": sha256_file(path),
            "snapshot_uncompressed_bytes": len(blob),
            "snapshot_gzip_bytes": path.stat().st_size,
        })

    def observe(event: dict, vm: Machine) -> None:
        nonlocal raw_trace_bytes, last_checkpoint
        line = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        raw_trace_bytes += len(line)
        trace_digest.update(line)
        trace.write(line)
        if vm.steps > 0 and vm.steps % checkpoint_interval == 0 and vm.steps != last_checkpoint:
            last_checkpoint = vm.steps
            checkpoint(f"step_{vm.steps:08d}", vm)

    with gzip.GzipFile(filename=str(trace_path), mode="wb", compresslevel=9, mtime=0) as trace:
        checkpoint("initial", machine)
        machine.run(case.max_steps, observe)
        checkpoint("final", machine)
    oracle = run_mb_ref(oracle_path, program, case.payload, case.max_steps)
    result = machine.result()
    terminals_match = terminal_parity(result["terminal"], oracle)
    if checkpoints[0]["memory_sha256"] != initial_memory_sha256:
        raise AssertionError(f"recibo inicial divergente en {case.name}")
    steps_match = result["steps"] == case.max_steps if oracle["terminal"] == "MAX_STEPS" else None
    parity = result["output_hex"] == oracle["output_hex"] and terminals_match and steps_match is not False
    return {
        "case": asdict(case),
        "program_absolute_path": str(program),
        "source_bytes": len(source),
        "source_cells": len(cells),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "input_hex": case.payload.hex(),
        "initial_memory_sha256": initial_memory_sha256,
        "naive_initialization_equal": True,
        "python": result,
        "c_oracle": oracle,
        "parity": {
            "output_equal": result["output_hex"] == oracle["output_hex"],
            "terminal_and_stall_reason_equal": terminals_match,
            "max_steps_equal": steps_match,
            "halt_step_count_from_c": "NOT_EXPOSED_BY_MB_REF",
            "pass": parity,
        },
        "trace": {
            "path": str(trace_path.relative_to(run_dir)),
            "format": "JSONL gzip; escrituras [address,old,new,cause]",
            "uncompressed_bytes": raw_trace_bytes,
            "gzip_bytes": trace_path.stat().st_size,
            "gzip_ratio": trace_path.stat().st_size / raw_trace_bytes if raw_trace_bytes else None,
            "uncompressed_sha256": trace_digest.hexdigest(),
            "gzip_sha256": sha256_file(trace_path),
        },
        "checkpoint_interval": checkpoint_interval,
        "checkpoints": checkpoints,
        "wall_seconds": time.perf_counter() - started,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def read_observable(path: Path, observable: str) -> list[int | str]:
    values: list[int | str] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event["opcode"] is None:
                continue
            if observable == "opcode":
                op = event["opcode"]
                values.append(op if op in VALID_OPS else "nop_other")
            elif observable == "a_mod3":
                values.append(event["a_after"] % 3)
            elif observable == "a_high_trit":
                values.append((event["a_after"] // 19683) % 3)
            elif observable == "c_mod94":
                values.append(event["c_after"] % 94)
            elif observable == "d_mod94":
                values.append(event["d_after"] % 94)
            elif observable == "write_class":
                causes = {write[3] for write in event["writes"]}
                values.append("+".join(sorted(causes)) if causes else "none")
            else:
                raise ValueError(observable)
    return values


def _transitions(sequences: Iterable[Sequence], order: int, minimum_index: int | None = None) -> Iterator[tuple[tuple, object]]:
    start = order if minimum_index is None else max(order, minimum_index)
    for sequence in sequences:
        for index in range(start, len(sequence)):
            yield tuple(sequence[index-order:index]), sequence[index]


def _fit_model(name: str, observable: str, train: dict[str, list]) -> dict:
    sequences = list(train.values())
    targets = [target for _, target in _transitions(sequences, 1, minimum_index=2)]
    majority = Counter(targets).most_common(1)[0][0] if targets else None
    model: dict = {"name": name, "observable": observable, "majority": majority}
    if name in {"markov1", "markov2"}:
        order = int(name[-1])
        table: dict[tuple, Counter] = {}
        for context, target in _transitions(sequences, order, minimum_index=2):
            table.setdefault(context, Counter())[target] += 1
        model["order"] = order
        model["table"] = {context: counts.most_common(1)[0][0] for context, counts in table.items()}
        model["training_deterministic"] = all(len(counts) == 1 for counts in table.values())
        model["trained_contexts"] = len(table)
    elif name == "linear_mod3":
        best = None
        for alpha in range(3):
            for beta in range(3):
                for gamma in range(3):
                    correct = total = 0
                    for sequence in sequences:
                        for index in range(2, len(sequence)):
                            prediction = (alpha * sequence[index-1] + beta * sequence[index-2] + gamma) % 3
                            correct += prediction == sequence[index]
                            total += 1
                    candidate = (correct / total if total else 0.0, -alpha, -beta, -gamma, alpha, beta, gamma, correct, total)
                    if best is None or candidate > best:
                        best = candidate
        model.update(alpha=best[4], beta=best[5], gamma=best[6], selection_training_correct=best[7], selection_training_total=best[8], candidates_searched=27)
    return model


def _predict(model: dict, sequence: Sequence, index: int):
    name = model["name"]
    if name == "majority":
        return model["majority"]
    if name == "persistence":
        return sequence[index-1]
    if name in {"markov1", "markov2"}:
        order = model["order"]
        context = tuple(sequence[index-order:index])
        return model["table"].get(context, model["majority"])
    if name == "fibonacci_mod3":
        return (sequence[index-1] + sequence[index-2]) % 3
    if name == "crazy_recurrence_mod3":
        return crz_trit(sequence[index-1], sequence[index-2])
    if name == "linear_mod3":
        return (model["alpha"] * sequence[index-1] + model["beta"] * sequence[index-2] + model["gamma"]) % 3
    if name == "increment_mod94":
        return (sequence[index-1] + 1) % 94
    raise ValueError(name)


def _score(model: dict, sequences: dict[str, list], alignment_order: int | None = None) -> dict:
    natural_order = 2 if model["name"] in {"markov2", "fibonacci_mod3", "crazy_recurrence_mod3", "linear_mod3"} else 1
    order = max(natural_order, alignment_order or 1)
    correct = total = 0
    per_case = {}
    counterexamples = []
    for name, sequence in sequences.items():
        case_correct = case_total = 0
        for index in range(order, len(sequence)):
            if model["name"] in {"fibonacci_mod3", "crazy_recurrence_mod3", "linear_mod3", "increment_mod94"}:
                # Estas familias no necesitan entrenamiento, pero sí dos/uno valores previos.
                pass
            expected = sequence[index]
            actual = _predict(model, sequence, index)
            hit = actual == expected
            correct += hit
            total += 1
            case_correct += hit
            case_total += 1
            if not hit and len(counterexamples) < 10:
                counterexamples.append({"case": name, "index": index, "context": list(sequence[max(0, index-order):index]), "expected": expected, "predicted": actual})
        per_case[name] = {"correct": case_correct, "total": case_total, "accuracy": case_correct / case_total if case_total else None}
    accuracy = correct / total if total else None
    case_accuracies = [entry["accuracy"] for entry in per_case.values() if entry["total"]]
    macro_accuracy = statistics.mean(case_accuracies) if case_accuracies else None
    wilson = None
    if total:
        z = 1.959963984540054
        denominator = 1 + z*z/total
        center = (accuracy + z*z/(2*total)) / denominator
        margin = z * math.sqrt(accuracy*(1-accuracy)/total + z*z/(4*total*total)) / denominator
        wilson = [max(0.0, center-margin), min(1.0, center+margin)]
    return {
        "correct": correct,
        "total": total,
        "accuracy_micro_by_transition": accuracy,
        "accuracy_macro_by_case": macro_accuracy,
        "accuracy": accuracy,
        "wilson_95_descriptive": wilson,
        "exact": total > 0 and correct == total,
        "per_case": per_case,
        "first_counterexamples": counterexamples,
    }


def analyze_register_rules(run_dir: Path, case_results: Sequence[dict]) -> dict:
    """Verifica los dominios exactos de +1 en C/D y clasifica todos los fallos."""
    accum = {
        split: {
            register: {"domain_total": 0, "domain_correct": 0, "failure_reasons": Counter(), "unexplained_failures": []}
            for register in ("c", "d")
        }
        for split in ("discovery", "validation")
    }
    for result in case_results:
        split = result["case"]["split"]
        with gzip.open(run_dir / result["trace"]["path"], "rt", encoding="utf-8") as handle:
            for line in handle:
                event = json.loads(line)
                if event["opcode"] is None:
                    continue
                for register in ("c", "d"):
                    data = accum[split][register]
                    before = event["c_fetch"] if register == "c" else event["d_before"]
                    after = event["c_after"] if register == "c" else event["d_after"]
                    predicted = (before + 1) % 94
                    actual = after % 94
                    jump = "i" if register == "c" else "j"
                    in_domain = event["terminal"] == "RUNNING" and event["opcode"] != jump and before != MEM_SIZE - 1
                    if in_domain:
                        data["domain_total"] += 1
                        data["domain_correct"] += predicted == actual
                    if predicted != actual:
                        if event["terminal"] != "RUNNING":
                            reason = f"terminal:{event['terminal']}"
                        elif event["opcode"] == jump:
                            reason = f"jump:{jump}"
                        elif before == MEM_SIZE - 1:
                            reason = "wrap:59048"
                        else:
                            reason = "UNEXPLAINED"
                            if len(data["unexplained_failures"]) < 10:
                                data["unexplained_failures"].append(event)
                        data["failure_reasons"][reason] += 1
    output = {}
    for split, registers in accum.items():
        output[split] = {}
        for register, data in registers.items():
            total = data["domain_total"]
            output[split][register] = {
                "rule": f"({register}_before+1) mod 94 = {register}_after mod 94",
                "domain": f"paso completado, opcode != {'i' if register == 'c' else 'j'}, {register}_before != 59048",
                "domain_total": total,
                "domain_correct": data["domain_correct"],
                "domain_accuracy": data["domain_correct"] / total if total else None,
                "all_failure_reasons_outside_domain": dict(data["failure_reasons"]),
                "unexplained_failures": data["unexplained_failures"],
                "classification": "DEMONSTRATED_LOCAL_KNOWN_RULE" if total and data["domain_correct"] == total and not data["unexplained_failures"] else "FALSIFIED",
            }
    return output


def shuffled_control(sequences: dict[str, list], observable: str) -> dict[str, list]:
    """Rompe el orden temporal conservando marginales por programa."""
    output = {}
    for name, sequence in sequences.items():
        seed_material = f"MAL-E01/null-v1/{observable}/{name}".encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
        shuffled = list(sequence)
        random.Random(seed).shuffle(shuffled)
        output[name] = shuffled
    return output


def analyze_a_persistence_mechanism(run_dir: Path, case_results: Sequence[dict]) -> dict:
    """Atribuye persistencia de A mod 3 al opcode que produce el valor siguiente."""
    splits = {"discovery": {}, "validation": {}}
    for result in case_results:
        split = result["case"]["split"]
        events = []
        with gzip.open(run_dir / result["trace"]["path"], "rt", encoding="utf-8") as handle:
            for line in handle:
                event = json.loads(line)
                if event["opcode"] is not None:
                    events.append(event)
        for index in range(2, len(events)):
            event = events[index]
            opcode = event["opcode"] if event["opcode"] in VALID_OPS else "nop_other"
            entry = splits[split].setdefault(opcode, {"correct": 0, "total": 0})
            entry["total"] += 1
            entry["correct"] += event["a_after"] % 3 == events[index - 1]["a_after"] % 3
    return {
        split: {
            opcode: {**entry, "accuracy": entry["correct"] / entry["total"]}
            for opcode, entry in sorted(opcodes.items())
        }
        for split, opcodes in splits.items()
    }


def analyze_traces(run_dir: Path, case_results: Sequence[dict]) -> dict:
    observables = ["opcode", "a_mod3", "a_high_trit", "c_mod94", "d_mod94", "write_class"]
    split_sequences: dict[str, dict[str, dict[str, list]]] = {}
    for observable in observables:
        splits = {"discovery": {}, "validation": {}}
        for result in case_results:
            split = result["case"]["split"]
            path = run_dir / result["trace"]["path"]
            splits[split][result["case"]["name"]] = read_observable(path, observable)
        split_sequences[observable] = splits

    report = {}
    for observable, splits in split_sequences.items():
        names = ["majority", "persistence", "markov1", "markov2"]
        if observable in {"a_mod3", "a_high_trit"}:
            names += ["fibonacci_mod3", "crazy_recurrence_mod3", "linear_mod3"]
        if observable in {"c_mod94", "d_mod94"}:
            names += ["increment_mod94"]
        null_sequences = shuffled_control(splits["validation"], observable)
        models = []
        for name in names:
            model = _fit_model(name, observable, splits["discovery"])
            serializable = dict(model)
            if "table" in serializable:
                serializable["table"] = {"|".join(map(str, key)): value for key, value in serializable["table"].items()}
            model_json = json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode("utf-8")
            models.append({
                "model": serializable,
                "model_json_bytes": len(model_json),
                "model_gzip_bytes": len(gzip.compress(model_json, compresslevel=9, mtime=0)),
                "discovery_descriptive": _score(model, splits["discovery"], alignment_order=2),
                "validation": _score(model, splits["validation"], alignment_order=2),
                "validation_null_shuffled": _score(model, null_sequences, alignment_order=2),
            })
        validation_counts = {name: max(0, len(sequence) - 2) for name, sequence in splits["validation"].items()}
        validation_total = sum(validation_counts.values())
        largest_two = sum(sorted(validation_counts.values(), reverse=True)[:2])
        report[observable] = {
            "split_unit": "programa; truth_0/truth_1 comparten programa y split",
            "discovery_programs": sorted(splits["discovery"]),
            "validation_programs": sorted(splits["validation"]),
            "validation_transition_counts": validation_counts,
            "validation_largest_two_transition_share": largest_two / validation_total if validation_total else None,
            "models": models,
            "selection_control": "27 recurrencias lineales se seleccionan sólo en discovery; validation se evalúa una vez. Todos los modelos se ajustan y puntúan desde el tercer valor para compartir denominador. El control nulo baraja cada programa con semilla SHA-256 MAL-E01/null-v1. No se afirma significancia ni universalidad.",
        }
    report["register_local_rules"] = analyze_register_rules(run_dir, case_results)
    report["a_persistence_mechanism"] = analyze_a_persistence_mechanism(run_dir, case_results)
    return report


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_all(repo_root: Path, run_id: str | None = None) -> dict:
    repo_root = repo_root.resolve()
    run_id = run_id or datetime.now(timezone.utc).strftime("MAL-E01_%Y%m%dT%H%M%SZ")
    run_dir = repo_root / "evidence" / run_id
    if run_dir.exists():
        raise FileExistsError(f"no se sobrescribe evidencia: {run_dir}")
    run_dir.mkdir(parents=True)
    cases = default_corpus()
    oracle_path = (repo_root / "../BolgeForge/mb_ref").resolve()
    env = environment(repo_root)
    pilot_result = pilot(repo_root, cases)
    case_results = []
    for case in cases:
        case_results.append(run_case(repo_root, case, run_dir, oracle_path))
        write_json(run_dir / "cases.json", {"cases": case_results})
    analysis = analyze_traces(run_dir, case_results)
    result = {
        "schema": SCHEMA,
        "run_id": run_id,
        "hypotheses": ["H1", "H2", "H3", "H4", "H5"],
        "configuration": {
            "classic_memory_cells": MEM_SIZE,
            "corpus": [asdict(case) for case in cases],
            "split": "programa completo; ningún paso de validation participa en ajuste",
            "checkpoint_interval": 5000,
            "oracle": str(oracle_path),
        },
        "environment": env,
        "pilot": pilot_result,
        "cases": case_results,
        "execution_analysis": analysis,
        "gates": {
            "semantic_integrity": all(case["parity"]["pass"] for case in case_results) and pilot_result["memory_parity"]["pass"],
            "mathematical_reproducibility": pilot_result["trit_prediction"]["pass"] and pilot_result["memory_parity"]["pass"],
            "out_of_sample_note": "Las métricas están en execution_analysis; ningún accuracy aislado se promociona a transformación exacta.",
        },
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    write_json(run_dir / "RESULTS.json", result)
    write_json(repo_root / "RESULTS.json", result)
    return result
