# Contributing to AgentGuard SDK

Thank you for your interest in contributing. This document covers how to get set up.

## Development Setup

```bash
git clone https://github.com/agentguard/agentguard-sdk
cd agentguard-sdk
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Code Style

```bash
black agentguard/
ruff check agentguard/
mypy agentguard/
```

## Pull Requests

- Open an issue first for non-trivial changes
- Keep PRs focused — one concern per PR
- Add tests for any new behaviour
- Update `CHANGELOG.md` under `[Unreleased]`

## Reporting Bugs

Open an issue at [github.com/agentguard/agentguard-sdk/issues](https://github.com/agentguard/agentguard-sdk/issues).

Include: Python version, SDK version, minimal reproduction, expected vs actual behaviour.
