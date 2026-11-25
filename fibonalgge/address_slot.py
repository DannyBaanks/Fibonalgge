"""MAL-E02: slot reutilizable de direcciones completas de diez trits.

El experimento separa tres cosas que no deben confundirse:

1. **Álgebra del slot** (modelo exhaustivo): construir una palabra de diez
   trits desde una máscara `29524`, escribirla exactamente en un slot y
   rearmarlo. Se comprueba para las 59 049 palabras.
2. **Imagen Classic de un ciclo**: una imagen real guarda `target - 1` en un
   slot, salta indirectamente a través de él y aterriza en `target` después del
   incremento obligatorio de `c`. La celda del nuevo `c` se cifra.
3. **Repetición en la misma imagen**: se modela, pero no se atribuye a la
   imagen de un ciclo. La composición con dos slots y retornos físicos queda
   como el siguiente paso, no como resultado de este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Sequence

from .classic import (
    MEM_SIZE,
    Machine,
    TailModel,
    XLAT2,
    crazy,
    load_cells,
    rotate,
)
from .planner import DATA_HI, DATA_LO, OPS, Planner, enc

# Constantes del protocolo de escritura exacta.
MASK_ALL_ONES = 29524          # 111...111_3
MASK_ROT_SOURCE = 54           # 2000_3, una sola posición con trit 2
REARM_WORD = MASK_ALL_ONES

# Layout fijo de la imagen de un ciclo. Las celdas 41..126 son datos.
M = 41                         # fuente invariante de 29524
A = 42                         # scratch de escritura
P = 43                         # payload que se construye
S = 44                         # slot de dirección
PTR = 45                       # S+1: apunta a T, leído por el DLOAD del target
R = 110                        # código OUT del retorno
RH = 111                       # código HALT del retorno
FIXED_DATA = frozenset({M, A, P, S, PTR, R, RH})


@dataclass(frozen=True, slots=True)
class BuiltImage:
    image: bytes
    target: int
    slot_value: int
    slot_addr: int
    pointer_addr: int
    pointer_value: int
    target_pointer_addr: int
    return_addr: int
    halt_addr: int
    sentinel_addr: int
    sentinel_value: int
    masks: tuple[int, ...]
    summary: object

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.image).hexdigest()

    @property
    def expected_output(self) -> int:
        return self.slot_value & 0xFF


def trits(value: int) -> tuple[int, ...]:
    """Diez trits, del menos significativo al más significativo."""
    if not 0 <= value < MEM_SIZE:
        raise ValueError(f"palabra fuera de rango: {value}")
    return tuple((value // 3**i) % 3 for i in range(10))


def word_from_trits(values: Sequence[int]) -> int:
    if len(values) != 10:
        raise ValueError("se requieren diez trits")
    out = 0
    for position, value in enumerate(values):
        if value not in (0, 1, 2):
            raise ValueError(f"trit inválido: {value}")
        out += value * 3**position
    return out


def has_no_zero_trit(value: int) -> bool:
    return all(trit in (1, 2) for trit in trits(value))


def twos_positions(value: int) -> tuple[int, ...]:
    return tuple(i for i, trit in enumerate(trits(value)) if trit == 2)


def swap01(value: int) -> int:
    """Intercambia los trits 0 y 1; deja los 2 intactos."""
    return crazy(value, MASK_ALL_ONES)


def exact_write_model(value: int, *, a: int | None = None,
                      scratch: int = MASK_ALL_ONES,
                      slot: int = MASK_ALL_ONES) -> tuple[int, int, int]:
    """Modelo de `p` sobre scratch y después sobre slot.

    Devuelve `(slot, scratch, a)`. Para cualquier `value`, el slot termina
    exactamente en `value`; `a` termina en `value` y el scratch en `swap01`.
    """
    if a is None:
        a = value
    scratch = crazy(a, scratch)
    a = scratch
    slot = crazy(scratch, slot)
    a = slot
    return slot, scratch, a


def rearm_model(value: int) -> tuple[int, int]:
    """Devuelve `(slot_rearmado, a_final)` para un slot que contiene `value`.

    Primero `crazy(29524, value)`; después `crazy(resultado, resultado)`.
    La segunda operación convierte cualquier palabra de sólo 0/2 en
    `29524`; si el primer resultado es 0 también produce `29524`.
    """
    first = crazy(MASK_ALL_ONES, value)
    second = crazy(first, first)
    return second, second


def model_exhaustive() -> dict:
    """Comprueba escritura exacta y rearme para las 59 049 palabras."""
    write_failures = []
    rearm_failures = []
    for value in range(MEM_SIZE):
        slot, _, a = exact_write_model(value)
        if slot != value or a != value:
            write_failures.append({"value": value, "slot": slot, "a": a})
        rearmed, a_final = rearm_model(value)
        if rearmed != MASK_ALL_ONES or a_final != MASK_ALL_ONES:
            rearm_failures.append({"value": value, "rearmed": rearmed,
                                   "a": a_final})
    return {
        "domain": MEM_SIZE,
        "write_failures": write_failures,
        "rearm_failures": rearm_failures,
        "exact_write_ok": not write_failures,
        "rearm_ok": not rearm_failures,
    }


def model_sequence(targets: Iterable[int]) -> dict:
    """Modelo de varios ciclos: escribir, saltar, rearmar y repetir."""
    slot = MASK_ALL_ONES
    rows = []
    for target in targets:
        slot_value = (target - 1) % MEM_SIZE
        written, _, _ = exact_write_model(slot_value, a=slot_value, slot=slot)
        landing = (written + 1) % MEM_SIZE
        rearmed, _ = rearm_model(written)
        rows.append({
            "target": target,
            "slot_value": slot_value,
            "written_ok": written == slot_value,
            "landing": landing,
            "landing_ok": landing == target,
            "rearmed": rearmed,
            "rearm_ok": rearmed == MASK_ALL_ONES,
        })
        slot = rearmed
    return {
        "cycles": len(rows),
        "all_ok": all(row["written_ok"] and row["landing_ok"] and row["rearm_ok"]
                      for row in rows),
        "rows": rows,
    }


def _allocate_masks(count: int, reserved: set[int]) -> list[int]:
    if count == 0:
        return []
    masks = []
    for addr in range(90, DATA_HI + 1):
        if addr in reserved:
            continue
        if addr in FIXED_DATA:
            continue
        masks.append(addr)
        if len(masks) == count:
            return masks
    raise ValueError("no hay celdas de dato suficientes para las máscaras")


def build_one_cycle(target: int, *, store_value: int | None = None,
                    max_masks: int = 10) -> BuiltImage:
    """Construye una imagen Classic de un ciclo que salta a `target`.

    `target` es la dirección que se ejecuta después del salto. El slot guarda
    `target - 1` para compensar el incremento obligatorio de `c`.
    `store_value` permite el control negativo: guardar otra palabra para que el
    aterrizaje no sea `target`.
    """
    if not (DATA_HI < target < MEM_SIZE - 1):
        raise ValueError(f"target fuera de la zona alta: {target}")
    slot_value = (target - 1) % MEM_SIZE
    if store_value is None:
        store_value = slot_value
    if not has_no_zero_trit(store_value):
        raise ValueError("el payload debe tener sólo trits 1/2 para construirse")
    if twos_positions(store_value) and len(twos_positions(store_value)) > max_masks:
        raise ValueError("el payload requiere más máscaras que las permitidas")

    # La celda T se elige para que el DLOAD del target lea PTR y aterrice en T.
    target_pointer = enc(target, OPS["DLOAD"]) + 1
    if not (DATA_LO <= target_pointer <= DATA_HI):
        raise ValueError(f"T={target_pointer} fuera de la zona de dato")
    reserved = set(FIXED_DATA) | {target_pointer}
    if target_pointer in (R, RH):
        raise ValueError("T colisiona con el retorno fijo")
    masks = _allocate_masks(len(twos_positions(store_value)), reserved)

    p = Planner()
    for cell in (M, A, P, S):
        p.seed_free(cell, 36)
    p.seed_free(PTR, target_pointer - 1)
    for mask in masks:
        p.seed_free(mask, MASK_ROT_SOURCE)
    p.seed_free(target_pointer, R - 1)
    p.seed_free(R, enc(R, OPS["OUT"]))
    p.seed_free(RH, enc(RH, OPS["END"]))

    # Bootstrap: el DLOAD de pc=0 lee su propia celda (40) y cae en M=41.
    p.seed_free(0, 40)
    p._emit("DLOAD", M)
    p.d = M
    p.crazy(M)  # M: 36 -> 29524; a = 29524

    # El código principal cabe en la zona B; el salto de zona se hace ahora
    # para no depender de una celda de salto comprometida en el límite.
    p.park()
    p.zone_jump()

    # Fábrica: A, P y S pasan de 36 a 29524.
    for cell in (A, P, S):
        p.ensure_d(cell)
        p.crazy(cell)
        p.ensure_d(cell)
        p.crazy(cell)

    # Payload: P = store_value, empezando en 29524 y poniendo un 2 por posición.
    for position, mask in zip(twos_positions(store_value), masks):
        rotations = (3 - position) % 10 or 10
        p.ensure_d(mask)
        for _ in range(rotations):
            p.rot(mask)
            p.ensure_d(mask)
        p.ensure_d(P)
        p.crazy(P)

    # Escritura exacta: A = swap(value), S = value.
    p.ensure_d(A)
    p.crazy(A)
    p.ensure_d(S)
    p.crazy(S)

    # Salto indirecto a través del slot.
    p.ensure_d(S)
    p.jmp()

    # Código del target y retorno de un ciclo.
    p.seed_free(target, enc(target, OPS["DLOAD"]))
    p.seed_free(target + 1, enc(target + 1, OPS["JMP"]))
    p.seed_free(target + 2, 42)

    image = p.to_bytes()
    return BuiltImage(
        image=image,
        target=target,
        slot_value=store_value,
        slot_addr=S,
        pointer_addr=PTR,
        pointer_value=target_pointer - 1,
        target_pointer_addr=target_pointer,
        return_addr=R,
        halt_addr=RH,
        sentinel_addr=target + 2,
        sentinel_value=42,
        masks=tuple(masks),
        summary=p.summary(),
    )


def wrong_store_value(target: int) -> int:
    """Una palabra vecina con trits 1/2 distinta de target-1.

    Sirve como control negativo: el salto debe aterrizar fuera de `target`.
    """
    value = (target - 1) % MEM_SIZE
    for candidate in (MASK_ALL_ONES, value + 1, value - 1):
        if 0 <= candidate < MEM_SIZE and has_no_zero_trit(candidate) and candidate != value:
            return candidate
    raise ValueError(f"no se encontró control negativo para {value}")


def build_default_targets() -> tuple[int, ...]:
    """Dos destinos altos con `target - 1` sin trits 0 y target % 94 == 35."""
    return (29645, 31713)


def run_image(image: bytes, *, max_steps: int = 100_000,
              capture_trace: bool = False) -> tuple[Machine, list[dict]]:
    cells = load_cells(image, strict=False)
    model = TailModel.from_cells(cells)
    machine = Machine(mem=model.fill_memory())
    trace: list[dict] = []

    def observe(event: dict, _vm: Machine) -> None:
        if capture_trace:
            trace.append(event)

    machine.run(max_steps, observe)
    return machine, trace


def validate_one_cycle(built: BuiltImage, *, negative: bool = False) -> dict:
    machine, trace = run_image(built.image, capture_trace=True)
    first_target_event = None
    jump_events = []
    landing_cell = built.slot_value % MEM_SIZE
    for event in trace:
        if event["c_fetch"] == built.target and first_target_event is None:
            first_target_event = event
        if event["opcode"] == "i" and event["c_encrypt"] == landing_cell:
            jump_events.append(event)

    initial_cells = load_cells(built.image, strict=False)
    initial_landing = initial_cells[landing_cell] if landing_cell < len(initial_cells) else None
    final_landing = machine.mem[landing_cell]

    if negative:
        first_jump = jump_events[0] if jump_events else None
        checks = {
            "slot_exact": machine.mem[built.slot_addr] == built.slot_value,
            "payload_exact": machine.mem[P] == built.slot_value,
            "mask_invariant": machine.mem[M] == MASK_ALL_ONES,
            "sentinel_preserved": machine.mem[built.sentinel_addr] == built.sentinel_value,
            "jump_encrypts_wrong_landing": first_jump is not None,
            "wrong_landing_not_target": first_jump is not None
            and first_jump["c_after"] != built.target
            and (built.slot_value + 1) % MEM_SIZE != built.target,
        }
    else:
        checks = {
            "terminal_halt": machine.terminal == "HALT",
            "output_expected": bytes(machine.output) == bytes([built.expected_output]),
            "slot_exact": machine.mem[built.slot_addr] == built.slot_value,
            "payload_exact": machine.mem[P] == built.slot_value,
            "scratch_swap": machine.mem[A] == swap01(built.slot_value),
            "mask_invariant": machine.mem[M] == MASK_ALL_ONES,
            "sentinel_preserved": machine.mem[built.sentinel_addr] == built.sentinel_value,
            "pointer_preserved": machine.mem[built.pointer_addr] == built.pointer_value,
            "first_target_pc": first_target_event is not None
            and first_target_event["c_fetch"] == built.target,
            "jump_encrypts_landing": any(e["c_encrypt"] == landing_cell for e in jump_events),
            "landing_changed": initial_landing is not None and final_landing != initial_landing,
            "target_cell_encrypted": machine.mem[built.target]
            != initial_cells[built.target],
            "return_cell_encrypted": machine.mem[built.return_addr]
            != initial_cells[built.return_addr],
            "target_successor_not_encrypted": machine.mem[built.target + 1]
            == initial_cells[built.target + 1],
        }
    return {
        "checks": checks,
        "ok": all(checks.values()),
        "terminal": machine.terminal,
        "output_hex": bytes(machine.output).hex(),
        "steps": machine.steps,
        "events": machine.events,
        "first_target_event": first_target_event,
        "jump_events": jump_events,
        "final": {
            "a": machine.a,
            "c": machine.c,
            "d": machine.d,
            "slot": machine.mem[built.slot_addr],
            "payload": machine.mem[P],
            "scratch": machine.mem[A],
            "mask": machine.mem[M],
            "sentinel": machine.mem[built.sentinel_addr],
            "target_cell": machine.mem[built.target],
            "target_successor": machine.mem[built.target + 1],
            "landing_cell": final_landing,
            "return_cell": machine.mem[built.return_addr],
        },
        "trace": trace,
    }
