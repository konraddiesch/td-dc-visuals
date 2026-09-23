# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TouchDesigner-based audio-reactive visual setup for live gigging. The main project file (`digital_carbs_visuals.toe`) ties together modular .tox components that process audio and MIDI, generate reactive visuals, and output via DMX and media files.

## Architecture

The project is organized into independent modules loaded as .tox components:

- **`audio_analysis/`** — Audio analysis processing (FFT, audio features)
- **`midi/`** — MIDI input handling and mapping
- **`led/`** — LED tube simulation and DMX output
- **`post/`** — Post-processing adjustments on the final visual output
- **`visuals/BASE/`** — Base visual component template (`dc_visuals_base_v2.tox`), the foundation for song-specific visuals
- **`visuals/hitc/`** — "hitc" visual: includes performance channel recordings (.chan), a Python plotter tool, and test plots
- **`visuals/what_if/`** — "what if" visual component
- **`visuals/exploding_whale/`**, **`just_so_you_know/`**, **`mr_five/`** — Song-specific visual directories (currently empty, WIP)
- **`visuals/MISC/`** — Miscellaneous utility visuals (trippy1, trippy2)
- **`Backup/`** — Versioned .toe backup files (numbered .11 through .25)

## .chan File Format

Channel data files recorded at 60 fps. Each file has a header with channel names (e.g. `smsd_bass`, `fmsd_bass`, `sc_bass`, `smsd_drums`) followed by space-separated float samples — one row per frame, one column per channel.

## Tools (`tools/`)

Scripts for analyzing .chan performance recordings at `tools/`. MCP tools are auto-registered in `.claude/settings.json` — you can call them directly.

### MCP Tools (available as Claude Code tools)

| Tool | Description |
|---|---|
| `chan_list` | Find all .chan files in the project |
| `chan_info` | Quick overview: channels, duration, sample count |
| `chan_analyze` | Per-channel stats: global max, **local min** (between 1st & last peak), mean, median, std dev, variance |
| `chan_plot` | Generate a matplotlib plot saved as PNG |

### Standalone CLI

- **`python3 tools/chan_stats.py <file.chan>`** — Analyze with stats table.
  - `--channel sc_bass sc_drums` — specific channels
  - `--peak-distance 10` — adjust peak separation (default 5)
- **`python3 tools/plot_chan.py <file.chan>`** — Plot channel data.
  - `--channels smsd_bass sc_bass` — specific channels
  - `--output plot.png` — save to file
  - `--summary` — print statistics
  - `--window 600` — last N samples

## Key Patterns

- Visuals are organized by song/performance name as subdirectories under `visuals/`
- Each song-specific visual should start from or extend `visuals/BASE/dc_visuals_base_v2.tox`
- .tox files are TouchDesigner components that can be loaded into the main .toe project
- The main project file (`digital_carbs_visuals.toe`) orchestrates all components
- No build system, tests, or linters — this is a TouchDesigner project, all development happens in the TouchDesigner editor