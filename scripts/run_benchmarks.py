#!/usr/bin/env python3
"""Run repeatable Pi prompts with recording enabled and score traces."""
import argparse, json, os, subprocess, time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tasks",default="benchmarks/tasks.jsonl"); ap.add_argument("--out",default="outputs/benchmark-results.json"); ap.add_argument("--record-dir",default="traces"); ap.add_argument("--model",default=None); ap.add_argument("--pi",default="pi"); ap.add_argument("--extension",default="extension/trajectory-recorder.ts"); args=ap.parse_args()
    tasks=[json.loads(x) for x in Path(args.tasks).read_text().splitlines() if x.strip()]; results=[]; record=Path(args.record_dir); record.mkdir(parents=True,exist_ok=True)
    for task in tasks:
        before=set(record.glob("*.jsonl")); env={**os.environ,"PI_TRAJECTORY_RECORD":"1","PI_TRAJECTORY_DIR":str(record.resolve())}
        cmd=[args.pi,"-p","--mode","json","--no-session","-e",args.extension,"--thinking","off"]
        if args.model: cmd += ["--model",args.model]
        cmd += [task["prompt"]]
        started=time.time(); proc=subprocess.run(cmd,text=True,capture_output=True,env=env); time.sleep(.2)
        files=sorted(record.glob("*.jsonl"),key=lambda p:p.stat().st_mtime,reverse=True); calls=[]
        if files:
            try:
                rows=[json.loads(x) for x in files[0].read_text().splitlines() if x.strip()]; row=rows[-1] if rows else {}; calls=[e.get("name") for e in row.get("tool_events",[]) if e.get("type")=="tool_call"]
            except Exception: row={}
        text=(proc.stdout+proc.stderr).lower(); needed=set(task.get("needs",[])); seen=set(calls); answer_ok=all(term.lower() in text for term in task.get("answer_terms",[])); results.append({"id":task["id"],"returncode":proc.returncode,"calls":calls,"needed_tools":sorted(needed),"tool_selection":needed.issubset(seen) and len(seen-needed)==0 if needed else not calls,"answer_terms":answer_ok,"elapsed_s":round(time.time()-started,2)})
    summary={"n_tasks":len(results),"tool_success_rate":sum(r["tool_selection"] for r in results)/len(results),"answer_rate":sum(r["answer_terms"] for r in results)/len(results),"task_success_rate":sum(r["tool_selection"] and r["answer_terms"] for r in results)/len(results),"rows":results}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(summary,indent=2)+"\n"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
