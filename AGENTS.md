# Agent guide

This file is the working agreement for any coding agent in this repository. Follow it on every change.

## Index

The sections below are in reading order. This list is the order to jump in.

| Section | What an agent finds there |
| --- | --- |
| [Run](#run) | The command that opens the window, and the libraries it needs. There is no build. |
| [Branches, commits, and pull requests](#branches-commits-and-pull-requests) | Never commit, push, force-push, or merge to `main`. Branch prefixes, commit form, and what a pull request contains. |
| [Where the code lives](#where-the-code-lives) | The phase machine, the integrator, the units, and the numbers the window reports. |
| [Testing](#testing) | No tests exist. The convention to use once they do, and the oracles already in the model. |
| [Purpose](#purpose) | What the program calculates, and which numbers a change has to call out. |
| [Repository](#repository) | Paths, and what is not in the tree. |
| [Versioning](#versioning) | `VERSION`, the changelog, semver, and when a tag is allowed. |
| [Coding standards](#coding-standards) | Style and model details taken from `sling_simulator.py`. |
| [Scope](#scope) | What a small fix does not restructure. |

> **Never commit, push, force-push, or merge to `main`.** This repository's default branch is `main`. The same rule applies if the default branch is named something else, including `master`. All work happens on a branch and lands through a pull request that a human reviews and merges. Open the pull request and stop. Do not merge it, and do not push the result onto `main`.

## Purpose

`README.md` calls this a sling kinematics simulator with an abstracted physics engine and a Tkinter GUI. The program simulates a planar sling: a point mass on a cord of fixed length, moved through windup, a power stroke, a short opening, and a straight coast after release. It does not say who the numbers are for.

The window reports four statistics, a trajectory, time-series plots, and an optional CSV. The four statistics are:

- peak hand speed
- peak mass speed
- mass speed at release
- hand distance moved (the straight-line distance between the first and last hand samples)

Together with the mass position and velocity at release, and the tension series, those are the reported results. A change that moves them is a change to the throw the tool reports. Call that out in the pull request and in the changelog, with the old and new values in units a person can check (metres, seconds, metres per second, newtons).

The model is open-loop and deterministic. Post-release acceleration is zero. There is no gravity term and no drag term in the source. Do not describe that coast as a ballistic flight. `ROADMAP.md` is a draft for the owner. It is not a task list.

## Repository

| Path | Role |
| --- | --- |
| `sling_simulator.py` | The whole program |
| `README.md` | One-line description |
| `VERSION` | The version, one line: `0.1.0` |
| `CHANGELOG.md` | Keep a Changelog record |
| `AGENTS.md` | This guide |
| `ROADMAP.md` | Draft roadmap for discussion |

There is no package, `pyproject.toml`, dependency file, test suite, linter, type checker, CI workflow, or `__version__`. Do not add a version constant in `sling_simulator.py`. The version lives in `VERSION`.

Dependencies are NumPy, Matplotlib, and the Python 3 standard library (`tkinter`, `math`, `csv`, `logging`, `dataclasses`). `SlingSimulator.run` uses NumPy. The window uses Matplotlib (`FigureCanvasTkAgg`). Importing the module imports `tkinter` and Matplotlib, and it calls `logging.basicConfig`. On Debian/Ubuntu, Tk is often the `python3-tk` package. None of this is declared in a requirements file.

## Run

There is no build and no install step.

From the repository root, with Python 3, NumPy, Matplotlib, and Tk available:

```bash
python3 sling_simulator.py
```

That opens the Tk window. There is no command-line interface. The `if __name__ == '__main__'` block constructs `SlingSimulatorApp` and starts `mainloop`. A run writes phase-transition lines to stderr, because import sets the root logger to DEBUG.

The form's defaults were run through `SlingSimulatorApp.run_simulation` on Python 3.12.3 with NumPy 2.5.5. The pane showed `15.95 m/s`, `35.63 m/s`, `35.32 m/s`, and `1.42 m`. The repo does not pin those library versions.

## Where the code lives

All of it is in `sling_simulator.py`, top to bottom.

1. **Logging, at import.** The Matplotlib font-manager logger is set to INFO, then `logging.basicConfig(level=logging.DEBUG, format='%(message)s')` configures the root logger. `SlingSimulator.run` logs windup, power stroke, opening, release, the reach limit, and the stop time.
2. **Inputs and outputs.** `SimulationParameters` is the input dataclass. Lengths are metres, mass is kilograms, times are seconds, `hand_accel_rate` is m/s², and the three angles are degrees. `windup_speed_hz` is stored as given and converted with `ω = 2π f`, so the value labeled Hz is revolutions per second. `SimulationData` holds parallel lists. `ang_speeds` and `ang_accels` are rad/s and rad/s². The plots and the CSV divide both by `2π` and label them rps and rps/s.
3. **Integrator.** `SlingSimulator`. `max_sim_steps` is 50000. `float_threshold` is `1e-12`. `run` is the model. It does not read the widgets. `SimulationData.hand_speeds` is filled there. The dict the plots and the CSV use does not copy it. Peak hand speed is only the statistic.
4. **Window.** `SlingSimulatorApp`. The title is "Sling Kinematics Simulator" and the requested geometry is 1600×1200. `run_simulation` builds `SimulationParameters` from the form, calls `run`, and formats the four statistics to two decimal places. `plot_data` draws the series. `export_to_csv` writes the header in that method. `reset_inputs` restores the form defaults and the `N/A` strings. It does not clear `simulation_data` or the plots.

`dt` defaults to `0.0005` s. Reset sets it back. No widget displays it.

Phases, in order, for a throw that reaches release:

- **Windup.** The hand stays at the initial position. Angular acceleration is 0, so `ω` stays at `2π` times the windup speed. The windup count is unwrapped `θ / 2π`, not the wrapped angle. Once that count reaches `windup_turns`, the next crossing of `power_stroke_begin_angle_deg` starts the power stroke. With the form defaults (1 turn, then 180°) that crossing is at t = 0.751 s.
- **Power stroke.** Hand acceleration is constant: magnitude `hand_accel_rate`, direction `hand_accel_direction_deg` measured from +x toward +y. Angular acceleration is computed only on a step that begins already in this phase. The step that enters the phase still has `α = 0` and does apply the new hand acceleration. `α = (|a_hand| sin ψ) / L`, where `cos ψ` is the dot product of the hand-acceleration direction with the unit vector from the mass toward the hand, and `sin ψ` is the non-negative square root. If `|cos ψ| > 1`, the code uses `sin ψ = 0`. If the rate is 0, `α` is 0. `α` is never negative, so the spin does not decrease in this phase. Values with `abs(α) < 1e-12` are set to 0. Crossing `release_angle_deg` starts the opening.
- **Opening.** `ω` is set back to the value saved at the transition and held. Later opening steps set hand acceleration to 0, so the hand coasts. The transition step itself still uses the power-stroke hand acceleration. After `opening_duration` seconds the phase becomes post-release. The default duration is 0.01 s, and the default release row is at t = 0.92 s.
- **Post-release.** The hand update stops, so the hand stays at the release position. Mass acceleration and tension are 0. Mass position advances by `v * dt` with `v` unchanged. The loop stops when `t >= t_release + sim_time_after_release`, without storing that stop sample. On the default run the last stored time is 1.4195 s and the debug line prints 1.42 s.

Until release, the mass position is rebuilt from the constraint, not integrated from tension: hand position plus `L (cos θ, sin θ)`, using `θ` after the update. Tension is `m * L * ω²` only. It does not include hand acceleration along the cord. Time uses Kahan summation. The first stored time is `dt`, not 0. The stored angle is the wrapped angle from the start of the step, in degrees. On the same row, position and `ang_speeds` use the updated state, so the angle column lags the mass position by one step.

Hand position and velocity, and the sling angle, each use a velocity-Verlet step with acceleration held over the step. The hand step runs only while a power stroke has started and release has not. The angle step runs until release. `hand_pos_x` is snapped back to the initial x when the difference is under `float_threshold`, and `hand_vel_x` is snapped to 0 the same way. There is no matching snap on y. If the hand's distance from the initial position reaches `maximum_reach` during the power stroke or the opening, velocity, acceleration, and `α` are set to 0 and the power-stroke `α` formula is not applied again. The hand is not pulled back inside the reach.

`_is_angle_newly_at_or_past` compares angles wrapped to `[0, 2π)`. If the wrapped angle moves by less than `1e-9` rad, the step is a hit only when the current angle is within `1e-9` of the target. If the wrapped angle increases, the step is a hit when `prev < target <= curr`, or when `prev` is already within `1e-9` of the target. If the wrapped angle decreases, the code treats that as a wrap through 0. A negative windup speed is not rejected, and it takes that decrease path. With a positive turn count that case runs to `max_sim_steps` and raises `RuntimeError`.

Validation at the start of `run`:

```python
if dt <= 0 or L <= 0 or m <= 0 or opening_duration < 0 or maximum_reach < 0:
    raise ValueError("Time step, sling length, mass, opening duration, and maximum reach must be non-negative.")
```

`dt`, length, and mass have to be positive. Opening duration and maximum reach may be zero. The message says non-negative for all five. Windup speed, windup turns, the angles, hand acceleration, post-release duration, and the initial hand position are not checked. Reaching 50000 steps raises `RuntimeError("Maximum simulation steps reached.")` and returns nothing.

The window turns `ValueError` into an error dialog, `RuntimeError` into a warning titled "Simulation Limit", and `tk.TclError` into "Input Error". Export is disabled until a run returns. The trajectory axes are set to ±15 m with equal aspect. On the form defaults the mass ends near (−1.86 m, 19.09 m), outside that box. Matplotlib may then shrink the y axis to keep the aspect; the source still requests ±15 m.

New model math belongs on `SlingSimulator.run`, or on a function it calls, so a test can run it without `mainloop`.

## Versioning

The version is the single line in `VERSION` at the repository root: `0.1.0`. There is no `__version__` in `sling_simulator.py`. Do not add one. Do not keep a second copy of the number in the program.

`CHANGELOG.md` is in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. `## [Unreleased]` is present and empty. `## [0.1.0] - 2026-11-20` describes the current program as the baseline. It is not a git tag. Do not invent entries for commits that predate the file.

Use [Semantic Versioning](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH`. Pre-release identifiers are fine, for example `0.2.0-rc.1`. A release tag, when the owner asks for one, uses a leading `v` and the same text: `v0.1.0`, `v0.2.0-rc.1`. Do not create a tag unless the owner asked for that release.

To bump the version, in the same pull request: set the line in `VERSION`, and write the behavior change under `## [Unreleased]`. A release the owner asked for uses a `release/vX.Y.Z` branch, sets `VERSION` to that number, and moves the Unreleased notes under `## [X.Y.Z] - YYYY-MM-DD`. The tag is still created only when the owner asks. After a tag exists, the changelog compare links can point at it. Do not link `v0.1.0` while that tag is absent.

Below 1.0.0 the reported results may still change in a minor version. From 1.0.0 on, a change to the meaning, sign, or unit of release speed, release velocity, release position, hand distance, or tension is a major bump. A patch preserves those outputs and the numerical method. Name the bump in the pull request.

## Branches, commits, and pull requests

**Never commit, push, force-push, or merge to `main`.** This repository's default branch is `main`. The same rule applies if the default branch is named something else, including `master`. All work happens on a branch and lands through a pull request that a human reviews and merges. Open the pull request and stop. Do not merge it, and do not push the result onto `main`.

Branch names, lowercase and hyphenated:

- `feature/<short-desc>` — new behavior
- `fix/<short-desc>` — a correction to existing behavior
- `docs/<short-desc>` — documentation only
- `release/vX.Y.Z` — version bump and changelog date for a release the owner asked for

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional-scope>): <imperative summary>

<why, when the subject is not enough>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`. The subject is lowercase imperative, with no trailing period. Example: `fix(release): hold opening speed for the full opening interval`. Commits from before this guide do not use this form. New commits do.

Pull request expectations:

- One concern. Leave unrelated refactors out.
- Say what changed and why. If a reported result moved, give the old and new meaning in units a person can check.
- Add or update tests for any behavior change. A docs-only change needs no test.
- Tests, and any lint or type check the repo actually configures, pass before you request review. None are configured today. Report only commands you ran. Do not add a linter, formatter, or CI workflow inside an unrelated change.
- A human reviews and merges.

## Coding standards

Match `sling_simulator.py`.

- NumPy and Matplotlib are already imported. Do not add another third-party dependency unless the owner has agreed. Record an agreed dependency in a file an install can use, and in the changelog. Do not add that file inside an unrelated change.
- `snake_case` for functions and variables, `PascalCase` for classes. The integrator already uses short physics names (`L`, `m`, `theta`, `omega`, `alpha`); keep those in that function. A leading underscore marks a helper, as on `_is_angle_newly_at_or_past`.
- `run` is annotated, and the dataclasses are not given richer field types. The file does not import `typing`. Annotate new public functions with builtin generics (`list[float]`). Do not add a `typing` import to match a style this file does not use.
- There are no docstrings. A new physics function whose units or assumptions are not obvious gets a short docstring that names the units. Do not reflow the file to document existing functions in an unrelated change.
- No formatter is configured. Keep the section comments. Do not reflow the file.
- Illegal `dt`, length, mass, opening duration, and maximum reach raise the `ValueError` quoted above. The step cap raises the `RuntimeError` quoted above. Keep that split: the model raises, the window displays. Do not widen validation (negative windup speed, angles, post-release duration) as a drive-by. If you change the predicate, change the message in the same pull request.
- `run` is the model behind the reported results. Keep the phase order, the velocity-Verlet steps, Kahan time, `dt` default `0.0005`, `max_sim_steps`, `float_threshold`, the x-only snap, `tension = m * L * omega**2`, and the non-negative `α`, unless changing one of them is the point of the pull request.
- The step that enters the power stroke leaves `α` at 0. The step that enters the opening still applies power-stroke hand acceleration. Do not "fix" either as a drive-by.
- If `max_sim_steps` is hit, `run` raises and returns no series. Do not catch that and present a partial series as a finished throw.
- Post-release acceleration is 0. Do not label that path as a ballistic trajectory.
- Plot titles, axis labels, and the CSV header are the units a person sees. In-memory angular speed stays rad/s; the plot and the CSV use rps. If a unit changes, change the label or the header in the same pull request.
- The four statistics are formatted to two decimal places. Hand distance is the first sample to the last, not a path integral.
- The module calls `logging.basicConfig` at import. Do not add another `basicConfig`.

## Testing

There is no test suite, no `pytest` configuration, and no CI. There is no test command to run today.

Convention once tests exist (they do not yet): put them in `tests/`, use `pytest`, and run this before requesting review:

```bash
python3 -m pytest
```

`pytest` is a recommendation, not a current dependency. Test `SlingSimulator.run`, not `mainloop`. Importing `sling_simulator.py` requires Tk, NumPy, and Matplotlib, and it calls `logging.basicConfig`. If you split the model out, put the tests on the module that does not import `tkinter`.

The form's `dt` is `0.0005` s. A test that only checks one scenario may use that default. A test that sweeps many cases should pass a coarser `dt` and keep one tight-step case for the number it is locking. Library versions are not pinned. Lock the formatted statistics, or a tight tolerance, rather than a bit-exact dump.

Oracles already in the code, for when you add tests. The default-scenario figures below were produced with Python 3.12.3 and NumPy 2.5.5, and the four strings were read back from `run_simulation`:

- Form defaults: windup criteria in the debug log at t = 0.501 s, power stroke at t = 0.751 s, opening at t = 0.910 s, release row at t = 0.92 s, 2839 stored samples, last stored time 1.4195 s. The pane shows `15.95 m/s`, `35.63 m/s`, `35.32 m/s`, and `1.42 m`. Peak mass speed is higher than the release speed.
- Windup rows: hand at the initial position, hand velocity 0, `α = 0`, `ω = 2π` times the windup speed, tension `m * L * ω²`, mass radius `L`.
- Before the first post-release row, the mass is `L` from the hand.
- Power-stroke `α`, after the transition row, matches `|a_hand| * sin ψ / L` with `sin ψ >= 0`. The transition row's `α` is 0.
- Opening rows hold `ω` at the saved value and have `α = 0`.
- Post-release: tension 0, acceleration 0, velocity constant, and each position step equal to `v * dt`.
- On row `i > 0` before release, the stored angle matches the previous row's mass-position angle, not this row's.
- `dt <= 0`, length `<= 0`, mass `<= 0`, `opening_duration < 0`, and `maximum_reach < 0` raise `ValueError` with the message quoted above. Zero opening duration and zero maximum reach do not.
- A negative windup speed with a positive turn count raises `RuntimeError("Maximum simulation steps reached.")`.
- The first stored time is `dt`.

Recommended later, only if the owner adds them to the repo: [Ruff](https://docs.astral.sh/ruff/) for lint and format, [mypy](https://mypy-lang.org/) for types. They are not configured. Do not add them on the side.

## Scope

A fix of the reported results does not rename `sling_simulator.py`, invent a package, or restructure the file. That work waits for a roadmap item the owner has accepted. Read `ROADMAP.md` before proposing one. It is a draft.
