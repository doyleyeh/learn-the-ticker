PYTHON ?= python3

.PHONY: quality test eval contracts
quality:
	bash scripts/run_quality_gate.sh
test:
	$(PYTHON) -m pytest tests -q
eval:
	$(PYTHON) evals/run_static_evals.py
contracts:
	$(PYTHON) -m scripts.contracts
	node scripts/generate_types.mjs
