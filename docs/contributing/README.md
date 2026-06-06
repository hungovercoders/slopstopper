---
title: Contributing
description: Contributor workflow and expectations for the template-netlify project.
status: maintained
date: 2026-03-02
---

# Contributing

This document defines the default way to contribute to this project.

## Prerequisites

- Install Task (Taskfile runner): [taskfile.dev/installation](https://taskfile.dev/installation/)
- Verify installation: `task --version`

## Taskfile-Driven Basics

Use `Taskfile.yml` as the default interface for contributor workflows:

- `task ss:contributing:setup` — Install dependencies
- `task ss:contributing:build` — Build the project
- `task ss:contributing:lint` — Run lint checks
- `task ss:contributing:run` — Run local development server
- `task ss:contributing:test` — Run Playwright tests
- `task ss:contributing:test:complexity` — Run code complexity checks
- `task ss:contributing:test:security` — Run all security test suites
- `task ss:contributing:test:sast` — Run SAST tests
- `task ss:contributing:test:vulnerability` — Run vulnerability scanning tests
- `task ss:contributing:test:dast` — Run DAST tests
- `task ss:contributing:test:secrets` — Run secrets detection tests

Use namespaced documentation tasks via root Taskfile. Check available tasks with `task --list`:

- `task ss:hygiene:test`
- `task ss:hygiene:lint`
- `task ss:security:scan`
- `task ss:security:sast`
- `task ss:security:vulnerability:all`
- `task ss:decisions:validate`
- `task ss:decisions:new SLUG=<name>`

## Workflow

- Create a focused branch for each change.
- Keep pull requests small and reviewable.
- Link changes to relevant decisions or issues when applicable.

## Pre-Merge Checks

- Verify tests and checks pass.
- Confirm documentation is updated when behavior or structure changes.
- Ensure no accidental scope creep is included.

## Coding Conventions

- Prefer clarity over cleverness.
- Keep changes minimal and localized.
- Follow existing project style and naming patterns.

## When to Split into Additional Files

If this document becomes too long or team/process complexity increases, split details into:

- `DEVELOPMENT_WORKFLOW.md`
- `PR_CHECKLIST.md`
- `CODING_STANDARDS.md`
