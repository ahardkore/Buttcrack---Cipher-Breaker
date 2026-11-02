#!/usr/bin/env python3
"""Second-backend check of R16 UNKNOWN cases; same whole-packet constraints."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import nachtlorn_stored_gzip_probe as stored  # noqa: E402

try:
    import cvc5
except ImportError:
    cvc5 = None


class NumericValue:
    def __init__(self, value):
        self.value = value

    def as_long(self):
        return self.value


class CvcModel:
    def __init__(self, facade):
        self.facade = facade

    def eval(self, digit, model_completion=True):
        term = self.facade.symbols[digit.decl().name()]
        value = self.facade.solver.getValue(term).getBitVectorValue(10)
        return NumericValue(int(value))


class CvcFacade:
    """Minimal adapter for the shared enumerator, via standard SMT-LIB.

    The original Z3 context is used only to construct/serialize constraints and
    blocking clauses. cvc5 performs every check and supplies every model here.
    """
    def __init__(self, smt2):
        if cvc5 is None or stored.z3 is None:
            raise RuntimeError("optional cvc5 and z3-solver required; absent backend is not an exclusion")
        self.solver = cvc5.Solver()
        self.solver.setOption("produce-models", "true")
        self.solver.setOption("incremental", "true")
        self.solver.setOption("seed", str(stored.le.SEED))
        self.solver.setLogic("QF_BV")
        self.manager = cvc5.SymbolManager(self.solver)
        self.initial_smt2 = smt2
        self.result = None
        self.parse(smt2)
        self.symbols = {term.getSymbol(): term for term in self.manager.getDeclaredTerms()}

    def parse(self, text):
        parser = cvc5.InputParser(self.solver, self.manager)
        parser.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6, text, "stored-gzip")
        while True:
            command = parser.nextCommand()
            if command.isNull():
                break
            if command.getCommandName() == "check-sat":
                continue  # The shared enumerator owns the checks and deadline.
            output = command.invoke(self.solver, self.manager)
            if output.strip().startswith("(error"):
                raise RuntimeError(output)

    def to_smt2(self):
        return self.initial_smt2

    def set(self, *, timeout):
        self.solver.setOption("tlimit-per", str(timeout))

    def check(self):
        self.result = self.solver.checkSat()
        if self.result.isSat():
            return stored.z3.sat
        if self.result.isUnsat():
            return stored.z3.unsat
        return stored.z3.unknown

    def reason_unknown(self):
        return str(self.result.getUnknownExplanation())

    def model(self):
        return CvcModel(self)

    def add(self, constraint):
        self.parse("(assert " + constraint.sexpr() + ")")


def followup(text: str, previous: dict, *, budget_ms=stored.BUDGET_MS,
             candidate_cap=stored.CANDIDATE_CAP) -> dict:
    if cvc5 is None or stored.z3 is None:
        raise RuntimeError("optional cvc5 and z3-solver required")
    cases = []
    for model in previous["models"]:
        retained = text[:-1] if model["drop_final_i"] else text
        if model["drop_final_i"] and not text.endswith("I"):
            raise ValueError("recorded terminal-I model does not match source")
        bias = model["bias"]
        derived = stored.length_cases(retained, bias)
        for old_case in model["cases"]:
            if old_case["status"] != "unknown":
                continue
            case = {key: old_case[key] for key in ("minimal_bytes", "restored_trailing_zero_bytes",
                                                   "payload_bytes", "high_prefix_hex")}
            if case not in derived or len(retained) != model["retained_letters"]:
                raise ValueError("recorded length case disagrees with independent source derivation")
            result = stored.search_case(retained, bias, case, budget_ms=budget_ms, candidate_cap=candidate_cap,
                                        solver_adapter=CvcFacade)
            cases.append({"drop_final_i": model["drop_final_i"], "bias": bias, **result})
            print(json.dumps({"drop_final_i": model["drop_final_i"], "bias": bias,
                              "status": result["status"], "checked": result["candidate_numerals_checked"],
                              "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
    return {"status": "Independent backend for the same R16 constraints, not a new cipher model.",
            "solver": {"backend": "cvc5", "package_version": version("cvc5"),
                       "formula_builder_z3_version": stored.z3.get_version_string(),
                       "seed": stored.le.SEED, "case_budget_ms": budget_ms, "candidate_cap": candidate_cap},
            "cases": cases,
            "limits": ["Prior R16 exact exclusions are not rerun; only recorded UNKNOWN cases are selected.",
                       "Constraints, CRC checks and full-packet acceptance are unchanged.",
                       "Timeout or candidate cap remains incomplete, never an exclusion."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-ms", type=int, default=stored.BUDGET_MS)
    parser.add_argument("--candidate-cap", type=int, default=stored.CANDIDATE_CAP)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.previous.resolve()):
        parser.error("output must not overwrite the source or original result")
    if args.budget_ms < 1 or args.candidate_cap < 1:
        parser.error("positive budget and candidate cap required")
    raw = args.path.read_bytes()
    old_raw = args.previous.read_bytes()
    previous = json.loads(old_raw)
    source_hash = hashlib.sha256(raw).hexdigest()
    if previous.get("source_sha256") != source_hash:
        parser.error("original result refers to a different source")
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected original ASCII body")
    text = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = followup(text, previous, budget_ms=args.budget_ms, candidate_cap=args.candidate_cap)
    report["source_sha256"] = source_hash
    report["previous_result_sha256"] = hashlib.sha256(old_raw).hexdigest()
    report["previous_result"] = args.previous.as_posix()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
