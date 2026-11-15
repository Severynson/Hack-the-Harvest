import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "nemotron_agent", Path(__file__).resolve().parents[1] / "autoresearch" / "nemotron_agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

GOOD = """import time
import numpy as np
from prepare import evaluate
t0 = time.time()
def fit_predict(ts_tr, lab_tr, ts_te, keys_te):
    return np.zeros(len(keys_te), dtype=int)
"""


def test_parse_reply_strips_run_block():
    reply = f"<think>x</think>DESCRIPTION: blank\n```python\n{GOOD}{agent.RUN_BLOCK}```"
    desc, code = agent.parse_reply(reply.split("</think>")[-1])
    assert desc == "blank"
    assert "evaluate(fit_predict)" not in code
    agent.check_code(code)


def test_parse_reply_needs_format():
    with pytest.raises(ValueError):
        agent.parse_reply("here is my idea")


@pytest.mark.parametrize("bad", [GOOD.replace("import numpy as np", "import os"),
                                 GOOD.replace("fit_predict", "fit"),
                                 GOOD.replace("t0 = time.time()", ""),
                                 GOOD + "def broken(:\n"])
def test_check_code_rejects(bad):
    with pytest.raises(ValueError):
        agent.check_code(bad)


def test_seed_passes_check():
    agent.check_code(agent.SEED.read_text(encoding="utf-8"))
