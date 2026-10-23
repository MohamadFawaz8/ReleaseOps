# Lesson 02: Diagnose and repair a failed CI check

This is a controlled learning exercise, not a production incident. The application
is the local ReleaseOps API, and CI runs on a standard GitHub-hosted Ubuntu runner.

## Evidence and diagnosis

1. The baseline workflow passed on `main`.
2. A practice branch changed the health test's expected status from 200 to 503.
3. Local pytest reported `assert 200 == 503`, one failed test, three passing tests,
   and process exit code 1.
4. The learner opened [PR #1](https://github.com/MohamadFawaz8/ReleaseOps/pull/1)
   from `practice/ci-failure` into `main`, triggering the pull-request workflow.
5. The [failed hosted run](https://github.com/MohamadFawaz8/ReleaseOps/actions/runs/40006352693)
   completed dependency setup, lint, and formatting successfully. Its `Run tests`
   step failed. This narrows the investigation to the tests and application behavior.

The health endpoint's defined contract is HTTP 200 with `{"status":"ok"}` when the
process responds. The application still followed that contract; the exercise had
introduced an incorrect test expectation. A failing test alone does not establish
whether the test, application, or environment is wrong: compare the assertion,
actual response, intended contract, and recent change.

## Repair and verification

The expectation was restored to 200. Local verification with
`uv run --locked pytest -q` produced four passing tests. The application and workflow
configuration were unchanged during the repair.

Pushing the repair to the same open PR branch triggers a new CI run through the
default `pull_request` synchronize event. Inspect the latest result in the PR's
checks; the original failed run remains useful historical evidence.

Before merging, verify that the newest commit passed, inspect the files changed,
and confirm the assertion checks the intended behavior. Fixes should address the
cause rather than remove the test or hide its failed exit code.

## Exercise

Compare the failed run with the newest PR run. Identify the first failed step,
the expected and actual HTTP statuses, and the process exit code. Explain why
retrying the same unchanged commit would not repair this assertion failure.

A failed CI check reports a problem. Making a passing check a merge requirement
requires a separate branch-protection rule or repository ruleset.
