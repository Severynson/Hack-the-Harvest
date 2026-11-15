"""Smoke test before any fine-tuning: can this machine load a Nemotron model and generate with it?

Prints what the fine-tune script needs to know: the GPU, which loader works (Unsloth or plain
transformers), the names of the layers a LoRA adapter can attach to, how the model answers a
one-word question (so we can see whether it writes reasoning first), and the memory used.

Run in the separate LLM environment, never the data environment:
    cd /workspace && HF_HOME=/tmp/hf /tmp/llm/bin/python -m kernelag.nemotron_check
"""

from __future__ import annotations

import collections
import os
import time

from kernelag.paths import secret

MODEL = os.environ.get("KERNEL_NEMOTRON", "nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16")
QUESTION = "Answer with one word, silage or grain. Corn chopped green in August and fed to dairy cows is harvested for:"


def load(token):
    """Try Unsloth first (it documents Nemotron support), then plain transformers."""
    import torch

    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=MODEL, max_seq_length=2048, load_in_4bit=False, token=token)
        return model, tokenizer, "unsloth"
    except Exception as error:  # report and fall back; this script exists to find out what works
        print("unsloth loader failed:", type(error).__name__, str(error)[:600], flush=True)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL, token=token, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, token=token, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda")
    return model, tokenizer, "transformers"


def main() -> None:
    import torch

    print("torch", torch.__version__, "| cuda", torch.cuda.is_available(), flush=True)
    print("gpu:", torch.cuda.get_device_name(0))
    x = torch.randn(4096, 4096, device="cuda")
    print("gpu matrix product ok:", float((x @ x).mean()) == float((x @ x).mean()))

    token = secret("HF_TOKEN") or None
    print("model:", MODEL, "| HF token set:", bool(token), flush=True)
    start = time.time()
    model, tokenizer, loader = load(token)
    print(f"loaded with {loader} in {time.time() - start:.0f}s", flush=True)
    print("parameters (billions):", round(sum(p.numel() for p in model.parameters()) / 1e9, 2))

    linear = collections.Counter(
        name.split(".")[-1] for name, module in model.named_modules() if isinstance(module, torch.nn.Linear))
    print("linear layer names (LoRA targets):", dict(linear.most_common(20)))

    messages = [{"role": "user", "content": QUESTION}]
    inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt",
                                           return_dict=True).to("cuda")
    start = time.time()
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=60, do_sample=False)
    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    print(f"answer ({len(new_tokens)} tokens, {time.time() - start:.1f}s):",
          repr(tokenizer.decode(new_tokens, skip_special_tokens=False)))
    print("prompt as the model sees it:", repr(tokenizer.decode(inputs["input_ids"][0])[-300:]))
    print("gpu memory used (GB):", round(torch.cuda.max_memory_allocated() / 1e9, 1))


if __name__ == "__main__":
    main()
