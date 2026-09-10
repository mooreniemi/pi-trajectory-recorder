import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import type {
  AgentEndEvent,
  ExtensionAPI,
  ExtensionContext,
  ToolCallEvent,
  ToolResultEvent,
} from "@mariozechner/pi-coding-agent";

const enabled = process.env.PI_TRAJECTORY_RECORD === "1";
const outputDir = process.env.PI_TRAJECTORY_DIR || path.join(os.homedir(), ".pi", "trajectories");
const maxText = Number(process.env.PI_TRAJECTORY_MAX_CHARS || 12000);
let recording = enabled;

function redactText(value: string): string {
  return value
    .replace(/(?:sk|rk)-[A-Za-z0-9_-]{12,}/g, "[REDACTED_KEY]")
    .replace(/(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+/gi, "$1=[REDACTED]")
    .replace(/(?:\/home\/|\/Users\/|\/root\/)[^\s\"']+/g, "[HOME_PATH]")
    .slice(0, maxText);
}

function redact(value: unknown): unknown {
  if (typeof value === "string") return redactText(value);
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, redact(item)]));
  }
  return value;
}

function append(record: unknown): void {
  fs.mkdirSync(outputDir, { recursive: true, mode: 0o700 });
  fs.appendFileSync(path.join(outputDir, "trajectories.jsonl"), JSON.stringify(redact(record) as object) + "\n", { mode: 0o600 });
}

function textContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((part) => typeof part === "object" && part && "text" in part ? String((part as {text: unknown}).text) : "").join("\n");
  return content == null ? "" : String(content);
}

export default function (pi: ExtensionAPI): void {
  let trace: Record<string, unknown> | undefined;
  let toolEvents: unknown[] = [];

  pi.registerFlag("trajectory-record", { type: "boolean", description: "Record a redacted training trajectory", default: enabled });
  pi.registerCommand("trace-status", { description: "Show trajectory recorder status", handler: async (_args, ctx) => {
    ctx.ui.notify(`trajectory recorder: ${recording ? "on" : "off"}; output=${outputDir}`, "info");
  }});
  pi.registerCommand("trace-record", { description: "Toggle trajectory recording", handler: async (_args, ctx) => {
    recording = !recording;
    ctx.ui.notify(`trajectory recorder ${recording ? "enabled" : "disabled"}`, "info");
  }});

  pi.on("before_agent_start", async (event, ctx) => {
    if (!recording) return;
    toolEvents = [];
    trace = {
      schema_version: "pi-trajectory-v1",
      started_at: new Date().toISOString(),
      cwd: ctx.cwd,
      session_file: ctx.sessionManager.getSessionFile(),
      model: ctx.model ? { provider: ctx.model.provider, id: ctx.model.id } : undefined,
      system_prompt: event.systemPrompt,
      prompt: event.prompt,
      tools: pi.getAllTools().map((tool) => ({ name: tool.name, parameters: tool.parameters })),
      tool_events: toolEvents,
    };
  });

  pi.on("tool_call", async (event: ToolCallEvent) => {
    if (!trace) return;
    toolEvents.push({ type: "tool_call", at: new Date().toISOString(), id: event.toolCallId, name: event.toolName, arguments: event.input });
  });

  pi.on("tool_result", async (event: ToolResultEvent) => {
    if (!trace) return;
    toolEvents.push({ type: "tool_result", at: new Date().toISOString(), id: event.toolCallId, name: event.toolName, input: event.input, content: event.content, is_error: event.isError, details: event.details });
  });

  pi.on("agent_end", async (event: AgentEndEvent) => {
    if (!trace) return;
    const messages = event.messages.map((message) => ({
      role: message.role,
      content: "content" in message ? textContent(message.content) : undefined,
      tool_call_id: "toolCallId" in message ? message.toolCallId : undefined,
      tool_name: "toolName" in message ? message.toolName : undefined,
    }));
    append({ ...trace, ended_at: new Date().toISOString(), messages, tool_events: toolEvents });
    trace = undefined;
  });
}
