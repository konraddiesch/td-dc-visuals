#!/usr/bin/env python3
"""
Analyze TouchDesigner .chan files: find local extrema between first and last peak,
plus mean, median, standard deviation, and variance per channel.

Usage:
    python3 chan_stats.py hitc_performance.chan
    python3 chan_stats.py hitc_performance.chan --channel sc_bass smsd_bass
"""

import sys
import argparse
from pathlib import Path

import numpy as np

def parse_chan(filepath: str):
    """Parse a .chan file into channel names and a numpy array of samples."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        lines = f.readlines()

    channel_names = None
    data_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            content = stripped.lstrip("#").strip()
            if "Channels:" in content or "Timestamps:" in content:
                continue
            potential_channels = content.split()
            if len(potential_channels) > 4 and all(":" not in c for c in potential_channels):
                channel_names = potential_channels
            continue

        if channel_names is not None:
            try:
                values = [float(v) for v in stripped.split()]
                data_lines.append(values)
            except ValueError:
                pass

    if not channel_names:
        print("No channel names found in header.", file=sys.stderr)
        sys.exit(1)

    data = np.array(data_lines)
    if data.size == 0:
        print("No data found in file.", file=sys.stderr)
        sys.exit(1)

    return channel_names, data


def find_peaks(signal: np.ndarray, min_distance: int = 5) -> np.ndarray:
    """Find indices of local maxima (peaks) in a 1D signal."""
    if len(signal) < 3:
        return np.array([], dtype=int)

    # A point is a peak if it's >= both neighbours and > at least one (excludes flat lines)
    is_peak = (signal[1:-1] >= signal[:-2]) & (signal[1:-1] >= signal[2:]) & ((signal[1:-1] > signal[:-2]) | (signal[1:-1] > signal[2:]))
    peak_indices = np.where(is_peak)[0] + 1  # shift by 1 for the slice offset

    if len(peak_indices) == 0:
        return peak_indices

    # Enforce min_distance: remove weaker peaks that are too close.
    # Also discard peaks too close to edges.
    valid = np.ones(len(peak_indices), dtype=bool)
    valid &= peak_indices >= min_distance
    valid &= peak_indices < len(signal) - min_distance

    filtered = peak_indices[valid]
    if len(filtered) <= 1:
        return filtered

    # Greedy highest-peak-preserving filter
    amplitudes = signal[filtered]
    order = np.argsort(amplitudes)[::-1]
    keep = np.ones(len(filtered), dtype=bool)
    for i in range(len(order)):
        if not keep[order[i]]:
            continue
        for j in range(i + 1, len(order)):
            if abs(int(filtered[order[i]]) - int(filtered[order[j]])) < min_distance:
                keep[order[j]] = False

    return np.sort(filtered[keep])


def analyze_channel(
    values: np.ndarray,
    peak_distance: int = 5,
) -> dict:
    """
    Analyze a single channel.

    Steps:
      1. Trim leading/trailing near-zero samples (< 1e-12).
      2. Find the first and last peak (local maximum) in the trimmed signal.
      3. Report the *local* minimum between those two peaks.
      4. Compute mean, median, std, variance over the trimmed signal.
    """
    # Trim leading/trailing zeros
    nonzero = np.where(np.abs(values) > 1e-12)[0]
    if len(nonzero) < 2:
        trimmed = values
        first_peak_idx = None
        last_peak_idx = None
        local_min = float(values.min())
        local_min_at = np.argmin(values)
    else:
        trimmed = values[nonzero[0] : nonzero[-1] + 1]
        start_offset = nonzero[0]

        peaks = find_peaks(trimmed, peak_distance)

        if len(peaks) >= 2:
            first_peak_idx = int(peaks[0])
            last_peak_idx = int(peaks[-1])
            segment = trimmed[first_peak_idx : last_peak_idx + 1]
            local_min = float(segment.min())
            local_min_at = int(np.argmin(segment)) + first_peak_idx + start_offset
        elif len(peaks) == 1:
            # Only one peak — min is either side of it
            first_peak_idx = int(peaks[0])
            last_peak_idx = first_peak_idx
            left_min = trimmed[:first_peak_idx + 1].min()
            right_min = trimmed[first_peak_idx:].min()
            local_min = min(left_min, right_min)
            local_min_at = int(np.argmin(trimmed)) + start_offset
        else:
            # No peaks at all — fall back to global min of trimmed signal
            first_peak_idx = None
            last_peak_idx = None
            local_min = float(trimmed.min())
            local_min_at = int(np.argmin(trimmed)) + start_offset

    return {
        "trimmed_length": len(trimmed),
        "zeros_trimmed": len(values) - len(trimmed),
        "global_max": float(trimmed.max()),
        "global_max_at": int(np.argmax(trimmed)) + (nonzero[0] if len(nonzero) >= 2 else 0),
        "first_peak_at": first_peak_idx + (nonzero[0] if len(nonzero) >= 2 else 0) if first_peak_idx is not None else None,
        "last_peak_at": last_peak_idx + (nonzero[0] if len(nonzero) >= 2 else 0) if last_peak_idx is not None else None,
        "local_min": local_min,
        "local_min_at": local_min_at,
        "mean": float(np.mean(trimmed)),
        "median": float(np.median(trimmed)),
        "std": float(np.std(trimmed)),
        "variance": float(np.var(trimmed)),
    }


def fmt(val, width=12):
    """Format a float or None for table output."""
    if val is None:
        return "—".rjust(width)
    if isinstance(val, int):
        return str(val).rjust(width)
    return f"{val:.6f}".rjust(width)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze .chan files: local extrema between peaks + statistics."
    )
    parser.add_argument("file", help="Path to .chan file")
    parser.add_argument(
        "-c", "--channel", nargs="+",
        help="Channel(s) to analyze (default: all).",
    )
    parser.add_argument(
        "--peak-distance", type=int, default=5,
        help="Minimum distance between peaks in samples (default: 5)",
    )
    args = parser.parse_args()

    channel_names, data = parse_chan(args.file)

    if args.channel:
        indices = []
        for ch in args.channel:
            if ch in channel_names:
                indices.append(channel_names.index(ch))
            else:
                print(f"Warning: channel '{ch}' not found. Available: {channel_names}", file=sys.stderr)
        if not indices:
            print("No valid channels specified.", file=sys.stderr)
            sys.exit(1)
    else:
        indices = list(range(len(channel_names)))

    print(f"File: {args.file}")
    print(f"Samples: {data.shape[0]}, Channels: {data.shape[1]}")
    print(f"Duration: {data.shape[0] / 60:.1f}s @ 60 Hz\n")

    header = (
        f"{'Channel':<18} {'GlobalMax':>12} {'@sample':>8} "
        f"{'LocalMin':>12} {'@sample':>8} "
        f"{'Mean':>12} {'Median':>12} {'StdDev':>12} {'Variance':>12} {'Trimmed':>8}"
    )
    print(header)
    print("-" * len(header))

    for idx in indices:
        name = channel_names[idx]
        st = analyze_channel(data[:, idx], args.peak_distance)
        print(
            f"{name:<18}"
            f" {fmt(st['global_max'])} {fmt(st['global_max_at'], 8)}"
            f" {fmt(st['local_min'])} {fmt(st['local_min_at'], 8)}"
            f" {fmt(st['mean'])} {fmt(st['median'])}"
            f" {fmt(st['std'])} {fmt(st['variance'])}"
            f" {fmt(st['zeros_trimmed'], 8)}"
        )


if __name__ == "__main__":
    main()