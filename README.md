# Pi Trajectory Recorder

An opt-in Pi extension for collecting redacted agent trajectories as training data, plus repeatable tool-use benchmarks. It is designed for collecting high-quality agent trajectories from one configured model and using them to train or evaluate another model with SFT/QLoRA.

## What it records

The recorder captures prompts, system context, model/session metadata, tool calls, tool results, errors, and final messages. Recording is opt-in and defaults off. Common secrets and local home-directory paths are redacted by default; review every export before sharing.

### Example recorded trajectory

The following is synthetic example data. A raw recorder record is one JSON object per line and preserves the interaction timeline, including tool calls, results, and the final answer:

```json
{
  "schema_version": "pi-trajectory-v1",
  "model": {"provider": "model-provider", "id": "source-model"},
  "prompt": "Find the current release and summarize it.",
  "tools": [{"name": "web_search", "parameters": {"type": "object"}}],
  "tool_events": [
    {"type": "tool_call", "id": "call_1", "name": "web_search", "arguments": {"query": "Example project release"}},
    {"type": "tool_result", "id": "call_1", "name": "web_search", "is_error": false, "content": [{"text": "Example project release 7"}]}
  ],
  "messages": [
    {"role": "assistant", "content": "The current release is version 7."}
  ]
}
```

The normalizer converts that trajectory into a chat-training record suitable for SFT/QLoRA training. Ouro is one example target model; the format is not Ouro-specific:

```json
{
  "messages": [
    {"role": "system", "content": "You are an agent."},
    {"role": "user", "content": "Find the current release and summarize it."},
    {"role": "assistant", "content": null, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\":\"Example project release\"}"}}]},
    {"role": "tool", "tool_call_id": "call_1", "name": "web_search", "content": "Example project release 7"},
    {"role": "assistant", "content": "The current release is version 7."}
  ],
  "source": "pi-trajectory-recorder"
}
```

Errors and retries remain visible in the raw record so they can be filtered or deliberately included as recovery examples.

## End-to-end workflow

The training data is produced by running an evaluation or task dataset through Pi with a configured source model. The dataset supplies realistic prompts; Pi supplies the tool environment; and this extension records what actually happened. The recorder does not invent tool calls or turn static answers into trajectories.

```text
eval/task prompts
        │
        ▼
Pi + source model + configured tools
        │  model chooses tools, receives results, retries, answers
        ▼
redacted trajectories.jsonl
        │
        ├─ review_traces.py       inspect/filter/label successes and failures
        ├─ normalize_traces.py    convert approved traces to chat JSONL
        ▼
target-model SFT/QLoRA training
        │
        ▼
Pi/tool-use benchmark: base vs trained model
```

A typical experiment is: (1) run benchmark prompts with a source model in Pi, (2) review the resulting traces and remove private or undesirable examples, (3) export the approved traces as training data, (4) train an adapter for the target model, and (5) rerun a held-out benchmark to measure tool selection, argument validity, sequencing, recovery, and final task success. The benchmark runner in this repository is a prompt-and-trace harness; the configured Pi tools and task fixtures determine how realistic and reproducible the resulting evaluation is.

## Install locally

From this repository:

```bash
cd pi-trajectory-recorder
npm install
PI_TRAJECTORY_RECORD=1 \
PI_TRAJECTORY_DIR=$PWD/traces \
pi --extension $PWD/extension/trajectory-recorder.ts --model provider/model-id
```

Use `/trace-status` and `/trace-record` in Pi. Records are written to `traces/trajectories.jsonl`.

## Run the benchmark

```bash
python3 scripts/run_benchmarks.py \
  --model provider/model-id \
  --record-dir traces/source-model \
  --out outputs/source-model.json
```

The benchmark deliberately includes web, Bash, mixed web→Bash, and no-tool tasks. It is a prompt-and-trace harness: the model must run through Pi and the recorder captures the trajectory.

## Review and filter

```bash
python3 scripts/review_traces.py traces/source-model/trajectories.jsonl \
  --successful-only --min-tools 1 \
  --label source-model-v1 \
  --output outputs/reviewed.jsonl
```

## Export for training

```bash
python3 scripts/normalize_traces.py \
  traces/source-model/trajectories.jsonl \
  outputs/training-data.jsonl \
  --successful-only

TRAINING_ENTRYPOINT=/path/to/train_lora.py \
PYTHON=/path/to/venv/bin/python \
bash scripts/train_adapter.sh outputs/training-data.jsonl outputs/target-adapter
```

## View traces in MLflow

The recorder JSONL remains the lossless source of truth. To browse trajectories in MLflow, start a local MLflow server with a SQL backend, then export the reviewed JSONL as nested agent/tool traces:

```bash
mkdir -p mlartifacts
uv run --with mlflow mlflow server \
  --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlartifacts
```

In another terminal, export the traces:

```bash
uv run --with mlflow python scripts/export_mlflow.py \
  traces/source-model/trajectories.jsonl \
  --tracking-uri http://127.0.0.1:5000 \
  --experiment pi-trajectory-recorder \
  --raw-artifact
```

Then open `http://127.0.0.1:5000` locally, or use SSH port forwarding from your workstation:

```bash
ssh -L 5000:127.0.0.1:5000 user@host
```

Each trajectory appears as an MLflow agent trace with nested `TOOL` spans, model metadata, tool counts, error counts, and the final answer. MLflow tracing is OpenTelemetry-compatible; this exporter uses MLflow’s Python tracing API rather than making the recorder depend on MLflow at runtime.

## Results and milestones

The benchmark runner writes a machine-readable JSON summary to `outputs/`. Review or format that file with your preferred notification system; this repository does not depend on any host-specific messaging tool.

This project intentionally does not upload traces automatically. Treat traces as sensitive: review and redact every export before publishing, because application-specific secrets or personal data may use formats the built-in redactor cannot recognize.
