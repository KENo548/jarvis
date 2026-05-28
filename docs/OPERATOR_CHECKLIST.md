# JARVIS Operator Checklist (Condensed)

Purpose: quick, preflight and runbook checks for operators enabling capabilities in production.

Pre-deploy (Developer -> Operator handoff)
- Capability has unit tests and integration tests in CI.
- Supply-chain verification passed (`verification.md`).
- Metrics emitted locally (tokens, runtime, success/fail).
- Documentation: `skill.md` + capability manifest present in registry.
- Rollout plan: feature flag, budget cap, canary targets.

Canary / Enablement
- Enable capability under a feature flag and small budget cap.
- Run 5 representative tasks; verify outputs and side effects.
- Confirm metrics in Grafana: invocations, success rate, token usage.
- Check traces for lifecycle transitions and no leaked resources.
- Validate teardown: terminate a running instance and confirm `RESOURCE_CLEANUP` actions.

Monitoring & Ops
- Dashboard: capability cost_per_success, average_token_cost, average_runtime.
- Alert: success_rate drops > 15% in 30m.
- Alert: human_intervention_rate > configured threshold.
- Alert: runtime stuck in `WAITING` > timeout threshold.
- Daily: review top 10 costliest capabilities by `cost_per_success`.

Escalation & Human-in-the-Loop
- If `final_confidence < threshold` or `no candidate passes policy`, pause and open `human_review` ticket.
- Record replay bundle before escalation.
- Operator actions: `approve` / `reject` / `delegate` / `snapshot`.

Emergency Procedures
- Kill switch: global `force_kill` that transitions instances to `FORCE_KILL` and triggers `RESOURCE_CLEANUP`.
- Incident runbook: collect trace id, replay bundle, capability manifest; escalate to dev team.
- Compliance: preserve audit logs and store replay bundles per retention policy.

Notes
- Never enable dynamic capability synthesis in production without full replay and canary harnesses.
- Prefer cheaper, high-utility-per-cost capabilities when acceptable.
