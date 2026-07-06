# Jerry Manager Model → 9to5 Integration

End-to-end: a fine-tuned clone of the operator's gate decisions, wired into 9to5's
control plane to (eventually) resolve approval gates the way the operator would.

## Pipeline

```
gold_source_of_truth.jsonl            (1,413 verified human decisions)
    → build_sft_dataset.py --require-context   → datasets/sft/{train,val,test}.jsonl (1,140, clean)
    → train_sft.py (unsloth QLoRA, Qwen2.5-3B) → models/jerry-sft/  (LoRA adapter)
    → try_jerry.py                              → eyeball usability on held-out cases
    → jerry_serve.py (WSL GPU service)          → POST /decide {gate,context}->{verb,message,confidence}
    → 9to5 notifications/jerry_client.py        → calls the service at a gate (zero-dep)
    → 9to5 _handleOtherGate (SHADOW MODE)       → logs model-vs-human; human still decides
```

## Why a service + client (not a direct import)

9to5's bot runs in its own env (often Windows); the model needs the WSL GPU + unsloth.
So the model runs as a localhost HTTP service in WSL, and 9to5 calls it via a pure-stdlib
client. WSL2 forwards `localhost`, so Windows↔WSL works. The client never raises and never
blocks: any failure → returns `None` → 9to5 uses the normal human Discord gate.

## Verb contract

The model emits Jerry's natural-language decision; `jerry_serve.map_verb` maps it to a
9to5 control verb (mirrors `notifications/ask.py`): `approve | reject | retry | abort |
pause | resume | none`. `none` (or confidence 0) = "can't tell → defer to human".

## Run sequence (WSL, the training venv)

```bash
cd /mnt/c/manager-data && source ~/sft/bin/activate
# 1. retrain on the clean v2 data (best-checkpoint, dropout, ~60-75 min)
python manager_data/scripts/train_sft.py
# 2. sanity-check generations on held-out, has-context cases
python manager_data/scripts/try_jerry.py
# 3. start the decision service (leave running)
python manager_data/scripts/jerry_serve.py        # http://127.0.0.1:8008
```

## Turn on SHADOW MODE in 9to5 (safe: log-only)

```bash
# in the 9to5 bot's environment:
export JERRY_SHADOW=1          # Windows: set JERRY_SHADOW=1
# (optional) export JERRY_URL=http://127.0.0.1:8008
# run 9to5 as normal. At each pre_pr / other gate it will:
#   - ask the model for its verb (logged to 9to5 logs/jerry_shadow.jsonl)
#   - STILL wait for your Discord /approve|/reject — the model changes nothing
```

Let it run over real gates. Each line in `logs/jerry_shadow.jsonl` is
`{gate, model_verb, model_confidence, human_verb, agreed}`.

## Go / no-go for autonomy

Read the shadow log. When agreement is high (e.g. ≥90% on `approve`/`reject` at
confidence ≥ 0.8) over a meaningful number of gates, flip on confidence-gated autonomy:
in `_handleOtherGate`, when `_jerry_pred` is confident enough, push its verb onto the
ControlBus (the same channel `/approve` uses) instead of waiting — BUT:

- **never** auto-resolve a destructive / `escalate_risk` gate (always human),
- keep `/approve` override + the full decision log,
- keep the human deadline fallback.

Until then it is strictly shadow (observe + measure). Autonomy is a deliberate, data-gated
follow-up, not a default.

## Safety of the current 9to5 edit

The change to `_handleOtherGate` is: opt-in (`JERRY_SHADOW=1`, default off → zero behavior
change), fully `try/except`-wrapped (cannot break the gate loop), and **log-only** (never
touches `bus`/decision). Reversible by deleting the two added blocks (and `jerry_client.py`).
