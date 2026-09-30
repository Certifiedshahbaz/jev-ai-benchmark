import { useState, useEffect } from 'react';
import './App.css';

interface AnswerDetail {
  type: string;
  choice?: string;
  noul?: number;
  score?: number;
  confidence?: number;
  probabilities?: Record<string, number>;
  legend?: Record<string, string>;
}

interface RoutingDecision {
  team: string;
  priority: string;
  action: string;
  reason: string;
  confidence_factors: Record<string, any>;
  relevant_answers: Record<string, any>;
  ignored_answers: string[];
}

interface LLMBaselineResult {
  provider: string;
  model: string;
  answers: Record<string, any>;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  cost_usd: number;
  timing: {
    prep_ms: number;
    api_ms: number;
    total_ms: number;
  };
}

interface ComparisonMetrics {
  latency_delta_ms: number;
  latency_ratio: number;
  cost_delta_usd: number;
  cost_ratio: number;
  token_delta: number;
  agreement_score: number;
}

interface AnalyzeResponse {
  status: string;
  mode: string;
  question_count: number;
  model: string;
  request_id: string;
  answers: Record<string, AnswerDetail>;
  decision?: RoutingDecision;
  cost_usd: number;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens?: number;
  };
  timing: {
    prep_ms: number;
    api_ms: number;
    total_ms: number;
  };
  llm?: LLMBaselineResult;
  comparison?: ComparisonMetrics;
}

const PRESETS = [
  {
    label: "Duplicate Charge (Billing)",
    mode: "B",
    message: "I was charged twice for my order and I need the duplicate payment refunded today. I'm really frustrated because I have been waiting all morning.",
    context: {
      customer: { id: "CUS-1042", plan: "premium", lifetime_value: 1240 },
      order: { id: "ORD-8821", status: "delivered", amount: 149.99 },
      transactions: [
        { id: "TX-1001", amount: 149.99, status: "captured" },
        { id: "TX-1002", amount: 149.99, status: "captured" }
      ],
      policy: { duplicate_payment_refund: true, human_review_threshold: 0.75 }
    }
  },
  {
    label: "Late Delivery / Tracking (Orders)",
    mode: "B",
    message: "I ordered a birthday gift 6 days ago with express shipping and tracking hasn't moved in 72 hours. Is it lost? Where is my package?",
    context: {
      customer: { id: "CUS-2089", plan: "standard", lifetime_value: 320 },
      order: { id: "ORD-9430", status: "in_transit", carrier: "FedEx", tracking_id: "FX-88912" },
      policy: { shipping_delay_compensation: true }
    }
  },
  {
    label: "Account 2FA Locked",
    mode: "B",
    message: "I got a new phone and can no longer receive my 2FA authentication codes. I'm completely locked out of my account and need access urgently.",
    context: {
      customer: { id: "CUS-5033", plan: "pro", lifetime_value: 2100 },
      security: { two_factor_enabled: true, last_login: "2026-09-28" }
    }
  },
  {
    label: "Angry Customer Churn Risk",
    mode: "B",
    message: "This is the third time this week your service crashed during our team meeting. If this isn't resolved by end of day we are canceling our entire enterprise contract.",
    context: {
      customer: { id: "CUS-9901", plan: "enterprise", lifetime_value: 48000 },
      sla: { tier: "platinum", response_time_hours: 1 }
    }
  }
];

interface FieldAccuracy {
  field: string;
  correct: number;
  total: number;
  ambiguous_count?: number;
  accuracy: number;
}

interface FailedCase {
  case_id: string;
  category: string;
  message: string;
  expected: any;
  actual: any;
}

interface EngineAccuracyResult {
  model: string;
  overall_accuracy: number;
  total_evaluations: number;
  total_correct: number;
  ambiguous_matches: number;
  duration_seconds: number;
  per_field_accuracy: Record<string, FieldAccuracy>;
  failed_case_ids: Record<string, string[]>;
  failed_cases: Record<string, FailedCase[]>;
  ambiguous_cases?: Record<string, FailedCase[]>;
}

interface AccuracyBenchmarkData {
  status: string;
  total_cases: number;
  duration_seconds: number;
  results_file: string;
  jev: EngineAccuracyResult;
  llm: EngineAccuracyResult;
}

interface BenchmarkProgress {
  is_running: boolean;
  current_case: number;
  total_cases: number;
  current_case_id: string;
  percent: number;
  elapsed_seconds: number;
  phase: "idle" | "running" | "completed" | "error";
  error: string | null;
  latest_result?: AccuracyBenchmarkData | null;
}

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export default function App() {
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [mode, setMode] = useState<string>("B");
  const [message, setMessage] = useState(PRESETS[0].message);
  const [contextJson, setContextJson] = useState(JSON.stringify(PRESETS[0].context, null, 2));
  const [showContext, setShowContext] = useState(true);
  const [includeLlm, setIncludeLlm] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [backendHealth, setBackendHealth] = useState<{ status: string; model?: string; llm_model?: string } | null>(null);
  const [activeTab, setActiveTab] = useState<"comparison" | "trace" | "projections" | "accuracy" | "json">("comparison");
  const [primitiveFilter, setPrimitiveFilter] = useState<string>("all");

  const [accuracyLoading, setAccuracyLoading] = useState(false);
  const [accuracyError, setAccuracyError] = useState<string | null>(null);
  const [accuracyData, setAccuracyData] = useState<AccuracyBenchmarkData | null>(null);
  const [accuracyProgress, setAccuracyProgress] = useState<BenchmarkProgress | null>(null);
  const [expandedFields, setExpandedFields] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => res.json())
      .then(data => setBackendHealth({
        status: data.status,
        model: data.config?.jev_model,
        llm_model: data.config?.llm_model
      }))
      .catch(() => setBackendHealth({ status: "offline" }));

    fetch(`${API_BASE}/api/benchmark/accuracy/latest`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setAccuracyData(data);
      })
      .catch(() => {});
  }, []);

  const handleSelectPreset = (idx: number) => {
    setSelectedPreset(idx);
    const p = PRESETS[idx];
    setMode(p.mode);
    setMessage(p.message);
    setContextJson(JSON.stringify(p.context, null, 2));
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      let parsedContext = {};
      if (contextJson.trim()) {
        parsedContext = JSON.parse(contextJson);
      }

      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          customer_context: parsedContext,
          mode,
          include_llm: includeLlm
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${res.status}`);
      }

      const data: AnalyzeResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAccuracy = async () => {
    setAccuracyLoading(true);
    setAccuracyError(null);
    setAccuracyProgress({
      is_running: true,
      current_case: 0,
      total_cases: 49,
      current_case_id: 'initializing benchmark suite...',
      percent: 0,
      elapsed_seconds: 0,
      phase: 'running',
      error: null
    });

    try {
      // 1. Trigger non-blocking background benchmark run
      const res = await fetch(`${API_BASE}/api/benchmark/accuracy/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Benchmark start failed with status ${res.status}`);
      }

      // 2. Poll progress every 800ms
      const pollTimer = setInterval(async () => {
        try {
          const progRes = await fetch(`${API_BASE}/api/benchmark/accuracy/progress`);
          if (!progRes.ok) return;
          const prog: BenchmarkProgress = await progRes.json();
          setAccuracyProgress(prog);

          if (prog.phase === 'completed') {
            clearInterval(pollTimer);
            setAccuracyLoading(false);
            if (prog.latest_result) {
              setAccuracyData(prog.latest_result);
            } else {
              const latestRes = await fetch(`${API_BASE}/api/benchmark/accuracy/latest`);
              if (latestRes.ok) {
                const latestData: AccuracyBenchmarkData = await latestRes.json();
                setAccuracyData(latestData);
              }
            }
          } else if (prog.phase === 'error') {
            clearInterval(pollTimer);
            setAccuracyLoading(false);
            setAccuracyError(prog.error || 'Benchmark run encountered an error');
          }
        } catch {
          // Ignore transient poll network errors
        }
      }, 800);
    } catch (err: any) {
      setAccuracyError(err.message || 'Failed to start accuracy benchmark');
      setAccuracyLoading(false);
    }
  };

  const toggleFieldExpand = (field: string) => {
    setExpandedFields(prev => ({
      ...prev,
      [field]: prev[field] === false ? true : false,
    }));
  };

  const filteredAnswers = Object.entries(result?.answers || {}).filter(([_, ans]) => {
    if (primitiveFilter === "all") return true;
    return ans.type === primitiveFilter;
  });

  // Projection calculations
  const calculateProjections = (volume: number) => {
    const jevCost = (result?.cost_usd || 0) * volume;
    const llmCost = (result?.llm?.cost_usd || 0) * volume;
    const savings = llmCost - jevCost;
    return { volume, jevCost, llmCost, savings };
  };

  const renderAccuracyTab = () => (
    <div className="accuracy-container">
      {/* Accuracy Header & Trigger Card */}
      <div className="accuracy-header-card">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '18px' }}>🎯</span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>
              Dual Ground-Truth Accuracy Benchmark: JEV vs. LLM Baseline
            </h3>
            <span className="badge badge-purple" style={{ fontSize: '11px' }}>Mode B (15 Questions)</span>
          </div>
          <p style={{ margin: 0, fontSize: '12.5px', color: 'var(--text-muted)', maxWidth: '650px' }}>
            Evaluates 49 manually labeled real-world support cases against both TypeSafe JEV System One and the conventional LLM baseline (Groq) on identical ground-truth targets. Measures exact Choice categories, Noul probabilities (&ge; 0.5), and continuous Score tolerance (&le; 0.5).
          </p>
        </div>

        <button
          className="btn-primary"
          disabled={accuracyLoading}
          onClick={handleRunAccuracy}
          style={{
            background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
            minWidth: '280px',
            boxShadow: '0 4px 14px rgba(124, 58, 237, 0.35)',
          }}
        >
          {accuracyLoading ? (
            <>
              <span className="spinner" />
              <span>Running Dual Suite (49 cases)...</span>
            </>
          ) : (
            <>
              <span>⚡ Run Dual Accuracy Benchmark (49 cases)</span>
            </>
          )}
        </button>
      </div>

      {accuracyError && (
        <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', color: '#fb7185', fontSize: '13px' }}>
          <strong>Benchmark Error:</strong> {accuracyError}
        </div>
      )}

      {accuracyLoading && (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '12px', padding: '24px 28px', boxShadow: '0 8px 30px rgba(0,0,0,0.25)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2.5px', borderTopColor: '#a855f7' }} />
              <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-main)' }}>
                Processing Case {accuracyProgress?.current_case || 0} of {accuracyProgress?.total_cases || 49}
              </h4>
            </div>
            <span className="badge badge-purple" style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', padding: '4px 10px' }}>
              {accuracyProgress?.percent ? `${accuracyProgress.percent.toFixed(1)}%` : '0.0%'}
            </span>
          </div>

          {/* Real Animated Progress Bar */}
          <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '6px', overflow: 'hidden', marginBottom: '14px' }}>
            <div
              style={{
                width: `${Math.max(2, accuracyProgress?.percent || 0)}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #7c3aed, #3b82f6)',
                transition: 'width 0.4s ease-out',
                borderRadius: '6px'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12.5px', color: 'var(--text-muted)' }}>
            <span>
              Active Case: <strong style={{ color: 'var(--accent-blue)', fontFamily: 'JetBrains Mono' }}>{accuracyProgress?.current_case_id || 'initializing...'}</strong>
            </span>
            <span>
              Elapsed: <strong style={{ color: 'var(--text-main)', fontFamily: 'JetBrains Mono' }}>{accuracyProgress?.elapsed_seconds || 0}s</strong> (Hard timeout: 180s)
            </span>
          </div>
          <div style={{ marginTop: '8px', fontSize: '11.5px', color: 'var(--text-muted)', opacity: 0.8 }}>
            Running sequential evaluations with token-bucket rate pacing for Groq and concurrent JEV decision scoring.
          </div>
        </div>
      )}

      {accuracyData && (
        <>
          {/* KPI Dual Cards: JEV vs LLM Overall Accuracy */}
          <div className="accuracy-hero-dual">
            {/* JEV Card */}
            <div className="accuracy-stat-box" style={{ borderLeft: '4px solid #3b82f6', background: 'linear-gradient(180deg, #131d2e 0%, var(--bg-card) 100%)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="comp-badge-jev" style={{ fontSize: '12px', padding: '3px 8px' }}>JEV System One</span>
                <span style={{ fontSize: '12px', color: 'var(--accent-blue)', fontFamily: 'JetBrains Mono' }}>
                  {accuracyData.jev.model}
                </span>
              </div>
              <div className="stat-val" style={{ fontSize: '32px', color: '#34d399', margin: '8px 0 2px 0' }}>
                {accuracyData.jev.overall_accuracy.toFixed(1)}%
              </div>
              <span className="stat-sub" style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
                {accuracyData.jev.total_correct} / {accuracyData.jev.total_evaluations} correct expected fields
              </span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '10px', fontSize: '11.5px', color: 'var(--text-faint)' }}>
                <span>⏱ Total API time: {accuracyData.jev.duration_seconds}s</span>
                {accuracyData.jev.ambiguous_matches > 0 && (
                  <span>• 🎯 {accuracyData.jev.ambiguous_matches} multi-valid accepted</span>
                )}
              </div>
            </div>

            {/* LLM Card */}
            <div className="accuracy-stat-box" style={{ borderLeft: '4px solid #f59e0b', background: 'linear-gradient(180deg, #261f18 0%, var(--bg-card) 100%)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="comp-badge-llm" style={{ fontSize: '12px', padding: '3px 8px' }}>Conventional LLM Baseline</span>
                <span style={{ fontSize: '12px', color: '#fbbf24', fontFamily: 'JetBrains Mono' }}>
                  {accuracyData.llm.model}
                </span>
              </div>
              <div className="stat-val" style={{ fontSize: '32px', color: '#fbbf24', margin: '8px 0 2px 0' }}>
                {accuracyData.llm.overall_accuracy.toFixed(1)}%
              </div>
              <span className="stat-sub" style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
                {accuracyData.llm.total_correct} / {accuracyData.llm.total_evaluations} correct expected fields
              </span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '10px', fontSize: '11.5px', color: 'var(--text-faint)' }}>
                <span>⏱ Total API time: {accuracyData.llm.duration_seconds}s</span>
                {accuracyData.llm.ambiguous_matches > 0 && (
                  <span>• 🎯 {accuracyData.llm.ambiguous_matches} multi-valid accepted</span>
                )}
              </div>
            </div>
          </div>

          {/* Comparison Callout Banner */}
          <div className="accuracy-banner-dual">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Overall Accuracy Winner:</span>
              {accuracyData.jev.overall_accuracy > accuracyData.llm.overall_accuracy ? (
                <span className="advantage-badge" style={{ fontSize: '12px', padding: '4px 8px' }}>
                  🏆 JEV leads by +{(accuracyData.jev.overall_accuracy - accuracyData.llm.overall_accuracy).toFixed(1)}%
                </span>
              ) : accuracyData.llm.overall_accuracy > accuracyData.jev.overall_accuracy ? (
                <span className="badge badge-amber" style={{ fontSize: '12px', padding: '4px 8px' }}>
                  🏆 LLM leads by +{(accuracyData.llm.overall_accuracy - accuracyData.jev.overall_accuracy).toFixed(1)}%
                </span>
              ) : (
                <span className="badge badge-purple" style={{ fontSize: '12px', padding: '4px 8px' }}>
                  🤝 Exact Tie ({accuracyData.jev.overall_accuracy.toFixed(1)}%)
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span>⚡ JEV is {(accuracyData.llm.duration_seconds / Math.max(accuracyData.jev.duration_seconds, 0.1)).toFixed(1)}x faster</span>
              <span>📦 {accuracyData.total_cases} curated cases (98 API calls in {accuracyData.duration_seconds.toFixed(1)}s)</span>
              <span className="badge" style={{ fontSize: '11px' }} title={accuracyData.results_file}>
                📄 {accuracyData.results_file.split('/').pop()}
              </span>
            </div>
          </div>

          {/* Per-Field Accuracy Table (Side-by-Side Comparison) */}
          <div className="accuracy-table-card">
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Side-by-Side Per-Field Decision Accuracy
                </span>
                <span style={{ marginLeft: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  (JEV System One vs Conventional LLM on identical ground truth)
                </span>
              </div>
              <span className="badge badge-blue">
                {Object.keys(accuracyData.jev.per_field_accuracy).length} Evaluated Questions
              </span>
            </div>

            <table className="accuracy-table">
              <thead>
                <tr>
                  <th>Question Field</th>
                  <th>Type</th>
                  <th style={{ width: '220px' }}>JEV Accuracy</th>
                  <th style={{ width: '220px' }}>LLM Accuracy</th>
                  <th>Winner / Delta</th>
                  <th>Inspect Discrepancies</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(accuracyData.jev.per_field_accuracy)
                  .map(field => {
                    const jItem = accuracyData.jev.per_field_accuracy[field];
                    const lItem = accuracyData.llm.per_field_accuracy[field] || { field, correct: 0, total: jItem.total, accuracy: 0 };
                    return { field, jItem, lItem };
                  })
                  .sort((a, b) => a.jItem.accuracy - b.jItem.accuracy)
                  .map(({ field, jItem, lItem }) => {
                    const jFailures = accuracyData.jev.failed_cases[field] || [];
                    const lFailures = accuracyData.llm.failed_cases[field] || [];
                    const totalFailures = jFailures.length + lFailures.length;
                    const isExpanded = !!expandedFields[field];

                    const delta = jItem.accuracy - lItem.accuracy;
                    const jColor = jItem.accuracy >= 90 ? '#10b981' : jItem.accuracy >= 70 ? '#f59e0b' : '#ef4444';
                    const lColor = lItem.accuracy >= 90 ? '#10b981' : lItem.accuracy >= 70 ? '#f59e0b' : '#ef4444';

                    const qType = ['department', 'intent', 'issue_type'].includes(field)
                      ? 'choice'
                      : ['urgency', 'frustration', 'churn_risk', 'customer_priority'].includes(field)
                      ? 'score'
                      : 'noul';

                    return (
                      <tr key={field}>
                        <td>
                          <strong style={{ color: 'var(--text-main)' }}>{field}</strong>
                        </td>
                        <td>
                          <span className={`primitive-tag tag-${qType}`}>{qType}</span>
                        </td>
                        <td>
                          <div className="accuracy-bar-container">
                            <div className="accuracy-bar-track">
                              <div className="accuracy-bar-fill" style={{ width: `${Math.max(jItem.accuracy, 2)}%`, background: jColor }} />
                            </div>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: jColor, minWidth: '45px' }}>
                              {jItem.accuracy.toFixed(1)}%
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>({jItem.correct}/{jItem.total})</span>
                          </div>
                        </td>
                        <td>
                          <div className="accuracy-bar-container">
                            <div className="accuracy-bar-track">
                              <div className="accuracy-bar-fill" style={{ width: `${Math.max(lItem.accuracy, 2)}%`, background: lColor }} />
                            </div>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: lColor, minWidth: '45px' }}>
                              {lItem.accuracy.toFixed(1)}%
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>({lItem.correct}/{lItem.total})</span>
                          </div>
                        </td>
                        <td>
                          {delta > 0 ? (
                            <span className="match-pill-yes" style={{ fontSize: '11px' }}>
                              JEV +{delta.toFixed(1)}%
                            </span>
                          ) : delta < 0 ? (
                            <span className="badge badge-amber" style={{ fontSize: '11px' }}>
                              LLM +{Math.abs(delta).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="badge" style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                              TIE
                            </span>
                          )}
                        </td>
                        <td>
                          {totalFailures > 0 ? (
                            <button
                              className="preset-chip"
                              onClick={() => toggleFieldExpand(field)}
                              style={{
                                borderColor: isExpanded ? '#8b5cf6' : 'rgba(239, 68, 68, 0.4)',
                                color: isExpanded ? '#c084fc' : '#f87171',
                                fontSize: '11px',
                              }}
                            >
                              {isExpanded ? 'Hide' : 'Inspect'} (JEV: {jFailures.length} | LLM: {lFailures.length})
                            </button>
                          ) : (
                            <span style={{ color: '#10b981', fontSize: '12px' }}>✓ Both 100%</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>

          {/* Expandable Section for Inspecting Discrepancies */}
          <div style={{ marginTop: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h4 style={{ margin: 0, fontSize: '13px', color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Side-by-Side Case Discrepancy Inspector
              </h4>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Compare exact customer messages against ground truth, JEV inference, and LLM output
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.keys(accuracyData.jev.per_field_accuracy)
                .filter(field => {
                  const jF = (accuracyData.jev.failed_cases[field] || []).length;
                  const lF = (accuracyData.llm.failed_cases[field] || []).length;
                  return (jF + lF) > 0;
                })
                .map(field => {
                  const jFailures = accuracyData.jev.failed_cases[field] || [];
                  const lFailures = accuracyData.llm.failed_cases[field] || [];
                  const isExpanded = expandedFields[field] !== false;

                  const allFailedCaseIds = Array.from(new Set([
                    ...jFailures.map(f => f.case_id),
                    ...lFailures.map(f => f.case_id),
                  ]));

                  return (
                    <div key={field} style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '10px', overflow: 'hidden' }}>
                      <div
                        style={{
                          padding: '12px 18px',
                          background: 'var(--bg-card)',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                        onClick={() => toggleFieldExpand(field)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <strong style={{ fontSize: '13px', color: 'var(--text-main)', fontFamily: 'JetBrains Mono' }}>
                            {field}
                          </strong>
                          <span className="badge badge-purple" style={{ fontSize: '11px', padding: '2px 7px' }}>
                            JEV: {accuracyData.jev.per_field_accuracy[field]?.accuracy.toFixed(1)}% ({jFailures.length} failed)
                          </span>
                          <span className="badge badge-amber" style={{ fontSize: '11px', padding: '2px 7px' }}>
                            LLM: {accuracyData.llm.per_field_accuracy[field]?.accuracy.toFixed(1)}% ({lFailures.length} failed)
                          </span>
                        </div>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {isExpanded ? '▲ Collapse' : '▼ Expand'}
                        </span>
                      </div>

                      {isExpanded && (
                        <div style={{ padding: '14px 18px' }}>
                          {allFailedCaseIds.map(cId => {
                            const jCase = jFailures.find(f => f.case_id === cId);
                            const lCase = lFailures.find(f => f.case_id === cId);
                            const refCase = jCase || lCase;
                            if (!refCase) return null;

                            const jPassed = !jCase;
                            const lPassed = !lCase;

                            return (
                              <div key={cId} className="failure-card">
                                <div className="failure-header">
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span className="team-badge" style={{ fontSize: '12px', padding: '2px 8px' }}>
                                      {cId}
                                    </span>
                                    <span className="action-pill" style={{ fontSize: '10px' }}>
                                      Category: {refCase.category}
                                    </span>
                                  </div>
                                  <div style={{ display: 'flex', gap: '6px' }}>
                                    <span className={jPassed ? "match-pill-yes" : "match-pill-no"}>
                                      JEV: {jPassed ? "PASS" : "DIVERGED"}
                                    </span>
                                    <span className={lPassed ? "match-pill-yes" : "match-pill-no"}>
                                      LLM: {lPassed ? "PASS" : "DIVERGED"}
                                    </span>
                                  </div>
                                </div>

                                <div className="failure-msg-box">
                                  <strong>Message:</strong> "{refCase.message}"
                                </div>

                                <div className="failure-diff-grid-3">
                                  <div className="failure-diff-box failure-diff-expected">
                                    <span style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', marginBottom: '2px', opacity: 0.8 }}>
                                      Expected Ground Truth:
                                    </span>
                                    <strong>{String(refCase.expected)}</strong>
                                  </div>
                                  <div className={`failure-diff-box ${jPassed ? 'failure-diff-pass' : 'failure-diff-actual'}`}>
                                    <span style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', marginBottom: '2px', opacity: 0.8 }}>
                                      JEV Actual Output:
                                    </span>
                                    <strong>{jCase ? String(jCase.actual) : "✓ MATCH (Passed)"}</strong>
                                  </div>
                                  <div className={`failure-diff-box ${lPassed ? 'failure-diff-pass' : 'failure-diff-actual'}`}>
                                    <span style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', marginBottom: '2px', opacity: 0.8 }}>
                                      LLM Actual Output:
                                    </span>
                                    <strong>{lCase ? String(lCase.actual) : "✓ MATCH (Passed)"}</strong>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>
        </>
      )}
    </div>
  );

  return (
    <div className="lab-container">
      {/* Header */}
      <header className="lab-header">
        <div className="brand-section">
          <span className="brand-badge">SERALI</span>
          <div>
            <h1 className="brand-title">JEV WORKFORCE LAB</h1>
            <p className="brand-subtitle">Benchmark Laboratory: JEV System One vs. Conventional LLM Baseline</p>
          </div>
        </div>

        <div className="header-status">
          <div className="badge badge-green">
            <span className="dot-green"></span>
            Backend: {backendHealth?.status === "healthy" ? "Online" : "Connecting..."}
          </div>
          <div className="badge badge-purple">
            JEV: {result?.model || backendHealth?.model || "jev-1.13.0"}
          </div>
          <div className="badge badge-amber">
            LLM: {result?.llm?.model || backendHealth?.llm_model || "unknown"}
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="lab-main">
        {/* Left Control Sidebar */}
        <aside className="lab-sidebar">
          {/* Presets */}
          <div>
            <div className="section-label">Test Case Presets</div>
            <div className="preset-buttons">
              {PRESETS.map((p, i) => (
                <button
                  key={p.label}
                  className={`preset-chip ${selectedPreset === i ? 'active' : ''}`}
                  onClick={() => handleSelectPreset(i)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Mode Selector */}
          <div>
            <div className="section-label">
              <span>Question Fan-Out Mode</span>
              <span style={{ color: 'var(--accent-blue)', textTransform: 'none' }}>
                {mode === 'A' ? '5 questions' : mode === 'B' ? '15 questions' : mode === 'C' ? '25 questions' : mode === 'D' ? '50 questions' : '100 questions'}
              </span>
            </div>
            <div className="mode-selector">
              {['A', 'B', 'C', 'D', 'E'].map(m => (
                <button
                  key={m}
                  className={`mode-tab ${mode === m ? 'active' : ''}`}
                  onClick={() => setMode(m)}
                >
                  Mode {m}
                </button>
              ))}
            </div>
          </div>

          {/* Customer Message */}
          <div>
            <div className="section-label">Customer Message</div>
            <textarea
              className="text-input-field"
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Enter incoming customer message..."
            />
          </div>

          {/* Customer Context JSON */}
          <div>
            <div className="section-label">
              <span>Structured Context (Order, Transactions, Policy)</span>
              <button
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '11px' }}
                onClick={() => setShowContext(!showContext)}
              >
                {showContext ? 'Hide' : 'Show'}
              </button>
            </div>
            {showContext && (
              <textarea
                className="context-editor"
                value={contextJson}
                onChange={e => setContextJson(e.target.value)}
                spellCheck={false}
              />
            )}
          </div>

          {/* LLM Benchmark Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0' }}>
            <input
              type="checkbox"
              id="llmToggle"
              checked={includeLlm}
              onChange={e => setIncludeLlm(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="llmToggle" style={{ fontSize: '12.5px', color: 'var(--text-muted)', cursor: 'pointer' }}>
              Benchmark side-by-side with LLM baseline (Groq)
            </label>
          </div>

          {/* Action Button */}
          <button
            className="btn-primary"
            onClick={handleAnalyze}
            disabled={loading || !message.trim()}
          >
            {loading ? 'Executing Dual Benchmark...' : `Benchmark JEV vs. LLM (Mode ${mode})`}
          </button>

          {error && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', color: '#fb7185', fontSize: '12px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </aside>

        {/* Right Live Results Area */}
        <section className="lab-content">
          {result ? (
            <>
              {/* Head-to-Head Comparison Hero Card */}
              {result.llm && result.comparison && (
                <div className="comparison-hero">
                  {/* JEV Column */}
                  <div className="comparison-col">
                    <div className="comp-header">
                      <span className="comp-title">
                        <span className="comp-badge-jev">JEV</span>
                        TypeSafe System One
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--accent-blue)', fontFamily: 'JetBrains Mono' }}>
                        {result.model}
                      </span>
                    </div>

                    <div className="comp-stats-grid">
                      <div className="comp-stat-cell">
                        <span className="stat-label">Total Latency</span>
                        <div className="stat-val" style={{ color: 'var(--accent-cyan)' }}>
                          {result.timing.total_ms.toFixed(1)} ms
                        </div>
                        <span className="stat-sub">API: {result.timing.api_ms.toFixed(1)} ms</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Request Cost</span>
                        <div className="stat-val" style={{ color: 'var(--accent-emerald)' }}>
                          ${result.cost_usd.toFixed(6)}
                        </div>
                        <span className="stat-sub">$0.042 / 1M tokens</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Input Tokens</span>
                        <div className="stat-val">{result.usage.input_tokens}</div>
                        <span className="stat-sub">Output: {result.usage.output_tokens} (Free)</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Architecture</span>
                        <div className="stat-val" style={{ fontSize: '14px', color: '#60a5fa' }}>
                          Speculative
                        </div>
                        <span className="stat-sub">Single request fan-out</span>
                      </div>
                    </div>
                  </div>

                  {/* LLM Column */}
                  <div className="comparison-col">
                    <div className="comp-header">
                      <span className="comp-title">
                        <span className="comp-badge-llm">LLM</span>
                        Conventional Baseline ({result.llm.provider.toUpperCase()})
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--accent-amber)', fontFamily: 'JetBrains Mono' }}>
                        {result.llm.model}
                      </span>
                    </div>

                    <div className="comp-stats-grid">
                      <div className="comp-stat-cell">
                        <span className="stat-label">Total Latency</span>
                        <div className="stat-val" style={{ color: '#f87171' }}>
                          {result.llm.timing.total_ms.toFixed(1)} ms
                        </div>
                        <span className="stat-sub">API: {result.llm.timing.api_ms.toFixed(1)} ms</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Request Cost</span>
                        <div className="stat-val" style={{ color: '#fbbf24' }}>
                          ${result.llm.cost_usd.toFixed(6)}
                        </div>
                        <span className="stat-sub">In: $0.59 | Out: $0.79 /1M</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Total Tokens</span>
                        <div className="stat-val">{result.llm.usage.total_tokens}</div>
                        <span className="stat-sub">In: {result.llm.usage.input_tokens} | Out: {result.llm.usage.output_tokens}</span>
                      </div>

                      <div className="comp-stat-cell">
                        <span className="stat-label">Architecture</span>
                        <div className="stat-val" style={{ fontSize: '14px', color: '#fbbf24' }}>
                          Autoregressive
                        </div>
                        <span className="stat-sub">JSON mode completion</span>
                      </div>
                    </div>
                  </div>

                  {/* Advantage Bottom Bar */}
                  <div className="head-to-head-banner">
                    <div className="head-item">
                      <span>Speed Advantage:</span>
                      <span className="advantage-badge">
                        JEV is {result.comparison.latency_ratio.toFixed(1)}x faster ({result.comparison.latency_delta_ms > 0 ? `${result.comparison.latency_delta_ms.toFixed(0)}ms faster` : 'slower'})
                      </span>
                    </div>
                    <div className="head-item">
                      <span>Cost Advantage:</span>
                      <span className="advantage-badge">
                        JEV is {result.comparison.cost_ratio.toFixed(1)}x cheaper
                      </span>
                    </div>
                    <div className="head-item">
                      <span>Decision Agreement:</span>
                      <span className="badge badge-purple" style={{ padding: '2px 7px' }}>
                        {(result.comparison.agreement_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Deterministic Python Routing Card */}
              {result.decision && (
                <div className="decision-banner">
                  <div className="decision-header">
                    <div className="decision-team-title">
                      <span style={{ fontSize: '11px', color: 'var(--text-faint)', textTransform: 'uppercase', fontWeight: 600 }}>
                        Deterministic Python Route:
                      </span>
                      <span className="team-badge">{result.decision.team}</span>
                      <span className="action-pill">{result.decision.action}</span>
                    </div>
                    <span className={`badge ${result.decision.priority === 'urgent' ? 'badge-purple' : 'badge-blue'}`}>
                      Priority: {result.decision.priority.toUpperCase()}
                    </span>
                  </div>

                  <p className="decision-reason">
                    <strong>Routing Rationale:</strong> {result.decision.reason}
                  </p>

                  <div className="signal-tags">
                    <span style={{ fontSize: '11px', color: 'var(--text-faint)', marginRight: '4px' }}>
                      Relevant Signals Utilized:
                    </span>
                    {Object.entries(result.decision.relevant_answers).map(([k, v]) => (
                      <span key={k} className="signal-tag signal-relevant">
                        {k}: {typeof v === 'number' ? v.toFixed(2) : String(v)}
                      </span>
                    ))}
                    {result.decision.ignored_answers.length > 0 && (
                      <span className="signal-tag signal-ignored" title={`Ignored speculative questions: ${result.decision.ignored_answers.join(', ')}`}>
                        +{result.decision.ignored_answers.length} speculative signals ignored
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Tab Navigation */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className={`badge ${activeTab === 'comparison' ? 'badge-blue' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveTab('comparison')}
                  >
                    Head-to-Head Answers
                  </button>
                  <button
                    className={`badge ${activeTab === 'trace' ? 'badge-blue' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveTab('trace')}
                  >
                    JEV Decision Trace ({result.question_count})
                  </button>
                  <button
                    className={`badge ${activeTab === 'projections' ? 'badge-blue' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveTab('projections')}
                  >
                    Volume Cost Projections
                  </button>
                  <button
                    className={`badge ${activeTab === 'accuracy' ? 'badge-purple' : ''}`}
                    style={{ cursor: 'pointer', fontWeight: 600 }}
                    onClick={() => setActiveTab('accuracy')}
                  >
                    🎯 Accuracy Benchmark ({accuracyData ? `J: ${accuracyData.jev?.overall_accuracy}% | L: ${accuracyData.llm?.overall_accuracy}%` : '49 cases'})
                  </button>
                  <button
                    className={`badge ${activeTab === 'json' ? 'badge-blue' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveTab('json')}
                  >
                    Raw API Response
                  </button>
                </div>

                {activeTab === 'trace' && (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {['all', 'choice', 'noul', 'score'].map(filter => (
                      <button
                        key={filter}
                        className={`preset-chip ${primitiveFilter === filter ? 'active' : ''}`}
                        onClick={() => setPrimitiveFilter(filter)}
                      >
                        {filter.toUpperCase()}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* TAB 1: Head-to-Head Comparison Table */}
              {activeTab === 'comparison' && result.llm && (
                <div className="table-view-card">
                  <table className="comp-table">
                    <thead>
                      <tr>
                        <th>Decision Field</th>
                        <th>Primitive</th>
                        <th>JEV Decision</th>
                        <th>JEV Confidence</th>
                        <th>LLM Baseline Decision</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(result.answers).map(([qKey, jAns]) => {
                        const lAns = result.llm?.answers?.[qKey];
                        const jVal = jAns.choice ?? (jAns.noul !== undefined ? `${(jAns.noul > 0.5 ? 'YES' : 'NO')} (${jAns.noul.toFixed(2)})` : jAns.score?.toFixed(2));

                        let isMatch = false;
                        if (lAns !== undefined) {
                          if (jAns.type === 'choice' && typeof lAns === 'string') {
                            isMatch = jAns.choice?.toLowerCase() === lAns.toLowerCase();
                          } else if (jAns.type === 'noul') {
                            const jBool = (jAns.noul ?? 0) >= 0.5;
                            const lBool = Boolean(lAns);
                            isMatch = jBool === lBool;
                          } else if (jAns.type === 'score' && typeof lAns === 'number') {
                            isMatch = Math.abs((jAns.score ?? 0) - lAns) <= 0.6;
                          }
                        }

                        return (
                          <tr key={qKey}>
                            <td style={{ color: 'var(--text-main)', fontWeight: 600 }}>{qKey}</td>
                            <td>
                              <span className={`primitive-tag tag-${jAns.type}`}>{jAns.type}</span>
                            </td>
                            <td style={{ color: '#93c5fd' }}>{String(jVal)}</td>
                            <td style={{ color: 'var(--text-muted)' }}>
                              {jAns.confidence !== undefined ? `${(jAns.confidence * 100).toFixed(0)}%` : '—'}
                            </td>
                            <td style={{ color: '#fde68a' }}>
                              {lAns !== undefined ? String(lAns) : <span style={{ color: '#64748b' }}>Not generated</span>}
                            </td>
                            <td>
                              {lAns !== undefined ? (
                                isMatch ? (
                                  <span className="match-pill-yes">MATCH</span>
                                ) : (
                                  <span className="match-pill-no">DIVERGES</span>
                                )
                              ) : (
                                <span style={{ color: '#64748b' }}>—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* TAB 2: Full JEV Decision Trace Cards */}
              {activeTab === 'trace' && (
                <div className="trace-grid">
                  {filteredAnswers.map(([qKey, ans]) => (
                    <div key={qKey} className="trace-card">
                      <div className="trace-card-header">
                        <span className="question-key">{qKey}</span>
                        <span className={`primitive-tag tag-${ans.type}`}>
                          {ans.type}
                        </span>
                      </div>

                      {/* Choice rendering */}
                      {ans.type === 'choice' && (
                        <div>
                          <div className="answer-lead">
                            <span className="answer-value">{ans.choice}</span>
                            {ans.confidence !== undefined && (
                              <span className="confidence-indicator">
                                Conf: {(ans.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {ans.probabilities && (
                            <div className="prob-dist-list" style={{ marginTop: '10px' }}>
                              {Object.entries(ans.probabilities).map(([opt, prob]) => (
                                <div key={opt} className="prob-row">
                                  <span className="prob-label">{opt}</span>
                                  <div className="prob-bar-track">
                                    <div
                                      className={`prob-bar-fill ${opt === ans.choice ? 'winner' : ''}`}
                                      style={{ width: `${Math.round(prob * 100)}%` }}
                                    />
                                  </div>
                                  <span className="prob-val">{(prob * 100).toFixed(0)}%</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Noul rendering */}
                      {ans.type === 'noul' && (
                        <div>
                          <div className="answer-lead">
                            <span className="answer-value" style={{ color: (ans.noul ?? 0) > 0.5 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                              {(ans.noul ?? 0) > 0.5 ? 'YES' : 'NO'} ({(ans.noul ?? 0).toFixed(2)})
                            </span>
                            <span className="confidence-indicator">
                              Certainty: {(Math.abs((ans.noul ?? 0.5) - 0.5) * 200).toFixed(0)}%
                            </span>
                          </div>
                          <div className="prob-bar-track" style={{ marginTop: '10px' }}>
                            <div
                              className="prob-bar-fill winner"
                              style={{ width: `${Math.round((ans.noul ?? 0) * 100)}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Score rendering */}
                      {ans.type === 'score' && (
                        <div>
                          <div className="answer-lead">
                            <span className="answer-value">Score: {ans.score?.toFixed(2)}</span>
                            {ans.confidence !== undefined && (
                              <span className="confidence-indicator">
                                Conf: {(ans.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {ans.legend && (
                            <div className="prob-dist-list" style={{ marginTop: '10px' }}>
                              {Object.entries(ans.legend).map(([val, desc]) => (
                                <div key={val} className="prob-row">
                                  <span className="prob-label" title={desc}>{val}: {desc}</span>
                                  <div className="prob-bar-track">
                                    <div
                                      className="prob-bar-fill"
                                      style={{ width: `${((ans.probabilities?.[val] ?? 0) * 100)}%` }}
                                    />
                                  </div>
                                  <span className="prob-val">
                                    {((ans.probabilities?.[val] ?? 0) * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 3: Volume Cost Projections */}
              {activeTab === 'projections' && (
                <div className="projections-card">
                  <h3 style={{ fontSize: '15px', color: 'var(--text-main)', marginBottom: '4px' }}>
                    Volume Cost Scaling Projection
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Projected operational expenditure comparing TypeSafe JEV ($0.042/1M input) against Conventional LLM at scale.
                  </p>

                  <table className="proj-table">
                    <thead>
                      <tr>
                        <th>Request Volume</th>
                        <th>JEV Total Cost</th>
                        <th>LLM Total Cost</th>
                        <th>Projected Cost Savings</th>
                        <th>Cost Ratio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[1000, 10000, 100000, 1000000].map(vol => {
                        const proj = calculateProjections(vol);
                        return (
                          <tr key={vol}>
                            <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{vol.toLocaleString()} reqs</td>
                            <td style={{ color: 'var(--accent-emerald)' }}>${proj.jevCost.toFixed(3)}</td>
                            <td style={{ color: '#fbbf24' }}>${proj.llmCost.toFixed(3)}</td>
                            <td style={{ color: 'var(--accent-cyan)' }}>${proj.savings.toFixed(3)} saved</td>
                            <td>
                              <span className="advantage-badge">
                                {result.comparison?.cost_ratio ? `${result.comparison.cost_ratio.toFixed(1)}x cheaper` : '—'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* TAB 4: Raw JSON Inspector */}
              {activeTab === 'json' && (
                <pre style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)', color: '#38bdf8', fontSize: '12px', overflowX: 'auto' }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              )}

              {/* TAB 5: Accuracy Benchmark */}
              {activeTab === 'accuracy' && renderAccuracyTab()}
            </>
          ) : activeTab === 'accuracy' ? (
            <>
              {/* Tab Navigation when no single ticket benchmark result is loaded */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="badge"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveTab('comparison')}
                  >
                    ← Back to Single Ticket Benchmark
                  </button>
                  <button
                    className="badge badge-purple"
                    style={{ cursor: 'pointer', fontWeight: 600 }}
                    onClick={() => setActiveTab('accuracy')}
                  >
                    🎯 Accuracy Benchmark ({accuracyData ? `J: ${accuracyData.jev?.overall_accuracy}% | L: ${accuracyData.llm?.overall_accuracy}%` : '49 cases'})
                  </button>
                </div>
              </div>
              {renderAccuracyTab()}
            </>
          ) : (
            <div className="empty-state">
              <div style={{ fontSize: '32px' }}>⚡</div>
              <h3 style={{ color: 'var(--text-main)', fontSize: '16px' }}>Ready for Dual Benchmark</h3>
              <p style={{ maxWidth: '440px', fontSize: '13px' }}>
                Click <strong>"Benchmark JEV vs. LLM"</strong> on the left to execute both TypeSafe JEV and the Groq LLM baseline simultaneously and compare speed, cost, and decision agreement side-by-side.
              </p>
              <div style={{ marginTop: '14px' }}>
                <button
                  className="preset-chip"
                  style={{
                    background: 'rgba(124, 58, 237, 0.15)',
                    color: '#c084fc',
                    borderColor: 'rgba(124, 58, 237, 0.4)',
                    padding: '8px 16px',
                    fontSize: '13px',
                    fontWeight: 600,
                  }}
                  onClick={() => setActiveTab('accuracy')}
                >
                  🎯 Or Run Accuracy Benchmark on Curated Dataset (49 Cases) →
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
