import "./RoadAssetDashboard.css";

export type RoadAssetMetric = { label: string; value: string | number; unit?: string };

type Props = {
  metrics: RoadAssetMetric[];
  loading: boolean;
  error: string;
  onRefresh: () => void;
};

const shortcuts: { id: string; title: string; description: string; icon: string; tag: string; tone: string }[] = [
  { id: "module-road-inventory", title: "Road inventory", description: "Maintain the official road network, classifications, surfaces and lengths.", icon: "↗", tag: "NETWORK", tone: "blue" },
  { id: "module-road-asset-register", title: "Road asset register", description: "Manage bridges, culverts, drainage, signs and roadside infrastructure.", icon: "◈", tag: "ASSETS", tone: "teal" },
  { id: "module-gis-asset-map", title: "GIS asset map", description: "Explore verified GPS-located assets, condition and criticality.", icon: "⌖", tag: "SPATIAL", tone: "violet" },
  { id: "module-sections-and-chainage", title: "Sections & chainage", description: "Review road sections, chainage limits and condition ratings.", icon: "⇄", tag: "SEGMENTATION", tone: "slate" },
  { id: "inspections", title: "Field inspections", description: "Capture surveys, defects, evidence and recommended actions.", icon: "✓", tag: "FIELD DATA", tone: "amber" },
  { id: "module-maintenance-planning", title: "Maintenance plans", description: "Coordinate routine, periodic and emergency maintenance.", icon: "▤", tag: "PLANNING", tone: "blue" },
  { id: "module-maintenance-proposals", title: "Maintenance proposals", description: "Prepare measured BOQs and track engineering review.", icon: "▧", tag: "PROPOSALS", tone: "teal" },
  { id: "module-work-orders", title: "Work orders", description: "Follow assigned works, delivery progress and completion.", icon: "⚙", tag: "EXECUTION", tone: "slate" },
  { id: "module-ai-priority-support", title: "AI priority support", description: "Review evidence-backed road risk rankings and actions.", icon: "✦", tag: "AI DECISION SUPPORT", tone: "violet" },
];

function metricIcon(label: string): string {
  const key = label.toLowerCase();
  if (key.includes("road") || key.includes("network")) return "↗";
  if (key.includes("asset")) return "◈";
  if (key.includes("section") || key.includes("chainage")) return "⇄";
  if (key.includes("inspection") || key.includes("defect")) return "✓";
  if (key.includes("maintenance") || key.includes("work")) return "⚙";
  if (key.includes("budget") || key.includes("cost")) return "◉";
  return "▦";
}

export default function RoadAssetDashboard({ metrics, loading, error, onRefresh }: Props) {
  return (
    <section id="department-overview" className="rams-dashboard">
      <header className="rams-dashboard-hero">
        <div className="rams-hero-copy">
          <p className="rams-dashboard-kicker"><span className="rams-kicker-mark">R</span> ROAD ASSET MANAGEMENT <span className="rams-kicker-divider">/</span> OPERATIONS</p>
          <h2>Road network overview</h2>
          <p className="rams-hero-description">
            A single operational workspace for road inventory, field condition, maintenance delivery, GIS and AI-assisted prioritization.
          </p>
          <div className="rams-hero-actions">
            <a className="rams-primary-link" href="#module-road-inventory">Open road inventory <span aria-hidden="true">→</span></a>
            <a className="rams-secondary-link" href="#module-ai-priority-support"><span aria-hidden="true">✦</span> Review AI priorities</a>
          </div>
        </div>
        <div className="rams-hero-side">
          <div className={"rams-data-state" + (error ? " has-error" : loading ? " is-loading" : "")}>
            <span className="rams-data-state-dot" aria-hidden="true" />
            <div>
              <strong>{loading ? "Loading operational data" : error ? "Data needs attention" : "Department workspace"}</strong>
              <span>{loading ? "Retrieving authorized records" : error ? "Metrics could not be refreshed" : "Use current records for planning"}</span>
            </div>
          </div>
          <button className="rams-refresh-button" type="button" onClick={onRefresh} disabled={loading}>
            <span aria-hidden="true">↻</span> {loading ? "Refreshing…" : "Refresh dashboard"}
          </button>
          <p className="rams-hero-footnote">Metrics reflect the records returned by the department API.</p>
        </div>
        <div className="rams-hero-decoration" aria-hidden="true"><span /><span /><span /><span /><span /></div>
      </header>

      <div className="rams-section-heading">
        <div>
          <p className="rams-section-eyebrow">AT A GLANCE</p>
          <h3>Operational snapshot</h3>
          <p>Review current department indicators before opening a detailed module.</p>
        </div>
        <span className="rams-live-label"><span /> API DATA</span>
      </div>

      {loading && <div className="rams-dashboard-state" role="status"><span className="rams-loading-spinner" /> Loading authorized road asset metrics…</div>}
      {error && <div className="error-message" role="alert">{error}</div>}
      {!loading && !error && metrics.length > 0 && (
        <div className="rams-metric-grid">
          {metrics.slice(0, 8).map((metric, index) => (
            <article className={"rams-metric-card rams-tone-" + (index % 4)} key={metric.label}>
              <div className="rams-metric-topline">
                <span className="rams-metric-icon" aria-hidden="true">{metricIcon(metric.label)}</span>
                <span className="rams-metric-index">{String(index + 1).padStart(2, "0")}</span>
              </div>
              <span className="rams-metric-label">{metric.label}</span>
              <strong className="rams-metric-value">{metric.value}{metric.unit === "percent" ? "%" : ""}</strong>
              <span className="rams-metric-foot">Current reported value</span>
            </article>
          ))}
        </div>
      )}
      {!loading && !error && metrics.length === 0 && (
        <div className="rams-dashboard-state">
          <span className="rams-empty-icon" aria-hidden="true">▦</span>
          <div><strong>No operational metrics yet</strong><p>Add road and maintenance records to populate this snapshot. You can still open the modules below to review available records.</p></div>
        </div>
      )}

      <div className="rams-section-heading rams-modules-heading">
        <div>
          <p className="rams-section-eyebrow">WORKSPACE MODULES</p>
          <h3>Road asset operations</h3>
          <p>Choose a work area to manage records, review evidence or coordinate maintenance.</p>
        </div>
        <span className="rams-module-count">{shortcuts.length} modules</span>
      </div>
      <div className="rams-shortcut-grid">
        {shortcuts.map((item, index) => (
          <a className={"rams-shortcut-card rams-shortcut-" + item.tone} href={`#${item.id}`} key={item.id}>
            <div className="rams-shortcut-topline">
              <span className="rams-shortcut-icon" aria-hidden="true">{item.icon}</span>
              <span className="rams-shortcut-number">{String(index + 1).padStart(2, "0")}</span>
            </div>
            <span className="rams-shortcut-tag">{item.tag}</span>
            <strong>{item.title}</strong>
            <span className="rams-shortcut-description">{item.description}</span>
            <span className="rams-shortcut-open">Open module <span aria-hidden="true">→</span></span>
          </a>
        ))}
      </div>
      <div className="rams-advisory-note">
        <span className="rams-advisory-mark" aria-hidden="true">i</span>
        <p><strong>Engineering decision support.</strong> GIS markers depend on recorded GPS coordinates. AI priority scores and budget plans are advisory; validate field evidence, quantities and available funding before approving work.</p>
      </div>
    </section>
  );
}
