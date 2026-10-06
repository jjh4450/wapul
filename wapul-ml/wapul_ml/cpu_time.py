"""CPU inference time per solution, for the parts a service would run.

    python -m wapul_ml.cpu_time

Weights do not change the time, so untrained models are timed. Threads are capped at THREADS,
as on a small server. Timed per solution, on a fixed random sample plus the solution with the
most logic units:
- kinds: CodeBERT over each unit with context (codeseg.py), one pass per unit
- linker, AST: disentangle_ast.py's net over every candidate of every logic unit
- linker, CodeBERT: disentangle.py, one pass per candidate, so about n(n+1)/2 for n logic units;
  also with dynamic int8 quantization, the usual CPU deployment
"""

import time

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from wapul_ml import codeseg, disentangle, disentangle_ast
from wapul_ml.data import context_text, load_solutions

THREADS = 4
SAMPLE = 40


@torch.no_grad()
def encode(model, tok, texts: list[str], max_len: int) -> None:
    for k in range(0, len(texts), codeseg.BATCH):
        enc = tok(texts[k : k + codeseg.BATCH], truncation=True, max_length=max_len, padding=True, return_tensors="pt")
        model(**enc)


def timed(fn) -> float:
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def report(name: str, seconds: list[float]) -> None:
    s = np.array(seconds)
    print(
        f"  {name:<26} median {np.median(s):6.2f}s  p90 {np.percentile(s, 90):6.2f}s  max {s.max():6.2f}s", flush=True
    )


def main() -> None:
    torch.set_num_threads(THREADS)
    sols = load_solutions()
    n_logic = np.array([sum(u.kind == "logic" for u in s.units) for s in sols])
    pick = sorted({*np.random.default_rng(0).choice(len(sols), SAMPLE, replace=False).tolist(), int(n_logic.argmax())})
    print(f"{len(pick)} solutions, logic units: median {int(np.median(n_logic[pick]))}, max {n_logic[pick].max()}")
    print(f"CodeBERT passes for the CodeBERT linker: median {int(np.median(n_logic[pick] * (n_logic[pick] + 1) / 2))}")

    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    kind_model = AutoModelForSequenceClassification.from_pretrained(codeseg.MODEL, num_labels=4).eval()
    link_model = AutoModelForSequenceClassification.from_pretrained(codeseg.MODEL, num_labels=1).eval()
    link_int8 = torch.ao.quantization.quantize_dynamic(link_model, {torch.nn.Linear}, dtype=torch.qint8)
    net = torch.nn.Sequential(torch.nn.Linear(26, 64), torch.nn.ReLU(), torch.nn.Linear(64, 1)).eval()

    kinds, ast_link, bert_link, bert_int8 = [], [], [], []
    for i in pick:
        s = sols[i]
        texts = [context_text(s.units, j) for j in range(len(s.units))]
        kinds.append(timed(lambda texts=texts: encode(kind_model, tok, texts, codeseg.MAX_LEN)))
        a = disentangle_ast.Candidates(s)
        ast_link.append(timed(lambda a=a: [net(r) for r in a.rows]))
        b = disentangle.Candidates(s)
        bert_link.append(timed(lambda b=b: [encode(link_model, tok, x, disentangle.MAX_LEN) for x in b.texts]))
        bert_int8.append(timed(lambda b=b: [encode(link_int8, tok, x, disentangle.MAX_LEN) for x in b.texts]))
        print(f"    solution {i}: {n_logic[i]} logic units, CodeBERT linker {bert_link[-1]:.1f}s", flush=True)
    print(f"per solution, {THREADS} CPU threads")
    report("kinds (CodeBERT)", kinds)
    report("linker, AST net", ast_link)
    report("linker, CodeBERT", bert_link)
    report("linker, CodeBERT int8", bert_int8)


if __name__ == "__main__":
    main()
