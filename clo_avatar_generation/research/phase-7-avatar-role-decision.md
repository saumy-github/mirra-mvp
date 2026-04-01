# Phase 7 Avatar Role Decision

## Goal

Turn the CLO-native path into a decision-ready experiment.

This phase does not change runtime behavior. It creates a structured way to answer:

1. should the CLO-native avatar become the final visible avatar
2. should it remain only a simulation proxy
3. should the path be rejected

## What was added

### Decision logic

- `decision_matrix.py`

This file contains the isolated scoring and recommendation logic for the CLO-native path.

### Decision runner

- `evaluate_avatar_role.py`

This file provides a CLI to write a report for the current recommendation.

### Schema note

- `schema/avatar_role_decision.md`

This records the meaning of the three possible outcomes.

## Decision inputs used in this phase

The current decision model uses:

- body fidelity
- arrangement reliability
- placement quality
- simulation cleanliness
- implementation cost

This is enough to make the experiment decision-ready without binding the result to hidden assumptions in chat.

## Why this phase matters

Earlier phases made the CLO-native path technically isolated.

This phase makes it strategically isolated too:

- we can evaluate it
- we can document the recommendation
- we can choose its role without editing the default pipeline

## What this phase does not do

1. It does not declare the winner automatically.
2. It does not compare against STAR by itself.
3. It does not alter the default user-visible avatar path.

