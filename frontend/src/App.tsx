type Priority = "Critical" | "High" | "Medium";

const priorities: Array<{
  road: string;
  score: number;
  priority: Priority;
  condition: string;
  action: string;
}> = [
  {
    road: "Magado–Shakiso",
    score: 92,
    priority: "Critical",
    condition: "Very poor",
    action: "Immediate maintenance assessment",
  },
  {
    road: "Soda–Shakiso",
    score: 78,
    priority: "High",
    condition: "Poor",
    action: "Schedule priority maintenance",
  },
  {
    road: "Section 03",
    score: 61,
    priority: "High",
    condition: "Fair",
    action: "Inspect and prepare work order",
  },
];

function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">AI-RMMS</div>
          <div className="subtitle">AI-Powered Road Maintenance Management System</div>
        </div>
        <div className="ai-status">
          <span className="status-dot" />
          AI Intelligence Ready
        </div>
      </header>

      <main className="content">
        <section className="hero">
          <div>
            <p className="eyebrow">ROAD MAINTENANCE INTELLIGENCE</p>
            <h1>Turn maintenance data into decisions.</h1>
            <p className="hero-copy">
              AI-RMMS combines road condition, work orders and maintenance
              information to help maintenance teams identify what needs
              attention first.
            </p>
          </div>
          <div className="hero-card">
            <span>AI priority engine</span>
            <strong>Evidence-based</strong>
            <small>AI explains verified engineering data.</small>
          </div>
        </section>

        <section className="metrics">
          <article><span>Road sections</span><strong>—</strong><small>Connected data</small></article>
          <article><span>Critical</span><strong>1</strong><small>Needs attention</small></article>
          <article><span>High priority</span><strong>2</strong><small>Review recommended</small></article>
          <article><span>AI confidence</span><strong>90%</strong><small>Top recommendation</small></article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI ROAD INTELLIGENCE</p>
              <h2>Priority ranking</h2>
            </div>
            <button type="button">Refresh analysis</button>
          </div>

          <div className="table">
            <div className="table-row table-head">
              <span>Road section</span><span>Score</span><span>Priority</span><span>Condition</span><span>Recommended action</span>
            </div>
            {priorities.map((item) => (
              <div className="table-row" key={item.road}>
                <span className="road-name">{item.road}</span>
                <span className="score">{item.score}</span>
                <span><span className={`badge ${item.priority.toLowerCase()}`}>{item.priority}</span></span>
                <span>{item.condition}</span>
                <span>{item.action}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="assistant-panel">
          <div>
            <p className="eyebrow">AI OFFICE ASSISTANT</p>
            <h2>Ask about your maintenance office</h2>
            <p>Examples: “Which road sections require urgent attention?” or “Why is this section ranked critical?”</p>
          </div>
          <div className="question-box">Ask AI about roads, plans, work orders and documents…</div>
        </section>
      </main>
    </div>
  );
}

export default App;
