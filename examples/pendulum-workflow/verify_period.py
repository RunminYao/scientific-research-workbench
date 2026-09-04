#!/usr/bin/env python3
"""Independently verify the pendulum expansion using an AGM reference."""

from __future__ import annotations

import json
import math
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).parent


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def elliptic_k_agm(modulus: float) -> float:
    a = 1.0
    b = math.sqrt(1 - modulus * modulus)
    for _ in range(100):
        next_a = (a + b) / 2
        next_b = math.sqrt(a * b)
        if abs(next_a - next_b) < 1e-16:
            return math.pi / (2 * next_a)
        a, b = next_a, next_b
    raise RuntimeError("AGM did not converge")


def main() -> int:
    data = json.loads((ROOT / "verification/period-data.json").read_text(encoding="utf-8"))
    theta = data["theta_0_rad"]
    small = 2 * math.pi * math.sqrt(data["length_m"] / data["gravity_m_s2"])
    expansion = small * (1 + theta**2 / 16 + 11 * theta**4 / 3072)
    reference = 4 * math.sqrt(data["length_m"] / data["gravity_m_s2"]) * elliptic_k_agm(math.sin(theta / 2))
    quadrature_relative_error = abs(data["period_s"] - reference) / reference
    expansion_relative_error = abs(expansion - reference) / reference
    passed = quadrature_relative_error < 1e-11 and expansion_relative_error < 1e-7
    report = {
        "schema_version": 1,
        "passed": passed,
        "theta_0_rad": theta,
        "reference_period_s": reference,
        "quadrature_relative_error": quadrature_relative_error,
        "expansion_relative_error": expansion_relative_error,
        "tolerances": {"quadrature": 1e-11, "fourth_order_expansion": 1e-7},
        "limitation": "Validated only at theta_0=0.2 rad; the small-angle series is not asserted near pi.",
    }
    atomic_text(ROOT / "verification/report.json", json.dumps(report, indent=2) + "\n")
    suite = ET.Element("testsuite", name="pendulum", tests="1", failures="0" if passed else "1", errors="0")
    case = ET.SubElement(suite, "testcase", classname="pendulum", name="finite_amplitude_period")
    if not passed:
        ET.SubElement(case, "failure", message="pendulum tolerance exceeded")
    ET.SubElement(case, "system-out").text = json.dumps(report, sort_keys=True)
    atomic_text(ROOT / "verification/junit.xml", ET.tostring(suite, encoding="unicode", xml_declaration=True) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
