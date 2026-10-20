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
| `scripts/` | `dc_paths.py` (path module, live-linked to `/config/paths`), `check_paths.py` (repo guard), `td_path_scan.py` (live TD scan) |
| `visuals/BASE/` | `dc_visuals_base_v6.tox` — template for song visuals |
| `visuals/what_if/` | `dc_what_if_v1.tox` — completed song visual |
| `visuals/like_a_child/` | `like_a_child_v1.tox` — completed song visual |
| `visuals/MISC/` | `trippy1.tox`, `trippy2.tox` — utility visuals |
| `visuals/exploding_whale/`, `just_so_you_know/`, `mr_five/`, `hitc/` | WIP — no current .tox (old versions in their `old/`) |
| `data/` | `.chan` performance recordings + plots, organized `data/<song>/<YYYYMMDD_ort>/` |

Each module keeps superseded versions in its own `old/` subdirectory (e.g. `led/old/`, `visuals/BASE/old/`).

Start: `./td-dc.sh` — launches TouchDesigner with this project (macOS: `open -a`; WSL2: `cmd.exe` + `wslpath`, TD on the Windows host) and then opencode. The project path is derived from the script's own location; `DC_ABLETON_SET` optionally opens an Ableton set.

## Live project (running `.toe`)

Verified 2026-10-17. Top level of `digital_carbs_visuals.toe`: `songs` (containerCOMP — all song visuals, output switching and DMX), `dc_audio_analysis_v2`, `dc_midi_v1`, plus loose `audiodevin1`, `midiin1`, `speed1`, `switch1`, `null1`, `moviefileout1`, `perform`, `annotate1-3`, and `config` (path roots, see below). The `led/`, `post/`, `player/` `.tox` files exist on disk but are **not** loaded as top-level COMPs — LED/DMX output and song/state playback are integrated inside `songs` (POP-based DMX via `dmxoutPOP`, per-song `led_controls`/`LED`).

**Data flow**
- Audio: device + per-stem `audiodeviceinCHOP`s (SUM / DRUMS / DAN_IN / VOCALS / BASS_IN / WILLY_IN) → `dc_audio_analysis_v2/out1` = 18 channels (`smsd` / `fmsd` / `sc` × bass, drums, dan, willy, sum, voc) → `/songs` input 0.
- MIDI: `midiin1` → `speed1` → `switch1` (index 0) ← `dc_midi_v1/out1` (6 triggers: `willy_trig`, `snare_trig`, `kick_trig`, `dan_trig`, `ft_trig`, `tt_trig`) → `/songs` input 1.

**Song switching** — `songs/registry` (tableDAT, one song name per row) is the single source of truth. `songs/01_start` (`onStart`) auto-wires every registry row to `pop_switch`/`top_switch` (input order = row order) and feeds `audio_analysis_in` + `midi_in` into each song. The active song is `songs/constant1['SongNumber']` (0-based) → `lag1` → `lag1_export` (CHOP Export DAT) → exported to `pop_switch.index` **and** `top_switch.index`.

**Outputs**
- Video: `top_switch` → `top_switch_out` → `top_out_select` (select-by-path) → `top_out` (outTOP) → `perform` window (`winop = /songs/top_out`). Preview/record tap: `songs/preview_out` → `/null1` → `/moviefileout1`.
- DMX: `pop_switch` → `pop_switch_out` → `dmx_out_select` → `dmx_out` (`dmxoutPOP`, Enttec USB Pro, 44 Hz). **`dmx_out.active` is deliberately off** — enable it for a physical rig.
- `/perform` (windowCOMP): `size=automatic` (follows the 1280×720 TOP), `borders=off`, `alwaysontop=on`, `cursorvisible=nocursor`, `blocksleep=on`, `single=singledisplay`.

**Song registry (8, in switch order)**: `like_a_child`, `exploding_whale`, `cocoon`, `just_so_you_know`, `mr_five`, `win_some_lose_some`, `what_if`, `head_in_the_clouds`. Note: `cocoon`, `win_some_lose_some` and `head_in_the_clouds` have **no matching `visuals/` dir or `.tox`** — they live only inside the `.toe` (`head_in_the_clouds`'s WIP dir is `visuals/hitc/`).

## Paths in the TD project (OS-agnostic)

Nothing in the `.toe` hardcodes a media or TD-install path. Verified live 2026-10-20 with `scripts/td_path_scan.py`: **`hardcoded_files=0`, 52 expression-resolved, 47 OSC/node strings (ok), 1922 intact binds, 0 broken binds** (see *Parameter control bus*).

**Mechanism** — one baseCOMP `/config` (custom pars `Mediaroot`, `Lutroot`, `Vst3root`, `Neutonevst`, `Diagnostics`) plus `/config/paths`, a Text DAT with **Sync File → `scripts/dc_paths.py`** (relative to the `.toe`), loaded as a module and used as `mod('/config/paths')`.

- Media root resolution: `DC_MEDIA_ROOT` env var → `/Volumes/Visuals` (macOS) → `D:/` (Windows); the first candidate containing `<root>/Library/Recordings` wins. One root covers `Library/Recordings`, `Library/Videos`, `Library/LUTs` and `Live/`.
- Optional overrides: `DC_LUT_ROOT`, `DC_VST3_ROOT`, `DC_TD_SAMPLES`, `DC_ABLETON_SET`.
- Helpers: `media()`, `lut()`, `samples()`, `install()`, `vst3()`, `ableton_set()`, `ocio_config()`, `report()`, `check()` — e.g. `mod('/config/paths').samples('Map/Banana.tif')`.
- Because the DAT is sync-linked, editing `scripts/dc_paths.py` changes TD behaviour immediately; the `.py` is the source of truth, not the DAT.

**Rules for new nodes**
- Never type an absolute path into a par. Use an expression: `mod('/config/paths').<helper>('relative/part')`.
- `os` is **not** available in parameter expressions — put any logic in `scripts/dc_paths.py` and call it via `mod()`.
- Song COMPs keep `par.File` / `par.Filesource` as **relative** constants (`Library/Recordings/Müll/müll_karo_3.mov`); internal nodes read them via `parent().par.File` / `parent().par.Filesource`. Never re-type the path in a child node.
- `externaltox` of a loaded component is relative to the `.toe` (e.g. `./audio_analysis/dc_audio_analysis_v2.tox`).
- macOS stores paths NFD, Windows NFC — `dc_paths` normalizes to NFC, so write names as you see them.
- Supposed to stay constant: OSC address patterns (`/listener/song/...`), scope patterns with `*`, node paths (`/project1/`), `/config`'s own root candidates, and `mcp_webserver_base` (never touch it).

**Checks** (both read-only)
- Repo text: `python3 scripts/check_paths.py` — absolute paths in versioned code/config fail (exit 1), in `.md` they only warn. Intentional exceptions get the per-line marker `os-path-ok`.
- Live project: `exec(open(project.folder + '/scripts/td_path_scan.py').read())` via the TD MCP / Textport → writes `Backup/td_path_scan_report.txt`. Expected: `hardcoded_files=0`.

## TouchDesigner MCP (live session)

The `touchdesigner` MCP drives the running TD instance (WebServer DAT, port 9981). Generic harness lives in the global opencode config: skill `touchdesigner-mcp`, agent + command `td` — **load the skill before any TD MCP work** (`/td <task>`). Full tool/workflow/persistence rules are in the skill; project-specifics:

⚠️ **Two workstations, one repo layout.** Everything *inside* the repo is identical on both machines — only the parent directories differ, and they matter only for shell/git/MCP work:

| Placeholder | macOS | Windows + WSL2 |
|---|---|---|
| `<TD_PROJECT>` | `/Volumes/Visuals/TouchDesigner/td-dc-visuals` | `/mnt/c/Code/td-dc-visuals` |
| `<TD_MCP_REPO>` | `/Volumes/Visuals/touchdesigner-mcp` | `/mnt/c/Code/touchdesigner-mcp` |

These are **shell-side** paths. Inside TouchDesigner nothing is machine-specific (see *Paths in the TD project*), and `td-dc.sh` derives the project path from its own location — so neither code nor nodes should ever contain one of these. `scripts/check_paths.py` enforces that for versioned files.

On Windows, TouchDesigner runs on the **Windows host**, not in WSL — opencode (in WSL2) reaches its WebServer DAT on port 9981 via WSL2 **mirrored networking** (`/etc/wsl.conf` → `[wsl2] networkingMode=mirrored`), so `127.0.0.1:9981` is correct. The host/port must be passed to the MCP server as `--host`/`--port` **arguments**; an `environment` block is silently discarded by the CLI.

- **Right project check**: the top level must show `songs`, `dc_audio_analysis_v2`, `dc_midi_v1` (plus `config`, `perform`, `moviefileout1`, `audiodevin1`, `midiin1`, …). If a scratch/default project is open, ask the user to open `digital_carbs_visuals.toe` first. Note: in this project the top level is `/` (not `/project1`).
- **Harness code**: the TD-side MCP server that TD actually imports is the git clone of the fork — `<TD_MCP_REPO>/td` (on macOS `~/Code/touchdesigner-mcp/td`) — so the source you edit *is* the running server. `/mcp_webserver_base.par.externaltox` points directly at `<clone>/td/mcp_webserver_base.tox` and `import_modules.py` derives `<dirname>/modules` (i.e. `td/modules`) from that par, so nothing is hardcoded. Edit only the loaded copy, never a duplicate: the old separate extract copy (`~/TouchDesigner/touchdesigner-mcp`, a symlink since 2026-10-18) and `touchdesigner-mcp.extract-v2.1.0` were removed. Runtime-required artifacts are gitignored: `td/modules/td_server/openapi_server/openapi/openapi.yaml` and `**/generated_handlers.py` (`node td/genHandlers.js`). Module edits do **not** take effect from a webserver `restart` pulse; you must re-import Python (clear `sys.modules` for `mcp`/`utils` and re-exec `/mcp_webserver_base/mcp_webserver_script`, or restart TouchDesigner). (An unrelated copy of just the `.tox` component lives in the `touchdesigner-wiki-mcp` project.)
- **Persistence**: save components as `.tox` under their module dir; re-save the main `.toe` with an explicit path — `project.save(project.folder + '/digital_carbs_visuals.toe')` (OS-neutral, no machine path needed). `project.save()` without a path writes numbered auto-versions (gitignored).
- **Namespaces**: `touchdesigner_*` (live), `touchdesigner-wiki_*` (docs), `chan-tools_*` (`.chan` data) — never mix.
- **Skill source (versioned)**: the skill text is authored in the `konraddiesch/touchdesigner-mcp` fork, branch `local/opencode-harness`, at `plugin/touchdesigner/skills/touchdesigner-mcp/SKILL.md` (clone: `~/Code/touchdesigner-mcp`). `~/.config/opencode/skills/touchdesigner-mcp/SKILL.md` is a **symlink** to it — never edit the global copy. After editing, `npm run plugin:sync` regenerates `plugins/touchdesigner/**` (CI's `plugin:check` compares byte-for-byte, so commit both trees). The same fork also versions the opencode-only harness — `opencode/agents/td.md` and `opencode/commands/td.md` — symlinked to `~/.config/opencode/agent/td.md` and `~/.config/opencode/command/td.md`; they are **not** packaged by `plugin:sync` (opencode frontmatter), and opencode only re-reads agent/command files on restart.

## Review agents (opencode)

Two read-only reviewers, both `mode: all` (Tab-selectable **and** launchable as a subagent), model `openrouter/z-ai/glm-5.3-flash`:

- **`reviewer`** — global, `~/.config/opencode/agents/reviewer.md`. Generic code/diff reviewer. Denies everything, then re-opens `read`/`glob`/`grep` and six read-only git commands (`git diff|log|status|show|blame|ls-files`). No MCP, no network — fully sealed.
- **`td-reviewer`** — this repo, `.opencode/agents/td-reviewer.md`. Only the delta that `AGENTS.md` does not already say (binaries, no toolchain, empty code surface) plus live-network verification through the read-only TD tools (`touchdesigner_get_*`, `touchdesigner_describe_td_tools`).

Both never edit. `AGENTS.md` reaches subagents automatically, so `td-reviewer` deliberately does **not** restate these conventions — if you change a convention here, do not copy it into the agent prompt.

## Creating a new song visual

1. Copy the live BASE instance (`songs/template`, sourced from `visuals/BASE/dc_visuals_base_v6.tox`) into a new dir under `visuals/`
2. Name `<artist>_<song>_v1.tox` (e.g. `dc_what_if_v1.tox`)
3. Load it into the `songs` COMP in `digital_carbs_visuals.toe`
4. Add the COMP's name as a row in `songs/registry` — row order defines the `SongNumber` index and `songs/01_start` wires it to `pop_switch`/`top_switch` on `onStart`
5. Keep the song's `File` / `Filesource` pars **relative** (`Library/Recordings/<artist>/<clip>.mov`) — see *Paths in the TD project*; internal nodes read them, never re-type the path
6. After editing any .tox, re-save the main .toe to update references

## Parameter control bus (parent shortcuts)

The song visuals are driven by **Parent Shortcuts** (`par.parentshortcut`), not by a global control COMP. `visuals_network` in all 8 songs (and `HITC_v1`) sets it to `Project`; every `annotate*` COMP sets `Annotate`. Inside a COMP, `parent.<Shortcut>` resolves to that COMP itself — independent of its name, path, or which `.tox` it was loaded from.

- `visuals_network` is the control surface: 66 custom pars (`Type`, `Seed`, `Period`, `Gain`, `Tx…Pz`, `Sx…Sz`, `Scale`, `Filesource`, …). 325 child pars mirror them with `ParMode.BIND` — verified 2026-10-20: 325/325 masters resolve.
- This is why there is **no** global `Project` COMP and none is missing: each song's network is "Project" for its own children, so the same network copy works in every song.
- ⚠️ **Never rename or clear a shortcut** (`par.parentshortcut`): it invalidates every bind of that COMP at once (325 for `Project`, 700+ for `Annotate`). Rename the COMP, not the shortcut.
- To inspect a bind, read `par.bindMaster` (the real wiring). `par.bindExpr` is only the label from creation time — `parent.Project.par.X` is correct and does **not** point at a node called `Project`. Never classify binds by that text.

## Reusable components (`components/`)

Song-agnostic components live in `components/` as `.tox` files. The house pattern (same as the inline `flow_network` / `vignette_v1` baseCOMPs inside a song's `visuals_network`):

- a `baseCOMP` containing `in1` (inPOP/inTOP/inCHOP) + `out1` (outPOP/outTOP/outCHOP) + the internal chain
- **custom parameters** on the COMP (PascalCase names, e.g. `Flowlag`, `Resw`)
- internal nodes bound to them via expressions `parent().par.X` (never `parent.Project.par.X` — see below)

**`point_network_v1.tox`** — POP-only "point cloud → instanced boxes": `in1` (inPOP source) → `rnd_scale` → `rnd_rotation` → `noise` → `life_fade` → `copy_boxes` (template `box`) → `out1` (outPOP). 24 custom pars on the "Point Network" page (random scale/rotation, noise type/size/harmon/parsize/seed/period/spread/gain/amp/exp/speed, fade enable/in/out/scale/color, box scale/offset). `Fadeenable` toggles `life_fade.bypass` (`1 - parent().par.Fadeenable`), so the particle-age fade is optional and its `PartAge`/`PartLifeSpan` errors are suppressed when off. Unifies the two former inline variants (fade / no-fade).

⚠️ The original inline point networks in `visuals_network` are bound (`ParMode.BIND`) to `parent.Project.par.*` — `Project` is the **parent shortcut** of the enclosing `visuals_network`, not a missing node (see *Parameter control bus*). Every meaningful par (`box.scale`, all `noise.*`, `life_fade.vec0/1value`, the `copy_boxes` transform block) mirrors the control surface of its own song. Those binds are intact; standalone components like `point_network_v1` carry their own custom pars instead of relying on an enclosing shortcut.

## `.chan` files (performance recordings)

Recorded at 60 fps, space-separated floats, one row per frame. Comment lines start with `#`. Header lists channel names (e.g. `smsd_bass fmsd_bass sc_bass smsd_drums`). Stored under `data/<song>/<YYYYMMDD_ort>/`.

## `.chan` tools (external)

The `.chan` analysis tooling lives in its own repo — **`chan-tools`** (sibling convention: `<workspace>/../chan-tools`, i.e. `~/Code/chan-tools` on macOS, `/mnt/c/Code/chan-tools` in WSL) — not in this project. This repo only *references* it; credentials-free, project-agnostic. Keep the separation: don't re-vendor the scripts here.

Both MCP harnesses resolve the server through the same fallback chain — `$HOME/Code/chan-tools` first, then `<workspace>/../chan-tools` — so nothing is hardcoded and the helper scripts always sit next to the server. The server resolves the *data* root from `CHAN_PROJECT_ROOT`, else the process cwd (the MCP host spawns it in the project workspace).

Dependencies: `numpy`, `matplotlib` (`chan-tools/requirements.txt`). The server
is stdlib-only and falls back to `uv run --with numpy --with matplotlib` when
the interpreter lacks them.

- `python3 ~/Code/chan-tools/chan_stats.py <file.chan>` — per-channel stats. Flags: `--channel`, `--peak-distance`
- `python3 ~/Code/chan-tools/plot_chan.py <file.chan>` — plot channel data. Flags: `--channels`, `--output`, `--summary`, `--window`

The MCP server `chan_mcp.py` auto-registers `chan_list`, `chan_info`,
`chan_analyze`, `chan_plot`. A global opencode skill `chan-tools` documents the
workflow — load it before any `.chan` MCP work. Wired in both harnesses via the
same `bash -lc` fallback loop: `opencode.json` (project entry, which overrides
the global `~/.config/opencode/opencode.jsonc`) and `.claude/settings.json`.
Path resolution: absolute → project root → `visuals/<path>` → bare filename
anywhere in the project.

## Gotchas

- No build system, linters, tests, or typecheck — pure TouchDesigner
- `.toe` backups (`Backup/`, numbered root versions, `CrashAutoSave*`) are gitignored — only `digital_carbs_visuals.toe` is versioned
- `Backup/` entries and numbered root `.toe` files come from TD's Increment Filename on Save — not hand-made copies
- The repo lives on an exFAT volume; macOS creates `._*` AppleDouble files (gitignored) that can break `git gc` — delete them before running gc
- Re-run `scripts/td_path_scan.py` after touching nodes that load files (repo-side equivalent: `scripts/check_paths.py`); "0 hardcoded" was verified 2026-10-20, not a permanent property
- Don't confuse the two "Project"s: `parent.Project` is the **parent shortcut** of the enclosing `visuals_network` (see *Parameter control bus*), while `op('/config')` is the path-root COMP. Neither indicates a missing node. The old file paths froze as *constants typed per machine* — not because of these binds
- To check binds, use `par.bindMaster`, not `par.bindExpr`: the label `parent.Project.par.*` is correct and resolves inside the COMP (verified 325/325), even though `op('…/Project')` legitimately returns `None`. Re-assigning `par.expr` on such a par converts BIND → EXPRESSION and can break it
- `/dc_midi_v1/tdAbletonPackage/tdAbleton` has an `externaltox` whose file does not exist in the repo. The expression resolves relative to the `.toe`, so it is *portable* — the file is simply absent (the TDAbleton packages live embedded in `/dc_midi_v1/tdAbletonPackage`). Leave the ref alone
- 6 `audiovst` nodes in `dc_audio_analysis_v2` have an empty `file` par: the `neutone` VST3 is installed on neither machine → 6 persistent red errors, deliberate
- 1 stale par: `/songs/just_so_you_know/visuals_network/ocio1` `filesource` is in EXPRESSION mode with the correct expression but a stale empty value (the only node of 9). Re-assigning the expression evaluates it — but that activates `The One LUT` for that song, i.e. it changes the look; documented, not fixed
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
