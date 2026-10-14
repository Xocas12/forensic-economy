"""Simulated size and power of the proxy-free smoothness test, per detrending and series type.

Both projects plan a driver-free smoothness test over
:func:`forensics_core.dispersion.underdispersion.too_smooth_test`: gosplan on reported harvest
*levels*, china on provincial *growth rates*. Which ``detrend`` is valid depends on how an
honest series of that type is generated, and the library's own docstring says the default
``"diff"`` has essentially no power on stationary or trend-stationary series while ``"none"``
flags any trend. This script puts numbers on that at the sample sizes the projects can reach,
so the choice can be stated in the pre-registration with its size and power next to it.

Everything here is synthetic. No project data is read, and the output is a property of the
test, not a finding about any series.

Series types (unit-variance noise; the ratio is scale-invariant, so only shapes matter):

``levels`` (gosplan harvest levels): honest = linear trend (slope 1 noise s.d. per period)
plus iid noise. Smoothed versions keep the trend and replace the noise with a three-point
moving average (``ma3``), an AR(1) with rho 0.9 scaled to unit variance (``ar09``), or the
honest series passed through :func:`forensics_core.inject.inject_smoothing` with
``retain=0.1`` (``inject``).

``growth`` (china growth rates): honest = iid around a constant mean (``iid``), or a
persistent honest process, AR(1) with rho 0.7 (``ar07``) or a random walk (``rw``). Smoothed
versions are the same three shapes as for levels, applied to iid growth with no trend, plus
:func:`~forensics_core.inject.inject_smoothing` applied to each persistent honest process, so
power is also reported against a persistent baseline.

Run from the repository root::

    uv run python scripts/smoothness_size_power.py            # the table in the docs
    uv run python scripts/smoothness_size_power.py --reps 50  # quicker, noisier
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

import numpy as np
from forensics_core.dispersion.underdispersion import too_smooth_test
from forensics_core.inject import inject_smoothing

DETRENDS = ("none", "linear", "diff")


def _ar1(n: int, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Stationary AR(1) with unit marginal variance."""
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    scale = np.sqrt(1.0 - rho**2)
    for t in range(1, n):
        x[t] = rho * x[t - 1] + scale * e[t]
    return x


def _ma3(n: int, rng: np.random.Generator) -> np.ndarray:
    """Three-point moving average of iid noise, scaled to unit variance."""
    e = rng.standard_normal(n + 2)
    return (e[:-2] + e[1:-1] + e[2:]) / np.sqrt(3.0)


def _inject(base: np.ndarray) -> np.ndarray:
    return inject_smoothing(base, retain=0.1)[0]


Generator = Callable[[int, np.random.Generator], np.ndarray]


def _levels() -> dict[str, tuple[str, Generator]]:
    def trend(n: int) -> np.ndarray:
        return np.arange(n, dtype=float)

    return {
        "trend + iid": ("honest", lambda n, r: trend(n) + r.standard_normal(n)),
        "trend + ma3": ("smoothed", lambda n, r: trend(n) + _ma3(n, r)),
        "trend + ar09": ("smoothed", lambda n, r: trend(n) + _ar1(n, 0.9, r)),
        "inject(trend + iid)": (
            "smoothed",
            lambda n, r: _inject(trend(n) + r.standard_normal(n)),
        ),
    }


def _growth() -> dict[str, tuple[str, Generator]]:
    return {
        "iid": ("honest", lambda n, r: r.standard_normal(n)),
        "ar07": ("honest", lambda n, r: _ar1(n, 0.7, r)),
        "rw": ("honest", lambda n, r: np.cumsum(r.standard_normal(n))),
        "ma3": ("smoothed", lambda n, r: _ma3(n, r)),
        "ar09": ("smoothed", lambda n, r: _ar1(n, 0.9, r)),
        "inject(iid)": ("smoothed", lambda n, r: _inject(r.standard_normal(n))),
        "inject(ar07)": ("smoothed", lambda n, r: _inject(_ar1(n, 0.7, r))),
        "inject(rw)": ("smoothed", lambda n, r: _inject(np.cumsum(r.standard_normal(n)))),
    }


FAMILIES: dict[str, Callable[[], dict[str, tuple[str, Generator]]]] = {
    "levels": _levels,
    "growth": _growth,
}


def rejection_rate(
    make: Generator,
    n: int,
    detrend: str,
    *,
    reps: int,
    n_perm: int,
    alpha: float,
    seed: int,
) -> float:
    """Share of ``reps`` synthetic series of length ``n`` that the test rejects at ``alpha``."""
    rng = np.random.default_rng(seed)
    hits = 0
    for i in range(reps):
        x = make(n, rng)
        res = too_smooth_test(x, detrend=detrend, n_perm=n_perm, seed=seed + i)
        hits += res.pvalue <= alpha
    return hits / reps


def table(
    family: str,
    sizes: list[int],
    *,
    reps: int,
    n_perm: int,
    alpha: float,
    seed: int,
) -> list[dict[str, object]]:
    """One row per (series, detrend, n): kind (honest = size, smoothed = power) and the rate."""
    rows = []
    for k, (series, (kind, make)) in enumerate(FAMILIES[family]().items()):
        for detrend in DETRENDS:
            for n in sizes:
                rate = rejection_rate(
                    make,
                    n,
                    detrend,
                    reps=reps,
                    n_perm=n_perm,
                    alpha=alpha,
                    seed=seed + 1000 * k + n,
                )
                rows.append(
                    {
                        "family": family,
                        "series": series,
                        "kind": kind,
                        "detrend": detrend,
                        "n": n,
                        "rate": rate,
                    }
                )
    return rows


def to_markdown(rows: list[dict[str, object]], sizes: list[int]) -> str:
    head = "| series | honest/smoothed | detrend | " + " | ".join(f"n={n}" for n in sizes) + " |"
    sep = "|---|---|---|" + "---:|" * len(sizes)
    lines = [head, sep]
    keyed: dict[tuple[object, object, object], dict[object, object]] = {}
    for r in rows:
        keyed.setdefault((r["series"], r["kind"], r["detrend"]), {})[r["n"]] = r["rate"]
    for (series, kind, detrend), by_n in keyed.items():
        cells = " | ".join(f"{by_n[n]:.2f}" for n in sizes)
        lines.append(f"| {series} | {kind} | {detrend} | {cells} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--family", choices=sorted(FAMILIES), action="append")
    p.add_argument("--sizes", type=int, nargs="+", default=[10, 15, 20, 25, 30])
    p.add_argument("--reps", type=int, default=300)
    p.add_argument("--n-perm", type=int, default=199)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=20261014)
    a = p.parse_args(argv)
    print(
        f"reps={a.reps}, n_perm={a.n_perm}, alpha={a.alpha}, seed={a.seed}. "
        "Honest rows are size, smoothed rows are power."
    )
    for family in a.family or ["levels", "growth"]:
        rows = table(family, a.sizes, reps=a.reps, n_perm=a.n_perm, alpha=a.alpha, seed=a.seed)
        print(f"\n### {family}\n")
        print(to_markdown(rows, a.sizes))


if __name__ == "__main__":
    main()
