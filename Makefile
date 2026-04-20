PYTHON ?= python3

.PHONY: quality test eval

quality:
	bash scripts/run_quality_gate.sh

test:
	$(PYTHON) -m pytest tests -q

eval:
	$(PYTHON) evals/run_static_evals.py
