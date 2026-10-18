# AGENTS.md

TouchDesigner audio-reactive visual setup for live gigging. All editing happens in the TouchDesigner GUI — `.toe` files are the project, `.tox` files are loadable components.

## Architecture

Main entrypoint: `digital_carbs_visuals.toe` (loads all .tox components). With TouchDesigner's **Increment Filename on Save** preference on, each save writes the next numbered file (`digital_carbs_visuals.N.toe`) into the project root and moves the previous file into `Backup/` — so the *open* project often shows a numbered name (e.g. `digital_carbs_visuals.1.toe`). That is normal TD behaviour, not an anomaly ([Troubleshooting in TouchDesigner](https://docs.derivative.ca/Troubleshooting_in_TouchDesigner)). Numbered root files and `Backup/` are gitignored; only `digital_carbs_visuals.toe` is versioned.

| Directory | Notable contents |
|---|---|
| `audio_analysis/` | `dc_audio_analysis_v2.tox` — FFT + audio features; `calibrate.tox` |
| `midi/` | `dc_midi.tox` — MIDI input/mapping |
| `led/` | `LED_TUBES_SIM_v2.tox`, `astera_dmx_out_v6.tox`, `led_controls_v2.tox` |
| `post/` | `dc_post_adjust.tox` — post-processing |
| `player/` | `dc_movie_player.tox` + `stateMachine.py` |
| `components/` | Reusable generic components (song-agnostic) — `point_network_v1.tox` |
| `visuals/BASE/` | `dc_visuals_base_v5.tox` — template for song visuals |
| `visuals/what_if/` | `dc_what_if_v1.tox` — completed song visual |
| `visuals/like_a_child/` | `like_a_child_v1.tox` — completed song visual |
| `visuals/MISC/` | `trippy1.tox`, `trippy2.tox` — utility visuals |
| `visuals/exploding_whale/`, `just_so_you_know/`, `mr_five/`, `hitc/` | WIP — no current .tox (old versions in their `old/`) |
| `data/` | `.chan` performance recordings + plots, organized `data/<song>/<YYYYMMDD_ort>/` |

Each module keeps superseded versions in its own `old/` subdirectory (e.g. `led/old/`, `visuals/BASE/old/`).

## Live project (running `.toe`)

Verified 2026-10-17. Top level of `digital_carbs_visuals.toe`: `songs` (containerCOMP — all song visuals, output switching and DMX), `dc_audio_analysis_v2`, `dc_midi_v1`, plus loose `audiodevin1`, `midiin1`, `speed1`, `switch1`, `null1`, `moviefileout1`, `perform`, `annotate1-3`. The `led/`, `post/`, `player/` `.tox` files exist on disk but are **not** loaded as top-level COMPs — LED/DMX output and song/state playback are integrated inside `songs` (POP-based DMX via `dmxoutPOP`, per-song `led_controls`/`LED`).

**Data flow**
- Audio: device + per-stem `audiodeviceinCHOP`s (SUM / DRUMS / DAN_IN / VOCALS / BASS_IN / WILLY_IN) → `dc_audio_analysis_v2/out1` = 18 channels (`smsd` / `fmsd` / `sc` × bass, drums, dan, willy, sum, voc) → `/songs` input 0.
- MIDI: `midiin1` → `speed1` → `switch1` (index 0) ← `dc_midi_v1/out1` (6 triggers: `willy_trig`, `snare_trig`, `kick_trig`, `dan_trig`, `ft_trig`, `tt_trig`) → `/songs` input 1.

**Song switching** — `songs/registry` (tableDAT, one song name per row) is the single source of truth. `songs/01_start` (`onStart`) auto-wires every registry row to `pop_switch`/`top_switch` (input order = row order) and feeds `audio_analysis_in` + `midi_in` into each song. The active song is `songs/constant1['SongNumber']` (0-based) → `lag1` → `lag1_export` (CHOP Export DAT) → exported to `pop_switch.index` **and** `top_switch.index`.

**Outputs**
- Video: `top_switch` → `top_switch_out` → `top_out_select` (select-by-path) → `top_out` (outTOP) → `perform` window (`winop = /songs/top_out`). Preview/record tap: `songs/preview_out` → `/null1` → `/moviefileout1`.
- DMX: `pop_switch` → `pop_switch_out` → `dmx_out_select` → `dmx_out` (`dmxoutPOP`, Enttec USB Pro, 44 Hz). **`dmx_out.active` is deliberately off** — enable it for a physical rig.
- `/perform` (windowCOMP): `size=automatic` (follows the 1280×720 TOP), `borders=off`, `alwaysontop=on`, `cursorvisible=nocursor`, `blocksleep=on`, `single=singledisplay`.

**Song registry (8, in switch order)**: `like_a_child`, `exploding_whale`, `cocoon`, `just_so_you_know`, `mr_five`, `win_some_lose_some`, `what_if`, `head_in_the_clouds`. Note: `cocoon`, `win_some_lose_some` and `head_in_the_clouds` have **no matching `visuals/` dir or `.tox`** — they live only inside the `.toe` (`head_in_the_clouds`'s WIP dir is `visuals/hitc/`).

## TouchDesigner MCP (live session)

The `touchdesigner` MCP drives the running TD instance (WebServer DAT, port 9981). Generic harness lives in the global opencode config: skill `touchdesigner-mcp`, agent + command `td` — **load the skill before any TD MCP work** (`/td <task>`). Full tool/workflow/persistence rules are in the skill; project-specifics:

- **Right project check**: the top level must show `songs`, `dc_audio_analysis_v2`, `dc_midi_v1` (plus `perform`, `moviefileout1`, `audiodevin1`, `midiin1`, …). If a scratch/default project is open, ask the user to open `digital_carbs_visuals.toe` first.
- **Harness code**: the TD-side MCP server that TD actually imports lives in `~/Code/touchdesigner-mcp/td` — the git clone of the fork — so the source you edit *is* the running server. `/mcp_webserver_base.par.externaltox` points directly at `<clone>/td/mcp_webserver_base.tox` and `import_modules.py` derives `<dirname>/modules` from that par. There is **no** separate extract copy any more: the old `~/TouchDesigner/touchdesigner-mcp` (a symlink since 2026-10-18) and `touchdesigner-mcp.extract-v2.1.0` were removed the same day. Runtime-required artifacts are gitignored: `td/modules/td_server/openapi_server/openapi/openapi.yaml` and `**/generated_handlers.py` (`node td/genHandlers.js`). Module edits do **not** take effect from a webserver `restart` pulse; you must re-import Python (clear `sys.modules` for `mcp`/`utils` and re-exec `/mcp_webserver_base/mcp_webserver_script`, or restart TouchDesigner). (An unrelated copy of just the `.tox` component lives in the `touchdesigner-wiki-mcp` project.)
- **Persistence**: save components as `.tox` under their module dir; re-save the main `.toe` with an explicit absolute path to this repo's root, `project.save('<repo-root>/digital_carbs_visuals.toe')` — `project.save()` without path writes numbered auto-versions (gitignored).
- **Namespaces**: `touchdesigner_*` (live), `touchdesigner-wiki_*` (docs), `chan-tools_*` (`.chan` data) — never mix.
- **Skill source (versioned)**: the skill text is authored in the `konraddiesch/touchdesigner-mcp` fork, branch `local/opencode-harness`, at `plugin/touchdesigner/skills/touchdesigner-mcp/SKILL.md` (clone: `~/Code/touchdesigner-mcp`). `~/.config/opencode/skills/touchdesigner-mcp/SKILL.md` is a **symlink** to it — never edit the global copy. After editing, `npm run plugin:sync` regenerates `plugins/touchdesigner/**` (CI's `plugin:check` compares byte-for-byte, so commit both trees). The same fork also versions the opencode-only harness — `opencode/agents/td.md` and `opencode/commands/td.md` — symlinked to `~/.config/opencode/agent/td.md` and `~/.config/opencode/command/td.md`; they are **not** packaged by `plugin:sync` (opencode frontmatter), and opencode only re-reads agent/command files on restart.

## Review agents (opencode)

Two read-only reviewers, both `mode: all` (Tab-selectable **and** launchable as a subagent), model `openrouter/z-ai/glm-5.3-flash`:

- **`reviewer`** — global, `~/.config/opencode/agents/reviewer.md`. Generic code/diff reviewer. Denies everything, then re-opens `read`/`glob`/`grep` and six read-only git commands (`git diff|log|status|show|blame|ls-files`). No MCP, no network — fully sealed.
- **`td-reviewer`** — this repo, `.opencode/agents/td-reviewer.md`. Only the delta that `AGENTS.md` does not already say (binaries, no toolchain, empty code surface) plus live-network verification through the read-only TD tools (`touchdesigner_get_*`, `touchdesigner_describe_td_tools`).

Both never edit. `AGENTS.md` reaches subagents automatically, so `td-reviewer` deliberately does **not** restate these conventions — if you change a convention here, do not copy it into the agent prompt.

## Creating a new song visual

1. Copy the live BASE instance (`songs/template`, sourced from `visuals/BASE/dc_visuals_base_v5.tox`) into a new dir under `visuals/`
2. Name `<artist>_<song>_v1.tox` (e.g. `dc_what_if_v1.tox`)
3. Load it into the `songs` COMP in `digital_carbs_visuals.toe`
4. Add the COMP's name as a row in `songs/registry` — row order defines the `SongNumber` index and `songs/01_start` wires it to `pop_switch`/`top_switch` on `onStart`
5. After editing any .tox, re-save the main .toe to update references

## Reusable components (`components/`)

Song-agnostic components live in `components/` as `.tox` files. The house pattern (same as the inline `flow_network` / `vignette_v1` baseCOMPs inside a song's `visuals_network`):

- a `baseCOMP` containing `in1` (inPOP/inTOP/inCHOP) + `out1` (outPOP/outTOP/outCHOP) + the internal chain
- **custom parameters** on the COMP (PascalCase names, e.g. `Flowlag`, `Resw`)
- internal nodes bound to them via expressions `parent().par.X` (never `parent.Project.par.X` — see below)

**`point_network_v1.tox`** — POP-only "point cloud → instanced boxes": `in1` (inPOP source) → `rnd_scale` → `rnd_rotation` → `noise` → `life_fade` → `copy_boxes` (template `box`) → `out1` (outPOP). 24 custom pars on the "Point Network" page (random scale/rotation, noise type/size/harmon/parsize/seed/period/spread/gain/amp/exp/speed, fade enable/in/out/scale/color, box scale/offset). `Fadeenable` toggles `life_fade.bypass` (`1 - parent().par.Fadeenable`), so the particle-age fade is optional and its `PartAge`/`PartLifeSpan` errors are suppressed when off. Unifies the two former inline variants (fade / no-fade).

⚠️ The original inline point networks in `visuals_network` are bound (`ParMode.BIND`) to a `Project` COMP that does **not** exist in `what_if` or `template` — every meaningful par (`box.scale`, all `noise.*`, `life_fade.vec0/1value`, the `copy_boxes` transform block) points at `parent.Project.par.*` (Scale, Seed, Period, Gain, Amp, Exp, T4d, Fadein, Fadeout, Ncy, Tx/Ty/Tz, Rx/Ry/Rz, Sx/Sy/Sz, Px/Py/Pz, …). Those binds are dangling; the component internalizes the controls instead.

## `.chan` files (performance recordings)

Recorded at 60 fps, space-separated floats, one row per frame. Comment lines start with `#`. Header lists channel names (e.g. `smsd_bass fmsd_bass sc_bass smsd_drums`). Stored under `data/<song>/<YYYYMMDD_ort>/`.

## `.chan` tools (external)

The `.chan` analysis tooling lives in its own repo — **`chan-tools`** (`~/Code/chan-tools`, sibling convention) — not in this project. This repo only *references* it; credentials-free, project-agnostic. Keep the separation: don't re-vendor the scripts here.

Dependencies: `numpy`, `matplotlib`.

- `python3 ~/Code/chan-tools/chan_stats.py <file.chan>` — per-channel stats. Flags: `--channel`, `--peak-distance`
- `python3 ~/Code/chan-tools/plot_chan.py <file.chan>` — plot channel data. Flags: `--channels`, `--output`, `--summary`, `--window`

The MCP server `chan_mcp.py` auto-registers `chan_list`, `chan_info`, `chan_analyze`, `chan_plot`. A global opencode skill `chan-tools` documents the workflow — load it before any `.chan` MCP work. It is wired via `opencode.json` (`{env:HOME}/Code/chan-tools/chan_mcp.py`) and `.claude/settings.json` (`$HOME/Code/chan-tools/chan_mcp.py`). It resolves the *data* project from `CHAN_PROJECT_ROOT`, else the process cwd (the MCP host spawns it in the project workspace). File paths: absolute → project root → `visuals/<path>`.

## Gotchas

- No build system, linters, tests, or typecheck — pure TouchDesigner
- `.toe` backups (`Backup/`, numbered root versions, `CrashAutoSave*`) are gitignored — only `digital_carbs_visuals.toe` is versioned
- `Backup/` entries and numbered root `.toe` files come from TD's Increment Filename on Save — not hand-made copies
- The repo lives on an exFAT volume; macOS creates `._*` AppleDouble files (gitignored) that can break `git gc` — delete them before running gc
- **Permission `ask` is useless in a subagent** — a backgrounded subagent has no client to prompt, so `ask` behaves like `allow` (verified: a subagent ran `nc`, `curl`, `whoami`, `cat ~/.config/opencode/*` under an `ask` rule). Read-only guarantees need `deny` plus an explicit allowlist, never `ask`
- **MCP tools are reachable only through Code Mode** — denying the `execute` action removes every MCP tool (a subagent loses `touchdesigner_*` entirely, even with the webserver up on 9981), while allowing it also grants outbound `fetch`. Not separable
- **Permission action names are `<server>_<tool>`** (underscore, not dot); `*` matches `/` too, so `**` is redundant; a shell pattern ending in `*` also matches the argument-less command (`git status *` covers `git status` and `git status --short`); both `agent/` and `agents/` directories are discovered (glob `{agent,agents}/**/*.md`)

## Session memory (MemPalace)

**Session start (read) — do this before answering, not on request:**

- Call `mempalace_status` once to load the palace overview + AAAK spec.
- Call `mempalace_diary_read` (`agent_name: opencode`, `last_n: 3-5`) for recent agent continuity.
- Before any statement about a past decision, a past session, or a file/commit history, verify with a **narrow** `mempalace_search` (small `limit`, relevant scope) — never guess. Widen only if recall is insufficient.

Shell access alone is not enough: the palace often holds the *why* behind repo state.

**Session end (write) — automatic:**

- Call `mempalace_checkpoint` with the session's key decisions/outcomes as `items` (wing `td_dc_visuals`, room `decisions`), plus a `diary` entry (agent `opencode`, AAAK format).
- Do this without being asked — it is the default behavior.
- Keep items verbatim and concise; never summarize away specifics like file paths, commit hashes, or exact numbers.
