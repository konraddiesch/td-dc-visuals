#!/usr/bin/env python3
"""
Plotter für TouchDesigner .chan-Dateien im hitc-Format.

Usage:
    python plot_chan.py hitc_performance.chan
    python plot_chan.py hitc_performance.chan --channels smsd_bass sc_bass
    python plot_chan.py hitc_performance.chan --output plot.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def parse_chan(filepath: str):
    """Parse a .chan file into channel names and a numpy array of samples."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        lines = f.readlines()

    # Kanalnamen aus dem Header extrazieren
    channel_names = None
    data_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            # Header: "# Thu Jun 11 14:42:31 2026:Channels:"
            # oder:    "# Thu Jun 11 14:42:31 2026:"
            if "Channels:" in stripped:
                # "Channels:" kann mit oder ohne vorherigen Timestamp kommen
                # Format: "# Thu Jun 11 14:42:31 2026:Channels:\n# name1 name2 ..."
                pass
            elif channel_names is None:
                # Nach dem Channels:-Header: "# smsd_bass fmsd_bass ..."
                # Aber auch Timestamps: "# Thu Jun 11 ...:"
                # Kanalzeilen haben KEINEN Doppelpunkt nach der Uhrzeit
                if "Timestamps:" in stripped:
                    continue
                # Wenn die Zeile Timestamps als Kommentar hat, überspringen
                content = stripped.lstrip("#").strip()
                # Check: Keine Timestamp-Zeile (kein ":" nach Uhrzeitmuster)
                # Einfacher: Wenn sie nur channel-like Tokens enthält, ist es die Kanalzeile
                potential_channels = content.split()
                if len(potential_channels) > 4 and all(":" not in c for c in potential_channels):
                    channel_names = potential_channels
            continue

        # Datenzeile: space-separated floats
        if channel_names is not None:
            try:
                values = [float(v) for v in stripped.split()]
                data_lines.append(values)
            except ValueError:
                # Kommentar mitten in Daten ignorieren
                pass

    if not channel_names:
        print("No channel names found in header.", file=sys.stderr)
        sys.exit(1)

    data = np.array(data_lines)
    if data.size == 0:
        print("No data found in file.", file=sys.stderr)
        sys.exit(1)

    return channel_names, data


def plot_channels(
    channel_names: list[str],
    data: np.ndarray,
    channels_to_plot: list[str] | None = None,
    output: str | None = None,
    window: int = 0,
    sample_rate: float = 60.0,
):
    """Plot selected or all channels from the data array."""
    num_cols = len(channel_names)

    if channels_to_plot:
        indices = []
        for ch in channels_to_plot:
            if ch in channel_names:
                indices.append(channel_names.index(ch))
            else:
                print(f"Warning: channel '{ch}' not found. Available: {channel_names}", file=sys.stderr)
        if not indices:
            print("No valid channels selected.", file=sys.stderr)
            sys.exit(1)
    else:
        indices = list(range(num_cols))

    time_axis = np.arange(data.shape[0]) / sample_rate

    if window > 0:
        data = data[-window:]
        time_axis = time_axis[-window:]
        if len(time_axis) == 0:
            time_axis = np.arange(data.shape[0]) / sample_rate

    n_plots = len(indices)
    cols = min(3, n_plots)
    rows = (n_plots + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(14, 2.5 * rows), squeeze=False)
    fig.suptitle(
        f"TouchDesigner .chan — {Path(output).name if output else 'hitc_performance'}",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])

    for idx, ax in enumerate(axes.flat):
        ax.grid(True, alpha=0.3)

    for i, ch_idx in enumerate(indices):
        row, col = divmod(i, cols)
        ax = axes[row][col]
        ax.plot(time_axis, data[:, ch_idx], linewidth=0.8)
        ax.set_title(channel_names[ch_idx], fontsize=10)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Value", fontsize=8)
        ax.tick_params(labelsize=7)

    # Leere Subplots ausblenden
    for i in range(n_plots, rows * cols):
        row, col = divmod(i, cols)
        axes[row][col].set_visible(False)

    if output:
        plt.savefig(output, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {output}")
    else:
        plt.show()


def summary(channel_names: list[str], data: np.ndarray):
    """Print a quick statistical summary of all channels."""
    print(f"Samples: {data.shape[0]}, Channels: {data.shape[1]}")
    print(f"Duration: {data.shape[0] / 60:.1f}s @ 60 Hz\n")
    print(f"{'Channel':<20} {'Min':>10} {'Max':>10} {'Mean':>10} {'Std':>10}")
    print("-" * 60)
    for name, col in zip(channel_names, data.T):
        print(f"{name:<20} {col.min():>10.6f} {col.max():>10.6f} {col.mean():>10.6f} {col.std():>10.6f}")


def main():
    parser = argparse.ArgumentParser(
        description="Plot TouchDesigner .chan files (hitc format)."
    )
    parser.add_argument("file", help="Path to .chan file")
    parser.add_argument(
        "-c", "--channels",
        nargs="+",
        help="Channels to plot (default: all). "
             "Available: smsd_bass, fmsd_bass, sc_bass, smsd_drums, ...",
    )
    parser.add_argument("-o", "--output", help="Save plot to file instead of showing")
    parser.add_argument(
        "-w", "--window", type=int, default=0,
        help="Only plot last N samples (e.g. 600 = 10s at 60 fps)",
    )
    parser.add_argument(
        "-s", "--sample-rate", type=float, default=60.0,
        help="Sample rate in Hz (default: 60)",
    )
    parser.add_argument("--summary", action="store_true", help="Print channel statistics and exit")

    args = parser.parse_args()

    channel_names, data = parse_chan(args.file)

    if args.summary:
        summary(channel_names, data)
        return

    plot_channels(
        channel_names,
        data,
        channels_to_plot=args.channels,
        output=args.output,
        window=args.window,
        sample_rate=args.sample_rate,
    )


if __name__ == "__main__":
    main()
