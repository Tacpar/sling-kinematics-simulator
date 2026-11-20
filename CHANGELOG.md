# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-20

Baseline name for the program already on `main` at `d7c4fbf` (committed 2026-11-18). This section is not a git tag. Commits from before this file are not listed one by one.

### Added

- `sling_simulator.py`: a planar sling model (`SlingSimulator`) and a Tkinter window (`SlingSimulatorApp`). The mass stays on a fixed-length cord through windup, power stroke, and opening, then coasts in a straight line at constant velocity. The window reports peak hand speed, peak mass speed, mass speed at release, and hand distance, and it plots the series and exports CSV. There is no gravity term and no drag term in the source.
- `VERSION` at 0.1.0, this changelog, `AGENTS.md`, and a draft `ROADMAP.md`.
