#!/usr/bin/env bash
set -euo pipefail
JLENS_ROOT=${JLENS_ROOT:?Set JLENS_ROOT to the jlens repository}
DATASET=${1:?Usage: train_ouro.sh DATASET.jsonl OUTPUT_DIR}
OUTPUT=${2:?Usage: train_ouro.sh DATASET.jsonl OUTPUT_DIR}
DATASET_ABS=$(realpath "$DATASET")
OUTPUT_ABS=$(realpath -m "$OUTPUT")
MODE=${MODE:-qlora}
MAX_SAMPLES=${MAX_SAMPLES:-0}
MAX_LENGTH=${MAX_LENGTH:-1024}
EPOCHS=${EPOCHS:-1}
SEED=${SEED:-42}
cd "$JLENS_ROOT"
uv run --group dev python scripts/train_ouro_tool_lora.py --mode "$MODE" --dataset "$DATASET_ABS" --max-samples "$MAX_SAMPLES" --max-length "$MAX_LENGTH" --epochs "$EPOCHS" --seed "$SEED" --output-dir "$OUTPUT_ABS"
