# AGENTS.md

TouchDesigner audio-reactive visual setup for live gigging. All editing happens in the TouchDesigner GUI — `.toe` files are the project, `.tox` files are loadable components.

## Architecture

Main entrypoint: `digital_carbs_visuals.toe` (loads all .tox components). Standalone backup at `digital_carbs_visuals.26.toe`; older backups in `Backup/` (`.11`–`.25`).

| Directory | Notable contents |
|---|---|
| `audio_analysis/` | `dc_audio_analysis_v1.tox` — FFT + audio features |
| `midi/` | `dc_midi.tox` — MIDI input/mapping |
| `led/` | `LED_TUBES_SIM_v2.tox` — LED tube sim + DMX |
| `post/` | `dc_post_adjust.tox` — post-processing |
| `visuals/BASE/` | `dc_visuals_base_v2.tox` — template for song visuals |
| `visuals/what_if/` | `dc_what_if_v1.tox` — completed song visual |
| `visuals/MISC/` | `trippy1.tox`, `trippy2.tox` — utility visuals |
| `visuals/hitc/` | `hitc_performance.chan` — performance recording only, no .tox |
| `visuals/exploding_whale/`, `just_so_you_know/`, `mr_five/` | Empty/WIP, no .tox |

## Creating a new song visual

1. Copy `visuals/BASE/dc_visuals_base_v2.tox` into a new dir under `visuals/`
2. Name `<artist>_<song>_v1.tox` (e.g. `dc_what_if_v1.tox`)
3. Load into `digital_carbs_visuals.toe` in TouchDesigner
4. After editing any .tox, re-save the main .toe to update references

## `.chan` files (performance recordings)

Recorded at 60 fps, space-separated floats, one row per frame. Comment lines start with `#`. Header lists channel names (e.g. `smsd_bass fmsd_bass sc_bass`). The only `.chan` file is `visuals/hitc/hitc_performance.chan`.

## Python tools

Dependencies: `numpy`, `matplotlib`.

- `python3 tools/chan_stats.py <file.chan>` — per-channel stats. Flags: `--channel`, `--peak-distance`
- `python3 tools/plot_chan.py <file.chan>` — plot channel data. Flags: `--channels`, `--output`, `--summary`, `--window`

MCP server at `tools/chan_mcp.py` auto-registers `chan_list`, `chan_info`, `chan_analyze`, `chan_plot` via `.claude/settings.json`. Path resolution: absolute → project root → `visuals/<path>`.

## Gotchas

- No build system, linters, tests, or typecheck — pure TouchDesigner
- No `.gitignore` exists; `.DS_Store` and `__pycache__` are tracked
- Backups are manual `.toe` copies with incrementing numbers
- `CLAUDE.md` exists but is secondary — prefer this file
