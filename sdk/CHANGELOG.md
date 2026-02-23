# Changelog

All notable changes to the AgentGuard SDK will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2025-02-22

### Added
- `AgentGuardClient` — core client for all AgentGuard API operations
- `enforce(action, resource, context)` — real-time permission check
- `log_action(...)` — audit log submission
- `query_logs(...)` — audit log querying with filters
- Admin methods: `create_agent`, `set_policy`, `get_policy`, `list_agents`, `get_agent`, `delete_agent`
- Framework integration examples: LangGraph, AutoGen, CrewAI
- MIT license

[0.1.0]: https://github.com/agentguard/agentguard-sdk/releases/tag/v0.1.0
