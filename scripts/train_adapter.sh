#!/usr/bin/env bash
set -euo pipefail
TRAINING_ENTRYPOINT=${TRAINING_ENTRYPOINT:?Set TRAINING_ENTRYPOINT to your training script}
DATASET=${1:?Usage: train_adapter.sh DATASET.jsonl OUTPUT_DIR}
OUTPUT=${2:?Usage: train_adapter.sh DATASET.jsonl OUTPUT_DIR}
DATASET_ABS=$(realpath "$DATASET")
OUTPUT_ABS=$(realpath -m "$OUTPUT")
MODE=${MODE:-qlora}
MAX_SAMPLES=${MAX_SAMPLES:-0}
MAX_LENGTH=${MAX_LENGTH:-1024}
EPOCHS=${EPOCHS:-1}
SEED=${SEED:-42}
PYTHON=${PYTHON:-python3}
TRAINER_ABS=$(realpath "$TRAINING_ENTRYPOINT")
"$PYTHON" "$TRAINER_ABS" --mode "$MODE" --dataset "$DATASET_ABS" --max-samples "$MAX_SAMPLES" --max-length "$MAX_LENGTH" --epochs "$EPOCHS" --seed "$SEED" --output-dir "$OUTPUT_ABS"
