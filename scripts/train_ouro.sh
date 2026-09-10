#!/usr/bin/env bash
set -euo pipefail
OURO_TRAINER=${OURO_TRAINER:?Set OURO_TRAINER to your Ouro training script}
DATASET=${1:?Usage: train_ouro.sh DATASET.jsonl OUTPUT_DIR}
OUTPUT=${2:?Usage: train_ouro.sh DATASET.jsonl OUTPUT_DIR}
DATASET_ABS=$(realpath "$DATASET")
OUTPUT_ABS=$(realpath -m "$OUTPUT")
MODE=${MODE:-qlora}
MAX_SAMPLES=${MAX_SAMPLES:-0}
MAX_LENGTH=${MAX_LENGTH:-1024}
EPOCHS=${EPOCHS:-1}
SEED=${SEED:-42}
TRAINER_ABS=$(realpath "$OURO_TRAINER")
uv run python "$TRAINER_ABS" --mode "$MODE" --dataset "$DATASET_ABS" --max-samples "$MAX_SAMPLES" --max-length "$MAX_LENGTH" --epochs "$EPOCHS" --seed "$SEED" --output-dir "$OUTPUT_ABS"
