#!/usr/bin/env python3
"""Convert recorder JSONL into Ouro/Pi SFT JSONL."""
import argparse, json
from pathlib import Path

def message_text(message):
    content = message.get("content")
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return "" if content is None else str(content)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("output"); ap.add_argument("--successful-only", action="store_true"); args=ap.parse_args()
    out=[]
    for line in Path(args.input).read_text().splitlines():
        row=json.loads(line); events=row.get("tool_events", [])
        if args.successful_only and any(e.get("is_error") for e in events if e.get("type")=="tool_result"): continue
        messages=[]
        if row.get("system_prompt"): messages.append({"role":"system","content":row["system_prompt"]})
        if row.get("prompt"): messages.append({"role":"user","content":row["prompt"]})
        for event in events:
            if event.get("type")=="tool_call":
                messages.append({"role":"assistant","content":None,"tool_calls":[{"id":event.get("id","call_0"),"type":"function","function":{"name":event["name"],"arguments":json.dumps(event.get("arguments",{}),separators=(",",":"))}}]})
            elif event.get("type")=="tool_result":
                content="\n".join(x.get("text","") for x in event.get("content",[]) if isinstance(x,dict))
                messages.append({"role":"tool","tool_call_id":event.get("id","call_0"),"name":event.get("name"),"content":content})
        # Tool events alone are insufficient for SFT; retain the final answer.
        assistant_messages = [m for m in row.get("messages", [])
                              if m.get("role") == "assistant" and message_text(m)]
        if assistant_messages:
            messages.append({"role":"assistant","content":message_text(assistant_messages[-1])})
        out.append({"messages":messages,"tools":row.get("tools",[]),"source":"pi-trajectory-recorder","trace_started_at":row.get("started_at")})
    Path(args.output).parent.mkdir(parents=True,exist_ok=True); Path(args.output).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in out)+("\n" if out else "")); print(f"wrote {len(out)} records to {args.output}")
if __name__=="__main__": main()
