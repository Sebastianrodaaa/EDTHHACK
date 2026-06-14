/** REST control plane — scenario control + operator actions (HITL). */
import { HTTP_BASE } from "../config";
import type { OperatorActionType } from "../store";

async function post(path: string, body?: unknown) {
  try {
    const res = await fetch(`${HTTP_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return await res.json();
  } catch (err) {
    console.warn(`[api] POST ${path} failed:`, err);
    return { ok: false, error: String(err) };
  }
}

export function startScenario(scenarioId: string) {
  return post(`/scenario/${scenarioId}/start`);
}

export function resetScenario() {
  return post(`/scenario/reset`);
}

export function stopScenario() {
  return post(`/scenario/stop`);
}

export function sendOperatorAction(
  action: OperatorActionType,
  assessmentId?: string | null
) {
  return post(`/operator/action`, {
    type: "operator_action",
    action,
    assessment_id: assessmentId ?? null,
    operator_id: "op-1",
  });
}

export async function listScenarios() {
  try {
    const res = await fetch(`${HTTP_BASE}/scenarios`);
    return (await res.json()).scenarios as Array<{
      id: string;
      name: string;
      description: string;
    }>;
  } catch {
    return [];
  }
}
