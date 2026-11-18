# QA plans

The active behavior matrix is [QA_PLAYBOOK_V4.md](../../docs/QA_PLAYBOOK_V4.md),
with exit and recovery contracts in [UI_DESIGN_PLAN_V2.md](../../docs/UI_DESIGN_PLAN_V2.md).

Official planner/generator/healer templates are in `qa/.codex/`. They are workflow
templates, not evidence that workers are available or that the product passed.
`qa/seed.spec.ts` is an untouched official seed and is outside the configured
`qa/e2e` test directory. Implement regression cases against real user behavior;
never delete assertions, skip requirements or relax expected results to get green.
