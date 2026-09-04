#!/usr/bin/env python3
"""Compute a finite-amplitude pendulum period using standard-library Simpson quadrature."""

from __future__ import annotations

import json
import math
from pathlib import Path


def elliptic_k_simpson(modulus: float, panels: int = 20000) -> float:
    if panels <= 0 or panels % 2:
        raise ValueError("panels must be a positive even integer")
    width = (math.pi / 2) / panels

    def integrand(phi: float) -> float:
        return 1 / math.sqrt(1 - modulus * modulus * math.sin(phi) ** 2)

    total = integrand(0.0) + integrand(math.pi / 2)
    total += 4 * sum(integrand(index * width) for index in range(1, panels, 2))
    total += 2 * sum(integrand(index * width) for index in range(2, panels, 2))
    return width * total / 3


def main() -> int:
    length = 1.0
    gravity = 9.81
    theta_0 = 0.2
    period = 4 * math.sqrt(length / gravity) * elliptic_k_simpson(math.sin(theta_0 / 2))
    output = Path(__file__).parent / "verification/period-data.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {"length_m": length, "gravity_m_s2": gravity, "theta_0_rad": theta_0, "period_s": period, "method": "composite Simpson quadrature", "panels": 20000},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"period={period:.12f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
