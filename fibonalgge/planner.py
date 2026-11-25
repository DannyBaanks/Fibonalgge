"""Mini-planificador de imágenes Classic Malbolge con placement absoluto.

Adaptado para MAL-E02 del planificador de
`MALBOLGE-MB-DATABASE/vm_malbolge/evidence/epoch_resolver_word_v1/plan.py`
(sha256 del original registrado en `PROVENANCE.md`). La lógica de rutado y las
reglas de `d` se conservan; sólo se sustituye el oráculo externo por las
primitivas locales de `fibonalgge.classic`.

Reglas que implementa:

  * `d` arranca en 0 y avanza +1 por instrucción ejecutada.
  * DLOAD (`j`): `d = mem[d]`, luego `d += 1`.
  * CRAZY (`p`): `mem[d] = crazy(a, mem[d])`, `a = mem[d]`.
  * ROT (`*`): `mem[d] = rot(mem[d])`, `a = mem[d]`.
  * JMP (`i`): `c = mem[d]`; la ejecución sigue en `c + 1`.
  * La celda del nuevo `c` se cifra antes del incremento.

El planificador simula `d` y los valores de dato para sembrar celdas de salto
imprimibles (33..126). No sustituye a la VM: la imagen resultante se ejecuta con
`fibonalgge.classic.Machine` y con el runner C.
"""
from __future__ import annotations

from dataclasses import dataclass

from .classic import crazy, rotate

OPS = {
    "JMP": 4,
    "OUT": 5,
    "IN": 23,
    "ROT": 39,
    "DLOAD": 40,
    "CRAZY": 62,
    "NOP": 68,
    "END": 81,
}

ZONE_A_HI = 39
DATA_LO, DATA_HI = 41, 126
ZONE_B_LO = 127
MAX_HOP = DATA_HI


def enc(addr: int, op: int) -> int:
    """Celda imprimible que decodifica `op` cuando se ejecuta en `addr`."""
    return 33 + ((op - 33 - addr) % 94)


class PlanError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PlanSummary:
    instructions: int
    pc_end: int
    seeds: int
    hops: int
    final_d: int
    final_a: int


class Planner:
    def __init__(self) -> None:
        self.mem: dict[int, int] = {}
        self.sim: dict[int, int] = {}
        self.hop_used: dict[int, int] = {}
        self.code: list[tuple[int, str, object]] = []
        self.pc = 0
        self.d = 0
        self.a = 0
        self.log: list[dict] = []

    # ---------- siembra ----------
    def seed(self, addr: int, value: int) -> None:
        if addr in self.mem and self.mem[addr] != value:
            raise PlanError(f"celda {addr}: semilla {self.mem[addr]} vs {value}")
        if not 33 <= value <= 126:
            raise PlanError(f"semilla no imprimible en {addr}: {value}")
        self.mem[addr] = value
        self.sim[addr] = value

    def seed_free(self, addr: int, value: int) -> None:
        if addr in self.mem:
            raise PlanError(f"celda {addr} ya sembrada ({self.mem[addr]})")
        self.seed(addr, value)

    # ---------- emisión ----------
    def _d_cell_free(self) -> bool:
        return self.d not in self.mem and self.d not in self.hop_used

    def jmp(self) -> None:
        """JMP dinámico: `c = mem[d]`, luego la ejecución sigue en `c + 1`."""
        self._emit("JMP_DYN")
        self.d += 1

    def _raw_emit(self, name: str, arg: object = None) -> None:
        self.code.append((self.pc, name, arg))
        self.log.append({"pc": self.pc, "op": name, "arg": arg,
                         "d": self.d, "a": self.a})
        self.pc += 1

    def _prepare_boundary(self) -> None:
        while (ZONE_A_HI - 2 <= self.pc <= ZONE_A_HI - 1
               and not self._d_cell_free()):
            if self.pc == ZONE_A_HI - 1:
                self._raw_emit("NOP")
                self.d += 1
                if not self._d_cell_free():
                    raise PlanError(
                        f"sin margen para el JMP de zona: d={self.d} comprometida")
                return
            self._raw_emit("NOP")
            self.d += 1

    def park(self) -> None:
        while not self._d_cell_free():
            if self.d > DATA_HI - 8:
                raise PlanError(f"sin celdas libres cerca de d={self.d}")
            self._raw_emit("NOP")
            self.d += 1

    def zone_jump(self) -> None:
        if self.pc > ZONE_A_HI:
            raise PlanError("la zona A ya se agotó")
        if not self._d_cell_free():
            raise PlanError(f"JMP de zona con d={self.d} comprometida; llama park()")
        self.seed_free(self.d, ZONE_B_LO - 1)
        self.hop_used[self.d] = ZONE_B_LO
        self._raw_emit("JMP", ZONE_B_LO)
        self.pc = ZONE_B_LO
        self.d += 1
        self.log[-1]["jump_to"] = ZONE_B_LO

    def _emit(self, name: str, arg: object = None) -> None:
        self._prepare_boundary()
        if self.pc == ZONE_A_HI:
            addr = self.d
            if not (DATA_LO <= addr <= DATA_HI):
                raise PlanError(f"JMP de zona con d={addr} fuera de la zona de dato")
            if addr in self.hop_used and self.hop_used[addr] != ZONE_B_LO:
                raise PlanError(f"celda {addr} comprometida a {self.hop_used[addr]}")
            self.hop_used[addr] = ZONE_B_LO
            self.seed_free(addr, ZONE_B_LO - 1)
            self.code.append((self.pc, "JMP", ZONE_B_LO))
            self.log.append({"pc": self.pc, "op": "JMP", "arg": ZONE_B_LO,
                             "d": self.d, "a": self.a, "jump_to": ZONE_B_LO})
            self.pc = ZONE_B_LO
        if ZONE_A_HI < self.pc < ZONE_B_LO:
            raise PlanError(f"pc {self.pc} cae en la zona de dato")
        self.code.append((self.pc, name, arg))
        self.log.append({"pc": self.pc, "op": name, "arg": arg,
                         "d": self.d, "a": self.a})
        self.pc += 1

    def nop(self, n: int = 1) -> None:
        for _ in range(n):
            self._emit("NOP")
            self.d += 1

    def _hop(self, target: int) -> None:
        if target > MAX_HOP:
            raise PlanError(f"hop a {target} > {MAX_HOP}: valor no imprimible")
        addr = self.d
        if not (DATA_LO <= addr <= DATA_HI):
            raise PlanError(f"celda de salto {addr} fuera de la zona de dato")
        if addr in self.hop_used:
            if self.hop_used[addr] != target:
                raise PlanError(
                    f"conflicto de rutado: celda {addr} usada para "
                    f"{self.hop_used[addr]} y ahora para {target}")
        else:
            if addr in self.mem:
                self.seed(addr, target - 1)
            else:
                self.seed_free(addr, target - 1)
        self.hop_used[addr] = target
        self._emit("DLOAD", target)
        self.d = target

    def ensure_d(self, target: int) -> None:
        if self.d == target:
            return
        while self.d in self.mem and self.mem[self.d] != target - 1:
            if self.d > DATA_HI - 8:
                raise PlanError(f"d={self.d} demasiado alto para alcanzar {target}")
            self.nop(1)
        self._hop(target)

    def crazy(self, target: int) -> None:
        assert self.d == target, f"d={self.d} != {target}"
        old = self.sim.get(target, enc(target, OPS["NOP"]))
        self._emit("CRAZY", target)
        new = crazy(self.a, old)
        self.sim[target] = new
        self.a = new
        self.d += 1

    def rot(self, target: int) -> None:
        assert self.d == target, f"d={self.d} != {target}"
        old = self.sim.get(target, enc(target, OPS["NOP"]))
        self._emit("ROT", target)
        new = rotate(old)
        self.sim[target] = new
        self.a = new
        self.d += 1

    def inn(self) -> None:
        self._emit("IN")
        self.d += 1

    def out(self) -> None:
        self._emit("OUT")
        self.d += 1

    def end(self) -> None:
        self._emit("END")
        self.d += 1

    # ---------- imagen ----------
    def to_bytes(self) -> bytes:
        last = max(list(self.mem) + [c[0] for c in self.code])
        by_pc = {pc: (pc, name, arg) for pc, name, arg in self.code}
        out = bytearray()
        for addr in range(last + 1):
            if addr in by_pc:
                op = OPS["JMP"] if by_pc[addr][1] == "JMP_DYN" else OPS[by_pc[addr][1]]
                out.append(enc(addr, op))
            elif addr in self.mem:
                out.append(self.mem[addr])
            else:
                out.append(enc(addr, OPS["NOP"]))
        return bytes(out)

    def summary(self) -> PlanSummary:
        return PlanSummary(
            instructions=len(self.code),
            pc_end=self.pc,
            seeds=len(self.mem),
            hops=len(self.hop_used),
            final_d=self.d,
            final_a=self.a,
        )
