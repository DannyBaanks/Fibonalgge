"""Caracterización exhaustiva de crz y de la recurrencia de inicialización."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .classic import CRZ_TABLE, MEM_SIZE, XLAT2, TailModel, crazy, crz_trit, naive_memory

Pair = tuple[int, int]


def pair_transition(pair: Pair) -> Pair:
    """(M[i-2], M[i-1]) -> (M[i-1], M[i])."""
    x, y = pair
    return y, crz_trit(y, x)


@dataclass(frozen=True, slots=True)
class PairAnalysis:
    state: Pair
    transient: int
    cycle: tuple[Pair, ...]
    cycle_position: int
    basin: int


def analyze_pair_graph() -> tuple[dict[Pair, dict], list[list[Pair]]]:
    states = [(x, y) for x in range(3) for y in range(3)]
    successors = {state: pair_transition(state) for state in states}
    analyses: dict[Pair, PairAnalysis] = {}
    cycles: list[list[Pair]] = []

    for origin in states:
        if origin in analyses:
            continue
        path: list[Pair] = []
        positions: dict[Pair, int] = {}
        state = origin
        while state not in analyses and state not in positions:
            positions[state] = len(path)
            path.append(state)
            state = successors[state]
        if state in positions:
            cycle = path[positions[state]:]
            basin = len(cycles)
            cycles.append(cycle)
            for offset, member in enumerate(cycle):
                analyses[member] = PairAnalysis(member, 0, tuple(cycle), offset, basin)
            prefix = path[:positions[state]]
            for member in reversed(prefix):
                nxt = successors[member]
                analyses[member] = PairAnalysis(
                    member,
                    analyses[nxt].transient + 1,
                    analyses[nxt].cycle,
                    -1,
                    basin,
                )
        else:
            known = analyses[state]
            for member in reversed(path):
                nxt = successors[member]
                analyses[member] = PairAnalysis(
                    member,
                    analyses[nxt].transient + 1,
                    known.cycle,
                    -1,
                    known.basin,
                )

    # Cuenca = conjunto de estados que termina en el mismo ciclo, no solo prefijo.
    by_basin: dict[int, list[Pair]] = {}
    for state, analysis in analyses.items():
        by_basin.setdefault(analysis.basin, []).append(state)
    table: dict[Pair, dict] = {}
    for state in states:
        analysis = analyses[state]
        table[state] = {
            "next": successors[state],
            "transient": analysis.transient,
            "cycle_length": len(analysis.cycle),
            "cycle": analysis.cycle,
            "basin": sorted(by_basin[analysis.basin]),
        }
    return table, cycles


def trit_sequence(pair: Pair, count: int) -> list[int]:
    if count < 0:
        raise ValueError("count debe ser no negativo")
    if count == 0:
        return []
    x, y = pair
    sequence = [x]
    if count == 1:
        return sequence
    sequence.append(y)
    while len(sequence) < count:
        x, y = y, crz_trit(y, x)
        sequence.append(y)
    return sequence[:count]


def predict_trit(pair: Pair, index: int) -> int:
    """Predicción O(1) tras clasificar el par; no itera hasta index."""
    if index < 0:
        raise IndexError(index)
    table, _ = analyze_pair_graph()
    info = table[pair]
    if index < info["transient"]:
        return trit_sequence(pair, index + 1)[index]
    # El estado del par en el borde del ciclo se alcanza tras t transiciones;
    # la secuencia de trits desplaza esa misma fase.
    sequence = trit_sequence(pair, info["transient"] + 2 * info["cycle_length"] + 1)
    start = info["transient"]
    return sequence[start + (index - start) % info["cycle_length"]]


def crz_algebra() -> dict:
    rows = CRZ_TABLE
    left_identity = [e for e in range(3) if all(crz_trit(e, y) == y for y in range(3))]
    right_identity = [e for e in range(3) if all(crz_trit(x, e) == x for x in range(3))]
    left_absorbing = [z for z in range(3) if all(crz_trit(z, y) == z for y in range(3))]
    right_absorbing = [z for z in range(3) if all(crz_trit(x, z) == z for x in range(3))]
    idempotent = [x for x in range(3) if crz_trit(x, x) == x]
    commutative = all(crz_trit(x, y) == crz_trit(y, x) for x in range(3) for y in range(3))
    associative = all(
        crz_trit(crz_trit(x, y), z) == crz_trit(x, crz_trit(y, z))
        for x in range(3) for y in range(3) for z in range(3)
    )
    comm_counterexamples = [
        [x, y, crz_trit(x, y), crz_trit(y, x)]
        for x in range(3) for y in range(3) if crz_trit(x, y) != crz_trit(y, x)
    ]
    assoc_counterexamples = [
        [x, y, z, crz_trit(crz_trit(x, y), z), crz_trit(x, crz_trit(y, z))]
        for x in range(3) for y in range(3) for z in range(3)
        if crz_trit(crz_trit(x, y), z) != crz_trit(x, crz_trit(y, z))
    ]
    left_permutations = {}
    for x in range(3):
        images = [crz_trit(x, y) for y in range(3)]
        if sorted(images) == [0, 1, 2]:
            left_permutations[x] = images
    right_permutations = {}
    for y in range(3):
        images = [crz_trit(x, y) for x in range(3)]
        if sorted(images) == [0, 1, 2]:
            right_permutations[y] = images
    return {
        "convention": "CRZ_TABLE[x][y] = crz(x,y); filas=x, columnas=y",
        "table": rows,
        "left_identities": left_identity,
        "right_identities": right_identity,
        "left_absorbing": left_absorbing,
        "right_absorbing": right_absorbing,
        "idempotent_values": idempotent,
        "commutative": commutative,
        "commutativity_counterexamples": comm_counterexamples,
        "associative": associative,
        "associativity_counterexample_count": len(assoc_counterexamples),
        "associativity_counterexamples": assoc_counterexamples,
        "bijective_when_left_fixed": left_permutations,
        "bijective_when_right_fixed": right_permutations,
    }


def check_word_tritwise_exhaustive() -> bool:
    """Control de separabilidad sobre dos familias exhaustivas de 59049 pares."""
    for value in range(MEM_SIZE):
        x, y = value, value
        direct = crazy(value, value)
        recomposed = 0
        place = 1
        for _ in range(10):
            recomposed += crz_trit(x % 3, y % 3) * place
            x //= 3
            y //= 3
            place *= 3
        if direct != recomposed:
            return False
    # Segunda familia exhaustiva por palabra; no pretende cubrir el producto 59049².
    for right in range(MEM_SIZE):
        left = (right * 19682 + 12345) % MEM_SIZE
        direct = crazy(left, right)
        x, y = left, right
        recomposed = 0
        place = 1
        for _ in range(10):
            recomposed += crz_trit(x % 3, y % 3) * place
            x //= 3
            y //= 3
            place *= 3
        if direct != recomposed:
            return False
    return True


def xlat2_analysis() -> dict:
    """Descomposición exacta del autocifrado en ciclos y fases."""
    mapping = [ord(char) for char in XLAT2]
    if sorted(mapping) != list(range(33, 127)):
        raise AssertionError("XLAT2 no es una permutación de los 94 imprimibles")
    seen: set[int] = set()
    cycles: list[list[int]] = []
    phase: dict[int, tuple[int, int]] = {}
    for start in range(33, 127):
        if start in seen:
            continue
        cycle = []
        value = start
        while value not in seen:
            seen.add(value)
            cycle.append(value)
            value = mapping[value - 33]
        if value != start:
            raise AssertionError("transitorio inesperado en una permutación")
        cycle_id = len(cycles)
        cycles.append(cycle)
        for position, member in enumerate(cycle):
            phase[member] = cycle_id, position

    def predict(value: int, count: int) -> int:
        cycle_id, position = phase[value]
        cycle = cycles[cycle_id]
        return cycle[(position + count) % len(cycle)]

    checks = 0
    mismatches = []
    horizon = math.lcm(*(len(cycle) for cycle in cycles))
    for start in range(33, 127):
        value = start
        for count in range(horizon + 1):
            actual = predict(start, count)
            checks += 1
            if actual != value:
                mismatches.append([start, count, value, actual])
            value = mapping[value - 33]
    return {
        "cycles": cycles,
        "cycle_lengths": [len(cycle) for cycle in cycles],
        "joint_period_lcm": horizon,
        "representation": "(cycle_id, phase); F rota phase módulo la longitud del ciclo",
        "prediction": "XLAT2^k(v) = cycle[(phase+k) mod cycle_length]",
        "exhaustive_checks": checks,
        "mismatches": mismatches,
        "scope": "sólo autocifrado de una celda no alterada por otra operación; no predice control de flujo",
    }


def algebra_report() -> dict:
    graph, cycles = analyze_pair_graph()
    lengths = [len(cycle) for cycle in cycles]
    return {
        "crz": crz_algebra(),
        "pair_graph": {
            "state_count": len(graph),
            "states": [
                {
                    "state": list(state),
                    "next": list(info["next"]),
                    "transient": info["transient"],
                    "cycle_length": info["cycle_length"],
                    "cycle": [list(pair) for pair in info["cycle"]],
                    "basin": [list(pair) for pair in info["basin"]],
                }
                for state, info in sorted(graph.items())
            ],
            "cycles": [[list(pair) for pair in cycle] for cycle in cycles],
            "cycle_lengths": lengths,
            "joint_period_lcm": 6 if sorted(lengths) == [2, 2, 3] else None,
            "maximum_transient": max(info["transient"] for info in graph.values()),
        },
        "xlat2": xlat2_analysis(),
        "word_model": {
            "generated_cells_evaluated": 6,
            "cycle_cells": 6,
            "formula": "M[i]=G[(i-N) mod 6] para i>=N, con G=M[N..N+5]",
            "scope": "cola generada por la recurrencia; las N celdas fuente se conservan literalmente",
        },
    }


def validate_tail_model(cases: Iterable[Sequence[int]]) -> dict:
    checked = 0
    mismatches = []
    for cells in cases:
        expected = naive_memory(cells)
        model = TailModel.from_cells(cells)
        actual = model.fill_memory()
        checked += 1
        if actual != expected:
            for index, (left, right) in enumerate(zip(actual, expected)):
                if left != right:
                    mismatches.append({"cells": list(cells), "index": index, "fast": left, "naive": right})
                    break
    return {"cases": checked, "mismatches": mismatches, "pass": not mismatches}
