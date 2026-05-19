"use client";

import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import Editor from "@monaco-editor/react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type ValidationResult = { ok: boolean; message: string };

function extractJsonObjectText(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) return fenced[1].trim();

  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start >= 0 && end > start) return trimmed.slice(start, end + 1);
  return trimmed;
}

function normalizeGrafanaJson(raw: string): string {
  const jsonText = extractJsonObjectText(raw);
  const parsed = JSON.parse(jsonText) as Record<string, unknown>;
  const root = (parsed.dashboard && typeof parsed.dashboard === "object"
    ? (parsed.dashboard as Record<string, unknown>)
    : parsed) as Record<string, unknown>;

  if (!root.title || typeof root.title !== "string") {
    root.title = "Auto Generated Dashboard";
  }
  if (!Array.isArray(root.panels)) {
    root.panels = [];
  }
  if (typeof root.schemaVersion !== "number") {
    root.schemaVersion = 39;
  }
  if (typeof root.version !== "number") {
    root.version = 1;
  }

  return JSON.stringify(root, null, 2);
}

function validateGrafanaJson(raw: string): ValidationResult {
  try {
    if (!raw.trim()) return { ok: false, message: "No JSON generated yet." };
    const normalized = normalizeGrafanaJson(raw);
    const parsed = JSON.parse(normalized) as Record<string, unknown>;
    if (!parsed.title || typeof parsed.title !== "string") {
      return { ok: false, message: "Missing dashboard title." };
    }
    return { ok: true, message: "Schema pre-check passed." };
  } catch (error) {
    return { ok: false, message: `Invalid JSON: ${(error as Error).message}` };
  }
}

export default function HomePage() {
  const [prompt, setPrompt] = useState(
    "Create a Grafana dashboard for API error rate, p95 latency, and request traffic trend."
  );
  const [query, setQuery] = useState("");
  const [metrics, setMetrics] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [jsonOutput, setJsonOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const validation = useMemo(() => validateGrafanaJson(jsonOutput), [jsonOutput]);

  const searchMetrics = async () => {
    const res = await fetch(`${API_BASE}/api/metrics/search?q=${encodeURIComponent(query)}`);
    const data = (await res.json()) as { items: string[] };
    setMetrics(data.items || []);
  };

  const toggleMetric = (metric: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(metric) ? prev.filter((m) => m !== metric) : [...prev, metric]
    );
  };

  const runGenerate = async () => {
    setLoading(true);
    setJsonOutput("");

    try {
      const response = await fetch(`${API_BASE}/api/dashboard/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, selected_metrics: selectedMetrics })
      });

      if (!response.body) {
        throw new Error("No stream body from backend.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assembled = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const event of chunks) {
          if (!event.startsWith("data:")) continue;
          const payload = event.replace(/^data:\s*/, "").trim();
          if (!payload || payload === "[DONE]") continue;
          if (!payload.startsWith("{")) continue;

          try {
            const parsed = JSON.parse(payload);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (typeof delta === "string") {
              assembled += delta;
              try {
                setJsonOutput(normalizeGrafanaJson(assembled));
              } catch {
                setJsonOutput(assembled);
              }
            }
          } catch {
            // ignore non-json chunks
          }
        }
      }

      if (!assembled.trim()) {
        const fallback = await fetch(`${API_BASE}/api/dashboard/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, selected_metrics: selectedMetrics })
        });
        const data = (await fallback.json()) as { dashboard_json?: string; detail?: string };
        if (data.dashboard_json) {
          setJsonOutput(normalizeGrafanaJson(data.dashboard_json));
        } else {
          setJsonOutput(JSON.stringify(data, null, 2));
        }
      } else {
        setJsonOutput(normalizeGrafanaJson(assembled));
      }
    } catch (error) {
      setJsonOutput(JSON.stringify({ error: (error as Error).message }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  const copyJson = async () => {
    if (!jsonOutput) return;
    await navigator.clipboard.writeText(jsonOutput);
  };

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <motion.header
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <div className="pill mb-3">GPT-OSS-120B + Prometheus Context</div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Grafana AI Assistant</h1>
            <p className="mt-2 text-sm text-slate-300 sm:text-base">
              Generate Grafana dashboard JSON from plain language requests.
            </p>
          </div>
          <div className="glass-card flex gap-3 px-4 py-3">
            <div>
              <p className="text-xs text-slate-400">Selected Metrics</p>
              <p className="text-lg font-semibold">{selectedMetrics.length}</p>
            </div>
            <div className="h-10 w-px bg-white/10" />
            <div>
              <p className="text-xs text-slate-400">Validation</p>
              <p className={`text-sm font-semibold ${validation.ok ? "text-emerald-300" : "text-amber-300"}`}>
                {validation.ok ? "Passed" : "Pending"}
              </p>
            </div>
          </div>
        </motion.header>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <motion.section
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-5 lg:col-span-4"
          >
            <h2 className="text-lg font-semibold">Request Builder</h2>
            <p className="mt-1 text-sm text-slate-400">Send prompt and selected metric context together.</p>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="field mt-4 h-40 resize-none"
              placeholder="Describe the dashboard you want to generate"
            />

            <button onClick={runGenerate} disabled={loading} className="btn-primary mt-4 w-full">
              {loading ? "Generating..." : "Generate Dashboard JSON"}
            </button>

            <div className="mt-5">
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Prompt Metrics</p>
              <div className="max-h-40 overflow-auto rounded-xl border border-white/10 bg-black/20 p-2">
                {selectedMetrics.length === 0 && (
                  <p className="px-2 py-3 text-xs text-slate-500">No selected metrics.</p>
                )}
                <div className="flex flex-wrap gap-2">
                  {selectedMetrics.map((m) => (
                    <button
                      key={m}
                      onClick={() => toggleMetric(m)}
                      className="rounded-full border border-cyan-300/40 bg-cyan-300/10 px-2.5 py-1 text-xs text-cyan-200"
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="glass-card p-5 lg:col-span-8"
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold">Live JSON Preview</h2>
                <p className="text-sm text-slate-400">Live result preview with Monaco editor.</p>
              </div>
              <button onClick={copyJson} className="btn-ghost">One-click Copy</button>
            </div>

            <div className="h-[480px] overflow-hidden rounded-xl border border-white/10 bg-[#0b1120]">
              <Editor
                height="100%"
                defaultLanguage="json"
                value={jsonOutput}
                theme="vs-dark"
                options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on", smoothScrolling: true }}
                onChange={(value) => setJsonOutput(value ?? "")}
              />
            </div>

            <p className={`mt-3 text-sm ${validation.ok ? "text-emerald-300" : "text-amber-300"}`}>
              {validation.message}
            </p>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-5 lg:col-span-12"
          >
            <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold">Metric Search</h3>
                <p className="text-sm text-slate-400">Click metrics to inject them into prompt context.</p>
              </div>
              <div className="flex w-full gap-2 sm:w-[420px]">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="http_requests_total"
                  className="field"
                />
                <button onClick={searchMetrics} className="btn-ghost whitespace-nowrap">Search</button>
              </div>
            </div>

            <div className="flex max-h-56 flex-wrap gap-2 overflow-auto rounded-xl border border-white/10 bg-black/20 p-3">
              {metrics.length === 0 && <p className="text-sm text-slate-500">No metrics found.</p>}
              {metrics.map((m) => {
                const active = selectedMetrics.includes(m);
                return (
                  <button
                    key={m}
                    onClick={() => toggleMetric(m)}
                    className={
                      active
                        ? "rounded-full border border-cyan-300/40 bg-cyan-300/10 px-3 py-1.5 text-xs font-medium text-cyan-200"
                        : "rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/10"
                    }
                  >
                    {m}
                  </button>
                );
              })}
            </div>
          </motion.section>
        </div>
      </div>
    </main>
  );
}