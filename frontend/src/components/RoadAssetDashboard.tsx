import type { ReactNode } from "react";

export type RoadAssetMetric = { label: string; value: string | number; unit?: string };

type Props = {
  metrics: RoadAssetMetric[];
  loading: boolean;
  error: string;
  onRefresh: () => void;
};

const shortcuts: { id: string; title: string; description: string; icon: string; tag: string }[] = [
  { id: "module-road-inventory", title: "Road inventory", description: "Register corridors, road class, surface and length.", icon: "↗", tag: "NETWORK" },
  { id: "module-sections-and-chainage", title: "Sections & chainage", description: "Manage section limits, chainage and condition ratings.", icon: "◎", tag: "SEGMENTATION" },
  { id: "inspections", title: "Field inspections", description: "Record surveys, defects and recommended actions.", icon: "✓", tag: "FIELD DATA" },
  { id: "module-maintenance-planning", title: "Maintenance plans", description: "Organize routine, periodic and emergency works.", icon: "▤", tag: "PLANNING" },
  { id: "module-work-orders", title: "Work orders", description: "Track assigned maintenance and delivery progress.", icon: "⚙", tag: "EXECUTION" },
  { id: "module-ai-priority-support", title: "AI road priority", description: "Review evidence-backed risk ranking and actions.", icon: "✦", tag: "INTELLIGENCE" },
];

export default function RoadAssetDashboard({ metrics, loading, error, onRefresh }: Props) {
  const metricCards: ReactNode = metrics.length ? (
    <div className="metric-grid rams-metric-grid">
      {metrics.slice(0, 8).map((metric, index) => (
        <article className={`metric-card rams-metric-card rams-metric-${index % 4}`} key={metric.label}>
          <span className="metric-label">{metric.label}</span>
          <strong className="metric-value">
            {metric.value}{metric.unit === "percent" ? "%" : ""}
          </strong>
          <span className="rams-metric-foot">Live operational data</span>
        </article>
      ))}
    </div>
  ) : null;

  return (
    <section id="department-overview" className="rams-dashboard">
      <div className="rams-dashboard-hero">
        <div className="rams-hero-copy">
          <p className="eyebrow">RAMS · ROAD ASSET MANAGEMENT</p>
          <h2>Road network operations</h2>
          <p>
            One workspace for road inventory, chainage sections, field inspections,
            maintenance delivery and evidence-based AI prioritization.
          </p>
          <div className="rams-hero-actions">
            <a className="rams-primary-link" href="#module-road-inventory">Open road inventory <span aria-hidden="true">→</span></a>
            <a className="rams-secondary-link" href="#module-ai-priority-support">Review AI priorities</a>
          </div>
        </div>
        <div className="rams-hero-status" aria-label="Dashboard data status">
          <span className="rams-status-dot" />
          <div>
            <strong>{loading ? "Refreshing live data" : error ? "Data needs attention" : "Operations workspace"}</strong>
            <span>{loading ? "Loading authorized department metrics" : error ? "Dashboard data could not be loaded" : "Use current records to guide maintenance decisions"}</span>
          </div>
          <button type="button" onClick={onRefresh} disabled={loading}>
            {loading ? "Loading…" : "Refresh data"}
          </button>
        </div>
      </div>

      <div className="rams-overview-heading">
        <div>
          <p className="eyebrow">NETWORK SNAPSHOT</p>
          <h3>Operational overview</h3>
          <p>Metrics are loaded from the AI-RMMS API; no sample figures are substituted.</p>
        </div>
      </div>
      {loading && <p className="empty-state">Loading road asset metrics…</p>}
      {error && <div className="error-message" role="alert">{error}</div>}
      {!loading && !error && metricCards}
      {!loading && !error && metrics.length === 0 && (
        <p className="empty-state">No operational metrics are available yet. Add road and maintenance records to populate the dashboard.</p>
      )}

      <div className="rams-overview-heading rams-shortcuts-heading">
        <div>
          <p className="eyebrow">RAMS MODULES</p>
          <h3>Road asset operations</h3>
          <p>Jump directly to the tools used by road engineers and maintenance teams.</p>
        </div>
      </div>
      <div className="rams-shortcut-grid">
        {shortcuts.map((item) => (
          <a className="rams-shortcut-card" href={`#${item.id}`} key={item.id}>
            <span className="rams-shortcut-icon" aria-hidden="true">{item.icon}</span>
            <span className="rams-shortcut-tag">{item.tag}</span>
            <strong>{item.title}</strong>
            <span className="rams-shortcut-description">{item.description}</span>
            <span className="rams-shortcut-open">Open module <span aria-hidden="true">→</span></span>
          </a>
        ))}
      </div>
      <div className="rams-advisory-note">
        <span className="rams-advisory-mark" aria-hidden="true">i</span>
        <p><strong>Engineering decision support:</strong> AI priority scores and recommendations are advisory. Verify field conditions and available evidence before approving maintenance work.</p>
      </div>
    </section>
  );
}
