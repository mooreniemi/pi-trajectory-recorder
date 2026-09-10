#!/usr/bin/env python3
"""Export pi-trajectory-v1 JSONL as MLflow agent/tool traces."""
import argparse
import json
from pathlib import Path


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return "" if content is None else str(content)


def final_answer(row):
    answers = [m for m in row.get("messages", []) if m.get("role") == "assistant" and text_content(m.get("content"))]
    return text_content(answers[-1].get("content")) if answers else ""


def export_row(mlflow, row, index):
    model = row.get("model") or {}
    name = f"pi-task-{index:05d}"
    attributes = {
        "schema_version": row.get("schema_version", "pi-trajectory-v1"),
        "model_provider": model.get("provider", ""),
        "model_id": model.get("id", ""),
        "tool_count": sum(event.get("type") == "tool_call" for event in row.get("tool_events", [])),
        "error_count": sum(event.get("type") == "tool_result" and event.get("is_error", False) for event in row.get("tool_events", [])),
    }
    with mlflow.start_span(name=name, span_type="AGENT") as root:
        root.set_inputs({"prompt": row.get("prompt", "")})
        root.set_attributes(attributes)
        for event in row.get("tool_events", []):
            if event.get("type") != "tool_call":
                continue
            result = next((candidate for candidate in row.get("tool_events", [])
                           if candidate.get("type") == "tool_result" and candidate.get("id") == event.get("id")), None)
            with mlflow.start_span(name=f"tool:{event.get('name', 'unknown')}", span_type="TOOL") as tool:
                tool.set_inputs(event.get("arguments", {}))
                tool.set_attributes({"tool_call_id": event.get("id", ""), "tool_name": event.get("name", "")})
                if result is not None:
                    tool.set_outputs({"content": text_content(result.get("content")), "is_error": bool(result.get("is_error", False))})
        root.set_outputs({"answer": final_answer(row)})
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="recorder trajectories.jsonl")
    parser.add_argument("--tracking-uri", default="http://127.0.0.1:5000")
    parser.add_argument("--experiment", default="pi-trajectory-recorder")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--raw-artifact", action="store_true", help="also log the source JSONL as a run artifact")
    args = parser.parse_args()

    try:
        import mlflow
    except ImportError as exc:
        raise SystemExit("MLflow is required. Run with: uv run --with mlflow python scripts/export_mlflow.py ...") from exc

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)
    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    with mlflow.start_run(run_name=f"import-{Path(args.input).stem}") as run:
        if args.raw_artifact:
            mlflow.log_artifact(args.input, artifact_path="source")
        for index, row in enumerate(rows):
            export_row(mlflow, row, index)
        mlflow.log_param("source_schema", "pi-trajectory-v1")
        mlflow.log_param("source_file", Path(args.input).name)
        mlflow.log_metric("trajectory_count", len(rows))
        print(f"exported {len(rows)} traces to experiment={args.experiment!r} run={run.info.run_id}")


if __name__ == "__main__":
    main()
