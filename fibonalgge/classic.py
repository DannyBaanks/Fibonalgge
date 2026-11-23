"""Semántica e instrumentación de Classic Malbolge (Olmstead 1998).

El trazador es código de observación. No introduce operaciones nuevas en la VM.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import hashlib
import sys
from typing import Callable, Iterator, Sequence

MEM_SIZE = 3**10
MAX_VALUE = MEM_SIZE - 1
EOF_VALUE = MAX_VALUE
XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
XLAT2 = "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
VALID_OPS = frozenset("ji*p</vo")
ASCII_WHITESPACE = frozenset(b" \t\n\r\v\f")

# Filas = trit del operando izquierdo x; columnas = trit del derecho y.
CRZ_TABLE = (
    (1, 1, 2),
    (0, 0, 2),
    (0, 2, 1),
)


def _check_word(value: int) -> None:
    if not 0 <= value <= MAX_VALUE:
        raise ValueError(f"palabra fuera de rango: {value}")


def crz_trit(x: int, y: int) -> int:
    """Crazy de dos trits, con orden de operandos explícito."""
    if x not in (0, 1, 2) or y not in (0, 1, 2):
        raise ValueError("los operandos de crz_trit deben ser trits")
    return CRZ_TABLE[x][y]


def crazy(x: int, y: int) -> int:
    """Crazy sobre exactamente diez trits, sin acarreo entre posiciones."""
    _check_word(x)
    _check_word(y)
    result = 0
    place = 1
    for _ in range(10):
        result += CRZ_TABLE[x % 3][y % 3] * place
        x //= 3
        y //= 3
        place *= 3
    return result


def rotate(value: int) -> int:
    _check_word(value)
    return value // 3 + (value % 3) * 3**9


def decode(value: int, address: int) -> str:
    if not 33 <= value <= 126:
        raise ValueError(f"celda no imprimible en {address}: {value}")
    return XLAT1[(value - 33 + address) % 94]


def load_cells(source: bytes, *, strict: bool = True) -> list[int]:
    """Carga fuente Classic; no rellena memoria ni normaliza bytes inválidos."""
    cells: list[int] = []
    for offset, byte in enumerate(source):
        if byte in ASCII_WHITESPACE:
            continue
        if not 33 <= byte <= 126:
            raise ValueError(f"byte no imprimible 0x{byte:02x} en offset {offset}")
        if strict and decode(byte, len(cells)) not in VALID_OPS:
            raise ValueError(f"opcode inicial inválido en celda {len(cells)}")
        cells.append(byte)
    if not 2 <= len(cells) <= MEM_SIZE:
        raise ValueError("el programa debe ocupar entre 2 y 59049 celdas")
    return cells


def naive_memory(cells: Sequence[int]) -> list[int]:
    """Relleno literal de referencia; se conserva como control del modelo rápido."""
    if not 2 <= len(cells) <= MEM_SIZE:
        raise ValueError("se requieren 2..59049 celdas iniciales")
    mem = list(cells)
    while len(mem) < MEM_SIZE:
        mem.append(crazy(mem[-1], mem[-2]))
    return mem


@dataclass(frozen=True, slots=True)
class TailModel:
    """Modelo exacto de la cola: seis palabras generadas G0..G5.

    Para i >= N, M[i] = cycle[(i-N) mod 6]. Los dos estados transitorios del
    grafo de pares también producen una secuencia generada periódica desde G0.
    """

    cells: tuple[int, ...]
    cycle: tuple[int, ...]

    @classmethod
    def from_cells(cls, cells: Sequence[int]) -> "TailModel":
        if not 2 <= len(cells) <= MEM_SIZE:
            raise ValueError("se requieren 2..59049 celdas iniciales")
        source = tuple(cells)
        if len(source) == MEM_SIZE:
            return cls(source, ())
        left, right = source[-1], source[-2]
        generated: list[int] = []
        for _ in range(6):
            value = crazy(left, right)
            generated.append(value)
            left, right = value, left
        return cls(source, tuple(generated))

    @property
    def source_length(self) -> int:
        return len(self.cells)

    def value_at(self, index: int) -> int:
        if index < 0:
            raise IndexError(index)
        if index < self.source_length:
            return self.cells[index]
        if not self.cycle:
            raise IndexError(index)
        return self.cycle[(index - self.source_length) % 6]

    def fill_memory(self) -> list[int]:
        return [self.value_at(i) for i in range(MEM_SIZE)]

    def generated_values(self, count: int) -> Iterator[int]:
        if count < 0:
            raise ValueError("count debe ser no negativo")
        for offset in range(count):
            yield self.value_at(self.source_length + offset)


def memory_bytes(mem: Sequence[int]) -> bytes:
    """Snapshot binario canónico uint16 little-endian de las 59049 celdas."""
    if len(mem) != MEM_SIZE:
        raise ValueError("snapshot incompleto")
    words = array("H", mem)
    if sys.byteorder != "little":
        words.byteswap()
    return words.tobytes()


def memory_sha256(mem: Sequence[int]) -> str:
    return hashlib.sha256(memory_bytes(mem)).hexdigest()


@dataclass(slots=True)
class Machine:
    """VM estricta con eventos y escrituras explícitas."""

    mem: list[int]
    payload: bytes = b""
    a: int = 0
    c: int = 0
    d: int = 0
    input_cursor: int = 0
    steps: int = 0  # instrucciones completadas; como mb_ref, excluye 'v'
    events: int = 0  # fetchs, incluye HALT o fallo terminal
    output: bytearray = None  # type: ignore[assignment]
    terminal: str = "RUNNING"

    def __post_init__(self) -> None:
        if len(self.mem) != MEM_SIZE:
            raise ValueError("la VM requiere 59049 celdas")
        if self.output is None:
            self.output = bytearray()

    @classmethod
    def from_source(cls, source: bytes, payload: bytes = b"", *, fast: bool = True) -> "Machine":
        cells = load_cells(source)
        model = TailModel.from_cells(cells)
        mem = model.fill_memory() if fast else naive_memory(cells)
        return cls(mem=mem, payload=payload)

    def tick(self) -> dict:
        if self.terminal != "RUNNING":
            raise RuntimeError(f"VM terminal: {self.terminal}")
        event_index = self.events
        self.events += 1
        c_fetch = self.c
        d_before = self.d
        a_before = self.a
        cell_c = self.mem[c_fetch]
        event = {
            "event": event_index,
            "step": self.steps,
            "c_fetch": c_fetch,
            "d_before": d_before,
            "a_before": a_before,
            "cell_c": cell_c,
            "mem_d": self.mem[d_before],
            "opcode": None,
            "writes": [],
            "input_byte": None,
            "output_byte": None,
            "terminal": "RUNNING",
        }
        if not 33 <= cell_c <= 126:
            self.terminal = "NONPRINTABLE_PC"
            event["terminal"] = self.terminal
            event.update(a_after=self.a, c_after=self.c, d_after=self.d)
            return event

        opcode = decode(cell_c, c_fetch)
        event["opcode"] = opcode
        if opcode == "j":
            self.d = self.mem[self.d]
        elif opcode == "i":
            self.c = self.mem[self.d]
        elif opcode == "*":
            address = self.d
            old = self.mem[address]
            new = rotate(old)
            self.mem[address] = new
            self.a = new
            if old != new:
                event["writes"].append([address, old, new, "data"])
        elif opcode == "p":
            address = self.d
            old = self.mem[address]
            new = crazy(self.a, old)
            self.mem[address] = new
            self.a = new
            if old != new:
                event["writes"].append([address, old, new, "data"])
        elif opcode == "<":
            value = self.a & 255
            self.output.append(value)
            event["output_byte"] = value
        elif opcode == "/":
            if self.input_cursor < len(self.payload):
                value = self.payload[self.input_cursor]
                self.input_cursor += 1
            else:
                value = EOF_VALUE
            self.a = value
            event["input_byte"] = value
        elif opcode == "v":
            self.terminal = "HALT"
            event["terminal"] = self.terminal
            event.update(a_after=self.a, c_after=self.c, d_after=self.d)
            return event
        # Cualquier otro carácter decodificado es NOP, como en el switch C.

        event["c_encrypt"] = self.c
        current = self.mem[self.c]
        if not 33 <= current <= 126:
            self.terminal = "INVALID_ENCRYPTION"
            event["terminal"] = self.terminal
            event.update(a_after=self.a, c_after=self.c, d_after=self.d)
            return event
        encrypted = ord(XLAT2[current - 33])
        self.mem[self.c] = encrypted
        if current != encrypted:
            event["writes"].append([self.c, current, encrypted, "encrypt"])
        self.c = (self.c + 1) % MEM_SIZE
        self.d = (self.d + 1) % MEM_SIZE
        self.steps += 1
        event.update(a_after=self.a, c_after=self.c, d_after=self.d)
        return event

    def run(self, max_steps: int, on_event: Callable[[dict, "Machine"], None] | None = None) -> None:
        if max_steps < 0:
            raise ValueError("max_steps debe ser no negativo")
        while self.steps < max_steps and self.terminal == "RUNNING":
            event = self.tick()
            if on_event is not None:
                on_event(event, self)
        if self.terminal == "RUNNING" and self.steps == max_steps:
            self.terminal = "MAX_STEPS"

    def result(self) -> dict:
        return {
            "terminal": self.terminal,
            "steps": self.steps,
            "events": self.events,
            "a": self.a,
            "c": self.c,
            "d": self.d,
            "input_cursor": self.input_cursor,
            "output_hex": bytes(self.output).hex(),
            "output_sha256": hashlib.sha256(self.output).hexdigest(),
            "memory_sha256": memory_sha256(self.mem),
        }
