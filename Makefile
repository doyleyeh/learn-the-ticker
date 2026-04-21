PYTHON ?= python3

.PHONY: quality test eval local-merge setup-wsl-agent-env

quality:
	bash scripts/run_quality_gate.sh

test:
	$(PYTHON) -m pytest tests -q

eval:
	$(PYTHON) evals/run_static_evals.py

local-merge:
	bash scripts/local_merge_task.sh

setup-wsl-agent-env:
	bash scripts/setup_wsl_agent_env.sh
