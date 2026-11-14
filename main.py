#!/usr/bin/env python3
"""make.fun polymarket-faa-attribution-02 entry.

Reads each case's JSON from the input dir and writes one forecast file per
case to the output dir. Standard library only, no network, no threads, no
randomness: byte-identical output on repeated runs of the same case.
"""

import json
import math
import os
import sys
from statistics import median

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.674490, 0.0, 0.674490, 1.644854]
LB = 720  # lookback in minutes (prices) for the volatility estimate
MIN_SIGMA = 0.0006


def robust_sigma(prices):
    """Per-sqrt-minute volatility from the last LB prices' 1-minute diffs.

    Uses as many differences as exist (at least 2); falls back to MIN_SIGMA
    when there are fewer than 2 differences.
    """
    window = prices[-LB:]
    if len(window) < 2:
        return MIN_SIGMA
    d = [window[i + 1] - window[i] for i in range(len(window) - 1)]
    if len(d) < 2:
        return MIN_SIGMA
    md = median(d)
    sigma = 1.4826 * median([abs(v - md) for v in d])
    return max(sigma, MIN_SIGMA)


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def forecast(market, horizon):
    prices = market.get("prices") or []
    if prices:
        x = prices[-1]
    else:
        x = 0.5
    sigma = robust_sigma(prices)

    rows = []
    for h in range(1, horizon + 1):
        s = sigma * math.sqrt(h)
        m = x * (1.0 - 0.5 * math.sqrt(h / 240.0))
        q05 = m - 1.644854 * s
        q25 = m - 0.674490 * s
        q50 = m
        q75 = m + 0.674490 * s * 1.5
        q95 = m + 1.644854 * s * 1.5
        row = [clamp01(q05), clamp01(q25), clamp01(q50), clamp01(q75), clamp01(q95)]
        row.sort()  # enforce non-decreasing within the row
        row = [round(v, 6) for v in row]
        rows.append(row)
    return rows


def process_case(case_path):
    with open(case_path, "r", encoding="utf-8") as f:
        case = json.load(f)
    horizon = case["horizon_minutes"]
    forecasts = []
    for market in case["markets"]:
        forecasts.append({"id": market["id"], "q": forecast(market, horizon)})
    out_path = os.path.join(OUTPUT_DIR, os.path.splitext(os.path.basename(case_path))[0] + ".out")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"forecasts": forecasts}, separators=(",", ":")))
        f.write("\n")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1]:
        ids = [sys.argv[1]]
    else:
        ids = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in ids:
        process_case(os.path.join(INPUT_DIR, name))


if __name__ == "__main__":
    main()