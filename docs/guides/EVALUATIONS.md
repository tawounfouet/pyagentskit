# Evaluations

PyAgentsKit 0.9.0 separates deterministic release gates from model-based quality judgments.
`EvalDataset` and `EvalReport` are strict, versioned JSON contracts. Assertions support terminal
status, exact text, containment, regular expressions, cost ceilings and duration ceilings.

```python
report = await Evaluator().evaluate(dataset, target)
save_eval_report(report, "candidate.json")
comparison = compare_reports(baseline, report, max_pass_rate_regression=0.0)
```

The target is an async callable receiving an `EvalCase` and returning a `RunResult`. Cases run
sequentially in 0.9.0 so results are stable and application rate limits are not guessed. Optional
`ModelJudge` implementations append advisory scores but never change deterministic pass/fail.

Use `pyagentskit eval validate dataset.json` before a campaign and `pyagentskit eval compare
baseline.json candidate.json` in CI. Exit code 2 means invalid input or an unacceptable regression.
The reference dataset in `evals/reference_dataset.json` performs no network call.

Do not store prompts containing secrets or personal data in versioned datasets. Live evaluations
remain explicit, budgeted and application-owned.
