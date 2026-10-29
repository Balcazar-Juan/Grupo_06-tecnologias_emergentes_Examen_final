import site from "vinext/server/fetch-handler";

type Env = {
  API_ORIGIN?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
};

const agentRun = /^\/api\/enrollment-requests\/[^/]+\/(validate|confirm)\/?$/;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) return site.fetch(request, env, ctx);

    const origin = env.API_ORIGIN || env.NEXT_PUBLIC_API_BASE_URL ||
      (url.hostname === "localhost" || url.hostname === "127.0.0.1" ? "http://localhost:8000" : "");
    if (!origin) {
      console.error(JSON.stringify({ event: "api_proxy_unconfigured", path: url.pathname }));
      return Response.json({ detail: "API_ORIGIN no está configurado en el Worker." }, { status: 503 });
    }

    const upstream = new URL(url.pathname + url.search, origin);
    try {
      const response = await fetch(new Request(upstream, request));
      if (agentRun.test(url.pathname) && response.ok) {
        try {
          const run = await response.clone().json() as {
            request_id?: string;
            run_id?: string;
            status?: string;
            handoffs?: Array<{ sender: string; receiver: string; status: string }>;
          };
          for (const handoff of run.handoffs || []) {
            console.log(JSON.stringify({
              event: "agent_handoff",
              request_id: run.request_id,
              run_id: run.run_id,
              sender: handoff.sender,
              receiver: handoff.receiver,
              status: handoff.status,
            }));
          }
          console.log(JSON.stringify({ event: "agent_run", request_id: run.request_id, run_id: run.run_id, status: run.status }));
        } catch {
          console.error(JSON.stringify({ event: "agent_run_log_error", path: url.pathname }));
        }
      }
      return response;
    } catch (error) {
      console.error(JSON.stringify({ event: "api_proxy_error", path: url.pathname, error_type: error instanceof Error ? error.name : "Unknown" }));
      return Response.json({ detail: "No se pudo contactar la API." }, { status: 502 });
    }
  },
};
