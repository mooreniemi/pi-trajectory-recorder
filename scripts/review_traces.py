#!/usr/bin/env python3
"""Review/filter recorder JSONL before using it as training data."""
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("--output"); ap.add_argument("--successful-only",action="store_true"); ap.add_argument("--min-tools",type=int,default=0); ap.add_argument("--label"); args=ap.parse_args()
    rows=[]
    for line in Path(args.input).read_text().splitlines():
        if not line.strip(): continue
        row=json.loads(line); calls=[e for e in row.get("tool_events",[]) if e.get("type")=="tool_call"]; errors=[e for e in row.get("tool_events",[]) if e.get("type")=="tool_result" and e.get("is_error")]
        if args.successful_only and errors: continue
        if len(calls)<args.min_tools: continue
        row["review"]={"tool_count":len(calls),"tool_names":[e.get("name") for e in calls],"error_count":len(errors)}
        if args.label: row["label"]=args.label
        rows.append(row)
    print(f"records={len(rows)}")
    for i,row in enumerate(rows): print(f"{i}: {row.get('prompt','')[:100]!r} tools={row['review']['tool_names']} errors={row['review']['error_count']}")
    if args.output:
        Path(args.output).parent.mkdir(parents=True,exist_ok=True); Path(args.output).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else "")); print(f"wrote {len(rows)} records to {args.output}")
if __name__=="__main__": main()
