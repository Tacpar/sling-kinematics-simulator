# Roadmap

> **DRAFT for discussion.** Nothing in this file is decided or scheduled, and no version is tagged. The grouping below is a proposal. The owner can drop, reorder, or replace any of it.

Inferred from `README.md` and `sling_simulator.py`. The README calls the project a sling kinematics simulator with an abstracted physics engine and a Tkinter GUI. The script simulates a point mass on a cord of fixed length, in the plane, through windup, a power stroke, and a short opening, then a straight coast at constant velocity. The window reports four speeds and distances, draws the paths, and can export CSV. The repository does not say who those numbers are for, or what agreement would count as enough.

## Current state

The repository is `sling_simulator.py`, a one-line `README.md`, `VERSION` (`0.1.0`), `CHANGELOG.md`, `AGENTS.md`, and this draft. There is no package, declared dependency file, test suite, linter, type checker, or CI. `python3 sling_simulator.py` opens a Tkinter window titled "Sling Kinematics Simulator" at a requested 1600×1200. Beyond the Python 3 standard library the script imports NumPy and Matplotlib. Tk has to be present; on Debian/Ubuntu that is often `python3-tk`. Importing the module sets the root logger to DEBUG, so a run prints phase lines to stderr. Nothing is git-tagged. The `[0.1.0]` changelog section names this program as the baseline and is not a release tag.

What a run does today is one deterministic planar throw:

- The form takes sling length and mass, initial hand position, windup speed and turns, three angles, hand acceleration, opening duration, time after release, and maximum reach. Units on the form are metres, kilograms, seconds, m/s², and degrees. Windup speed is labeled Hz and converted with `ω = 2π f`. `dt` is `0.0005` s and is not on the form.
- Form defaults: length 0.75 m, mass 0.1 kg, hand at the origin, 2 Hz, 1 turn, power stroke from 180° to a release angle of 0°, hand acceleration 100 m/s² at 90° (+y), opening 0.01 s, 0.5 s of coast, maximum reach 2 m.
- A run of those defaults through `run_simulation` (Python 3.12.3, NumPy 2.5.5) showed peak hand speed `15.95 m/s`, peak mass speed `35.63 m/s`, mass speed at release `35.32 m/s`, and hand distance `1.42 m`. The hand moved on a straight line along +y to about 1.424 m. Release is the row at t = 0.92 s. The mass then coasts to near (−1.86 m, 19.09 m) at the last stored sample, t = 1.4195 s. Peak mass speed is higher than the speed at release. NumPy is not pinned.
- Windup holds the hand still at constant `ω` until the turn count is met and the start angle is crossed. With the defaults that is 1 turn, then on to 180°, so the hand starts moving at t = 0.751 s (1.5 revolutions at 2 Hz).
- The power stroke uses a constant hand-acceleration vector. Angular acceleration is the perpendicular component of that vector divided by length, with the sign dropped, so spin does not decrease. The step that enters the phase still has `α = 0`.
- Opening holds `ω` and, after its first step, zeroes hand acceleration so the hand coasts. The first opening step still applies the power-stroke hand acceleration.
- After release, acceleration and tension are 0 and velocity is constant. The source has no gravity term and no drag term. The stop sample that ends the coast is not stored.
- Tension while the cord is taut is `m * L * ω²` only. Position is rebuilt from the fixed length, not integrated from that tension.
- The stored angle on a row is the angle from the start of the step. Position and angular velocity on that row are the updated state. The angle column lags the mass position by one step.
- The reach limit zeroes hand velocity and acceleration and can leave the hand outside the reach. It does not project the hand back onto the circle. A check with maximum reach 0.05 m stopped the hand at about 0.0512 m.
- The trajectory axes are requested at ±15 m with equal aspect. The default coast ends outside that box. On the check above, equal aspect kept x at ±15 m and shrank y.
- The four statistics use the first sample, the last sample, the max of each speed series, and the mass speed on the sample before the first post-release row. Hand distance is that end-to-end straight line, not a path length. Reset restores the form and the `N/A` strings and leaves the last series in memory, so Export can still write it.
- `dt`, length, and mass must be positive. Opening duration and maximum reach may be zero. The `ValueError` text says all five must be non-negative. Other inputs are not checked. A negative windup speed with a positive turn count runs until 50000 steps and raises `RuntimeError`.

Not in the tool: a test that locks those numbers, a declared dependency, a saved set of inputs, a `dt` field, gravity, drag, a cord force beyond `m L ω²`, a signed power-stroke acceleration, or a comparison against a measured throw.

## Proposed milestones

Version numbers follow `AGENTS.md`. The current script is the untagged **0.1.0** baseline named in `VERSION` and `CHANGELOG.md`. Later items are proposals. Each one that the owner skips is dropped, not renumbered in advance.

### v0.1.0 — name the model we have

Record today's throw as the baseline, without changing the numbers. `VERSION`, `CHANGELOG.md`, `AGENTS.md`, and this draft do that. The remaining act is a git tag `v0.1.0`, and only if the owner asks. See open question 10.

### v0.2.0 — lock today's numbers

No change to the phase machine, the tension formula, the Verlet steps, or the four default statistics.

- Tests in `tests/`, run with `pytest`, calling `SlingSimulator.run` rather than `mainloop`. One case uses the form defaults and `dt = 0.0005` s and checks the phase times, the four formatted statistics, the cord length, the coast, and the `ValueError` / `RuntimeError` oracles in `AGENTS.md`.
- Move the import-time `logging.basicConfig` and the font-manager logger line under `if __name__ == '__main__'`, so importing the module does not reconfigure the root logger. The GUI run may keep the debug lines. This does not change the reported speeds or the CSV columns.
- Extend `README.md` with the run command, the need for Tk, NumPy, and Matplotlib, the four phases, and a plain statement that the coast has zero acceleration.
- A dependency file is part of this version only if open question 11 says to add one. It would record NumPy and Matplotlib. Tk stays a system package such as `python3-tk`. If a known commit is enough, this version does not add a dependency file or a package.
- Done when those tests pass on a machine that has the libraries the suite needs, and a default run still shows `15.95 m/s`, `35.63 m/s`, `35.32 m/s`, and `1.42 m`.

### v0.3.0 — one instant per recorded row

Only if open question 12 says the angle column should match the mass position. If the lag stays, skip this version.

- Store, on each row, the angle of the `θ` used for that row's mass position.
- Do not change release speed, release velocity, or release position. Those do not read the stored angle.
- Update the v0.2 tests that locked the lagged column, in the same pull request, and say so in the changelog.
- Done when each pre-release row's angle matches `atan2` of that row's mass offset from the hand, and the four default statistics are unchanged.

### v0.4.0 — the form and the trajectory box

Only the parts the owner accepts from open questions 6 and 8. Either part can be dropped on its own.

- If `dt` should be editable: put it on the form, keep the default at `0.0005` s, and cover a second `dt` in the tests.
- If the axes should show the whole path: stop clipping the default coast, whose last point is near (−1.86 m, 19.09 m). If the ±15 m box stays, leave the limits as they are.
- Reset drops the stored series, clears the plots, and disables Export until the next successful run. The form defaults stay as they are.
- Done when a default run still shows the same four statistics, Export is disabled after Reset, and each accepted display change is what the window does.

### v0.5.0 — model terms the owner accepts

This version does not start until the owner answers open questions 2, 3, 4, 5, and 7. If the answers keep today's kinematic model, skip this version.

Candidates, none of them selected:

- Acceleration after release, if the coast should not be constant velocity. The source has no gravity constant today. The value and the direction would be the ones the owner names.
- A drag term, if the owner names the coefficient and the area it uses. Do not invent one.
- A signed power-stroke `α`, if the perpendicular component should be allowed to slow the spin. That changes the default release speed. The pull request states the old and new speed.
- Tension that includes the hand-acceleration component along the cord, if `m L ω²` is not the force to report. The default release speed can stay; the tension series will not.
- A windup count that means total revolutions before the hand moves, if "1 turn" should not wait out the remaining angle to 180°.

Done when only the accepted terms are in the model, each has a test and a changelog note that names units, and every term that was not accepted still matches the v0.2 oracles.

### v1.0.0 — the model the owner has accepted, checked

The first tag that means "this is the model," and only when the owner asks for it. There is no accuracy bar in the repository. Open question 9 decides what "checked" means. If the owner names no tolerance and no measurement, agreement between the tests and the accepted formulas is the bar, including the four default statistics.

- `README.md` states the phases and the terms that are in the model, and the terms that are absent, matching the owner's answers.
- Tests lock release time, release velocity, and release position for the default parameters, plus the four formatted statistics.
- A headless `SlingSimulator.run` remains what the window calls, and the test reads the same results the pane formats.
- A comparison against a measured throw is part of this version only if open question 9 says it is. Otherwise it is not a gate.
- Date the changelog section and tag `v1.0.0` when the owner asks. After that tag, a change to the meaning, sign, or unit of release speed, release velocity, release position, hand distance, or tension is a major version.

## Open questions for the owner

These are unanswered. The milestones above that depend on them wait.

1. What is this simulator for, and who uses the four statistics and the trajectory — a person reading the window, or a later calculation? The README and the script do not say.
2. Which of these limits are intentional, and which should a later version add: motion in the plane only, a rigid cord of fixed length, no gravity, no drag, and a coast at constant velocity after release?
3. Reported tension is `m * L * ω²` only. Should it stay that, or include the cord force from hand acceleration along the sling?
4. Power-stroke angular acceleration is `|a_hand| sin ψ / L` with `sin ψ` taken non-negative, so the spin does not decrease. Is that the intended power stroke? Changing the sign changes the default release speed.
5. Opening keeps the cord taut, zeroes hand acceleration after the transition step, and holds angular velocity for `opening_duration`. The form default is 0.01 s. Is that phase a keeper, and is 0.01 s the duration?
6. Are the form defaults a real sling or placeholders: 0.75 m, 0.1 kg, 2 Hz, 1 turn, power stroke from 180° to 0°, hand acceleration 100 m/s² at 90°, maximum reach 2 m, 0.5 s of coast, and `dt` of 0.0005 s? `dt` is not on the form. Should it become an input?
7. "Windup Turns" arms the power-stroke angle after that many revolutions. With the defaults the hand stays put until 180°, at t = 0.751 s, which is 1.5 revolutions at 2 Hz. Is that the meaning to keep?
8. The trajectory code requests ±15 m and equal aspect. The default run ends near (−1.86 m, 19.09 m), outside that box. Should the axes stay fixed, or show the whole path?
9. What agreement counts as done for release speed and release position, and against what reference? Nothing in the repo states a tolerance or a measured throw. If a measurement is in scope, what will be recorded, and is a match a gate on v1.0.0?
10. Should `v0.1.0` be tagged now that `VERSION` and `CHANGELOG.md` name the baseline, or should the first tag wait until tests lock the default-run numbers?
11. Is `python3 sling_simulator.py` from a known commit enough, or should the repo gain a dependency file and an installable package? NumPy and Matplotlib are imported and are not declared.
12. The angle stored on a row is the angle from the start of that step. The mass position on that row uses the updated angle. Should a later version make each row one instant? That changes the CSV and does not change the release speed.
13. Who must review a pull request that changes release speed, release velocity, release position, hand distance, or tension before it can merge?
14. The form is metres, kilograms, seconds, and degrees. The windup field is labeled Hz and implemented as revolutions per second. Should those units stay?
15. "Hand Distance Moved" is the straight-line distance between the first and last hand samples. On the default run that is the release position, shown as 1.42 m. Is that the statistic to keep?
