import { useCallback, useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { supabase } from "../lib/supabase";
import "leaflet/dist/leaflet.css";

type RoadAsset = {
  id: string;
  road_id: string;
  road_section_id: string | null;
  asset_code: string;
  asset_type: string;
  name: string;
  chainage_km: number | null;
  latitude: number | null;
  longitude: number | null;
  condition_rating: number | null;
  criticality: string;
  status: string;
};
type Road = { id: string; road_code: string; name: string };

const API = import.meta.env.VITE_API_BASE_URL_RMMS ?? "https://ai-rmms-backend.onrender.com/api/v1";
const TYPES = ["bridge", "culvert", "drainage", "sign", "guardrail", "retaining_wall", "marker", "lighting", "other"];
const STATUSES = ["active", "needs_inspection", "maintenance_required", "out_of_service", "retired"];
const ETHIOPIA_CENTER: [number, number] = [9.145, 40.489];

function markerIcon(criticality: string) {
  const color = criticality === "critical" ? "#b91c1c" : criticality === "high" ? "#d97706" : criticality === "medium" ? "#2563eb" : "#0f766e";
  return L.divIcon({
    className: "gis-marker-shell",
    html: `<span style="display:block;width:16px;height:16px;border:3px solid white;border-radius:50%;background:${color};box-shadow:0 1px 7px #0f172a88"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function FitMapToAssets({ points }: { points: RoadAsset[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) {
      map.setView([Number(points[0].latitude), Number(points[0].longitude)], 14);
    } else if (points.length > 1) {
      const bounds = L.latLngBounds(points.map((point) => [Number(point.latitude), Number(point.longitude)] as [number, number]));
      map.fitBounds(bounds, { padding: [36, 36], maxZoom: 14 });
    }
  }, [map, points]);
  return null;
}

export default function RoadGISModule() {
  const [assets, setAssets] = useState<RoadAsset[]>([]);
  const [roads, setRoads] = useState<Road[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [criticalityFilter, setCriticalityFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) throw sessionError;
      const token = data.session?.access_token;
      if (!token) throw new Error("Please sign in to view the GIS asset map.");
      const headers = { Authorization: `Bearer ${token}` };
      const [assetResponse, roadResponse] = await Promise.all([
        fetch(`${API}/road-assets?limit=200`, { headers }),
        fetch(`${API}/roads?limit=200`, { headers }),
      ]);
      if (!assetResponse.ok) throw new Error(assetResponse.status === 403 ? "You are not authorized to view road assets." : `Road assets failed to load (${assetResponse.status}).`);
      if (!roadResponse.ok) throw new Error(`Road list failed to load (${roadResponse.status}).`);
      const [assetRows, roadRows] = await Promise.all([assetResponse.json(), roadResponse.json()]);
      setAssets(assetRows as RoadAsset[]);
      setRoads(roadRows as Road[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load GIS asset data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const roadNames = useMemo(() => new Map(roads.map((road) => [road.id, `${road.road_code} · ${road.name}`])), [roads]);
  const filtered = useMemo(() => assets.filter((asset) =>
    (typeFilter === "all" || asset.asset_type === typeFilter) &&
    (statusFilter === "all" || asset.status === statusFilter) &&
    (criticalityFilter === "all" || asset.criticality === criticalityFilter)
  ), [assets, typeFilter, statusFilter, criticalityFilter]);
  const mapped = useMemo(() => filtered.filter((asset) =>
    Number.isFinite(Number(asset.latitude)) && Number.isFinite(Number(asset.longitude)) &&
    asset.latitude !== null && asset.longitude !== null &&
    Number(asset.latitude) >= -90 && Number(asset.latitude) <= 90 &&
    Number(asset.longitude) >= -180 && Number(asset.longitude) <= 180
  ), [filtered]);
  const unmappedCount = filtered.length - mapped.length;
  const criticalCount = mapped.filter((asset) => ["critical", "high"].includes(asset.criticality)).length;

  return (
    <section id="module-gis-asset-map" className="module-panel gis-module">
      <div className="section-heading">
        <div>
          <p className="eyebrow">GIS · SPATIAL OPERATIONS</p>
          <h2>Road asset GIS map</h2>
          <p className="panel-help">Map registered road assets from verified GPS coordinates. This view does not invent road alignments or missing locations.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh map"}</button>
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}

      <div className="gis-filter-bar">
        <label>Asset type
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="all">All types</option>
            {TYPES.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label>Status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            {STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label>Criticality
          <select value={criticalityFilter} onChange={(event) => setCriticalityFilter(event.target.value)}>
            <option value="all">All criticality</option>
            {["critical", "high", "medium", "low"].map((level) => <option key={level} value={level}>{level}</option>)}
          </select>
        </label>
      </div>

      <div className="gis-summary-grid">
        <div className="metric-card"><span className="metric-label">Assets in filter</span><strong className="metric-value">{filtered.length}</strong></div>
        <div className="metric-card"><span className="metric-label">Mapped assets</span><strong className="metric-value">{mapped.length}</strong></div>
        <div className="metric-card"><span className="metric-label">High / critical mapped</span><strong className="metric-value">{criticalCount}</strong></div>
        <div className="metric-card"><span className="metric-label">Missing coordinates</span><strong className="metric-value">{unmappedCount}</strong></div>
      </div>

      {loading ? <p className="empty-state">Loading authorized GIS records…</p> : (
        <>
          <div className="gis-map-frame" aria-label="Interactive map of registered road assets">
            <MapContainer center={ETHIOPIA_CENTER} zoom={6} scrollWheelZoom className="gis-leaflet-map">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <FitMapToAssets points={mapped} />
              {mapped.map((asset) => (
                <Marker key={asset.id} position={[Number(asset.latitude), Number(asset.longitude)]} icon={markerIcon(asset.criticality)}>
                  <Popup>
                    <div className="gis-popup">
                      <strong>{asset.asset_code} · {asset.name}</strong>
                      <span>{roadNames.get(asset.road_id) ?? "Road name unavailable"}</span>
                      <span>Type: {asset.asset_type.replaceAll("_", " ")}</span>
                      <span>Condition: {asset.condition_rating ?? "Not recorded"} / 5</span>
                      <span>Criticality: {asset.criticality}</span>
                      <span>Status: {asset.status.replaceAll("_", " ")}</span>
                      {asset.chainage_km !== null && <span>Chainage: {Number(asset.chainage_km).toFixed(2)} km</span>}
                      <span>GPS: {Number(asset.latitude).toFixed(5)}, {Number(asset.longitude).toFixed(5)}</span>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
          <div className="gis-legend" aria-label="Map criticality legend">
            <strong>Criticality</strong>
            <span><i className="gis-dot critical" /> Critical</span>
            <span><i className="gis-dot high" /> High</span>
            <span><i className="gis-dot medium" /> Medium</span>
            <span><i className="gis-dot low" /> Low</span>
          </div>
          {mapped.length === 0 && (
            <p className="empty-state">No assets with valid GPS coordinates match these filters. Register latitude and longitude in the Road Asset Register to display map markers.</p>
          )}
          {unmappedCount > 0 && (
            <p className="gis-data-note">{unmappedCount} filtered asset(s) are not shown on the map because latitude/longitude is missing or invalid. Their records remain available in the asset register.</p>
          )}
          {mapped.length > 0 && (
            <div className="gis-asset-list">
              <h3>Mapped assets</h3>
              {mapped.slice(0, 30).map((asset) => (
                <div className="gis-asset-row" key={asset.id}>
                  <span className={`gis-dot ${asset.criticality}`} aria-hidden="true" />
                  <div><strong>{asset.asset_code} · {asset.name}</strong><span>{roadNames.get(asset.road_id) ?? "Road name unavailable"}</span></div>
                  <span className="gis-coordinate">{Number(asset.latitude).toFixed(4)}, {Number(asset.longitude).toFixed(4)}</span>
                </div>
              ))}
              {mapped.length > 30 && <p className="panel-help">Showing the first 30 mapped records in the list; all filtered records remain visible on the map.</p>}
            </div>
          )}
        </>
      )}
      <p className="gis-attribution-note">Map tiles © OpenStreetMap contributors. Coordinate coverage depends on field GPS data; verify positions before engineering decisions.</p>
    </section>
  );
}
