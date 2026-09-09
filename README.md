# Pi Trajectory Recorder

An opt-in Pi extension for collecting redacted agent trajectories as training data, plus repeatable tool-use benchmarks. It is designed for teacher-trace collection (for example, Qwen in Pi) and downstream Ouro SFT/QLoRA.

## What it records

The recorder captures prompts, system context, model/session metadata, tool calls, tool results, errors, and final messages. Recording is opt-in and defaults off. Secrets and home-directory paths are redacted; review data before sharing.

## Install locally

From this repository:

```bash
cd /home/alex/Code/pi-trajectory-recorder
npm install
PI_TRAJECTORY_RECORD=1 \
PI_TRAJECTORY_DIR=$PWD/traces \
pi --extension $PWD/extension/trajectory-recorder.ts --model ouro-local/ouro-2.6b-thinking
```

Use `/trace-status` and `/trace-record` in Pi. Records are written to `traces/trajectories.jsonl`.

## Run the benchmark

```bash
python3 scripts/run_benchmarks.py \
  --model qwen3.6-27b \
  --record-dir traces/qwen-teacher \
  --out outputs/qwen-teacher.json
```

The benchmark deliberately includes web, Bash, mixed web→Bash, and no-tool tasks. It is a prompt-and-trace harness: the model must run through Pi and the recorder captures the trajectory.

## Review and filter

```bash
python3 scripts/review_traces.py traces/qwen-teacher/trajectories.jsonl \
  --successful-only --min-tools 1 \
  --label qwen-teacher-v1 \
  --output outputs/reviewed.jsonl
```

## Export for Ouro

```bash
python3 scripts/normalize_traces.py \
  traces/qwen-teacher/trajectories.jsonl \
  outputs/ouro-train.jsonl \
  --successful-only

JLENS_ROOT=/home/alex/Code/jlens/jacobian-lens \
bash scripts/train_ouro.sh outputs/ouro-train.jsonl outputs/ouro-adapter
```

## Milestones

Send a readable result table through Moneypenny with:

```bash
bash scripts/notify_milestone.sh "Pi teacher benchmark" "Model | Task success\nQwen | 80%"
```

This project intentionally does not upload traces automatically. Review and redact before publishing.
