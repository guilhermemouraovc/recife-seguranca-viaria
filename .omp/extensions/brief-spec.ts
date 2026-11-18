// Managed by Brief-Spec. Compatibility markers: briefspec: briefspec.pyz
const PYTHON = "python3";
const BRIEF_SPEC = new URL("../brief-spec/brief-spec.pyz", import.meta.url).pathname;

function contentText(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value
    .map((item) => typeof item === "string" ? item : String(item?.text ?? ""))
    .filter(Boolean).join("\n");
  return String(value?.text ?? value?.content ?? "");
}

export default function briefSpecExtension(pi) {
  pi.setLabel("Brief-Spec verified delivery");
  let activeSessionId = `omp-${crypto.randomUUID()}`;

  async function run(eventName, payload, ctx) {
    const value = {
      ...payload,
      cwd: ctx?.cwd,
      session_id: payload?.session_id ?? payload?.sessionId ?? activeSessionId,
      timestamp: new Date().toISOString(),
    };
    try {
      const result = await pi.exec(PYTHON, [
        BRIEF_SPEC, "hook", "--provider", "omp", "--event", eventName,
        "--payload-json", JSON.stringify(value),
      ], { cwd: ctx?.cwd, timeout: 10000 });
      if (result.code !== 0) {
        pi.logger.warn(`Brief-Spec hook ${eventName} exited ${result.code}`);
        return {};
      }
      return JSON.parse(result.stdout || "{}");
    } catch (error) {
      pi.logger.warn(`Brief-Spec hook ${eventName} failed: ${String(error)}`);
      return {};
    }
  }

  function contextFrom(value) {
    return value?.additionalContext ?? value?.hookSpecificOutput?.additionalContext;
  }

  pi.on("session_start", async (event, ctx) => {
    activeSessionId = event.session_id ?? event.sessionId ?? activeSessionId;
    await run("SessionStart", event, ctx);
  });

  pi.on("before_agent_start", async (event, ctx) => {
    const result = await run("UserPromptSubmit", { prompt: event.prompt }, ctx);
    const context = contextFrom(result);
    if (!context) return;
    return {
      message: {
        customType: "brief-spec.context",
        content: context,
        display: false,
        details: { source: "brief-spec", version: "0.5.0" },
        attribution: "Brief-Spec",
      },
    };
  });

  pi.on("tool_result", async (event, ctx) => {
    await run("PostToolUse", { tool_name: event.toolName, is_error: event.isError }, ctx);
  });

  pi.on("session.compacting", async (event, ctx) => {
    const result = await run("PreCompact", { session_id: event.sessionId }, ctx);
    const context = contextFrom(result);
    return context ? { context: [context] } : undefined;
  });

  pi.on("session_stop", async (event, ctx) => {
    await run("SessionStop", {
      session_id: event.session_id,
      turn_id: String(event.turn_id),
      stop_hook_active: event.stop_hook_active,
    }, ctx);
  });

  pi.on("agent_end", async (event, ctx) => {
    const messages = Array.isArray(event.messages) ? event.messages : [];
    const lastMessage = messages.length ? messages[messages.length - 1] : undefined;
    const result = await run("Stop", {
      session_id: event.session_id,
      turn_id: String(event.turn_id),
      stop_hook_active: event.stop_hook_active,
      last_assistant_message: contentText(
        event.last_assistant_message?.content ?? lastMessage?.content
      ),
    }, ctx);
    if (result?.decision === "block" && result?.reason) {
      return { decision: "block", reason: result.reason };
    }
  });
}
