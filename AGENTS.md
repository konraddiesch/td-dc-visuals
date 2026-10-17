# AGENTS.md

TouchDesigner audio-reactive visual setup for live gigging. All editing happens in the TouchDesigner GUI — `.toe` files are the project, `.tox` files are loadable components.

## Architecture

Main entrypoint: `digital_carbs_visuals.toe` (loads all .tox components). TouchDesigner writes numbered `.toe` versions (`digital_carbs_visuals.N.toe`) and crash autosaves into the project root — these are gitignored. Manual backups live in `Backup/` (also gitignored).

| Directory | Notable contents |
|---|---|
| `audio_analysis/` | `dc_audio_analysis_v2.tox` — FFT + audio features; `calibrate.tox` |
| `midi/` | `dc_midi.tox` — MIDI input/mapping |
| `led/` | `LED_TUBES_SIM_v2.tox`, `astera_dmx_out_v6.tox`, `led_controls_v2.tox` |
| `post/` | `dc_post_adjust.tox` — post-processing |
| `player/` | `dc_movie_player.tox` + `stateMachine.py` |
| `visuals/BASE/` | `dc_visuals_base_v5.tox` — template for song visuals |
| `visuals/what_if/` | `dc_what_if_v1.tox` — completed song visual |
| `visuals/like_a_child/` | `like_a_child_v1.tox` — completed song visual |
| `visuals/MISC/` | `trippy1.tox`, `trippy2.tox` — utility visuals |
| `visuals/exploding_whale/`, `just_so_you_know/`, `mr_five/` | WIP, no .tox yet |
| `data/` | `.chan` performance recordings + plots, organized `data/<song>/<YYYYMMDD_ort>/` |

Each module keeps superseded versions in its own `old/` subdirectory (e.g. `led/old/`, `visuals/BASE/old/`).

## Creating a new song visual

1. Copy `visuals/BASE/dc_visuals_base_v5.tox` into a new dir under `visuals/`
2. Name `<artist>_<song>_v1.tox` (e.g. `dc_what_if_v1.tox`)
3. Load into `digital_carbs_visuals.toe` in TouchDesigner
4. After editing any .tox, re-save the main .toe to update references

## `.chan` files (performance recordings)

Recorded at 60 fps, space-separated floats, one row per frame. Comment lines start with `#`. Header lists channel names (e.g. `smsd_bass fmsd_bass sc_bass smsd_drums`). Stored under `data/<song>/<YYYYMMDD_ort>/`.

## Python tools

Dependencies: `numpy`, `matplotlib`.

- `python3 tools/chan_stats.py <file.chan>` — per-channel stats. Flags: `--channel`, `--peak-distance`
- `python3 tools/plot_chan.py <file.chan>` — plot channel data. Flags: `--channels`, `--output`, `--summary`, `--window`

MCP server at `tools/chan_mcp.py` auto-registers `chan_list`, `chan_info`, `chan_analyze`, `chan_plot` via `.claude/settings.json`. Path resolution: absolute → project root → `visuals/<path>`.

## Gotchas

- No build system, linters, tests, or typecheck — pure TouchDesigner
- `.toe` backups (`Backup/`, numbered root versions, `CrashAutoSave*`) are gitignored — only `digital_carbs_visuals.toe` is versioned
- Backups are manual `.toe` copies with incrementing numbers
- The repo lives on an exFAT volume; macOS creates `._*` AppleDouble files (gitignored) that can break `git gc` — delete them before running gc

## Session memory (MemPalace)

At the end of every session, automatically save a checkpoint to MemPalace so conversations persist across sessions:

- Call `mempalace_checkpoint` with the session's key decisions/outcomes as `items` (wing `td_dc_visuals`, room `decisions`), plus a `diary` entry (agent `opencode`, AAAK format).
- Do this without being asked — it is the default behavior.
- Keep items verbatim and concise; never summarize away specifics like file paths, commit hashes, or exact numbers.
