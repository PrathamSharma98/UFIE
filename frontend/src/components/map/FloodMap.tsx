import React, { useEffect, useMemo, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
  ZoomControl,
  Tooltip,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import type {
  GeoJSONCollection,
  HotspotProperties,
  WardProperties,
  DrainageProperties,
  PumpProperties,
  MapLayers,
  WardScore,
  SimulationResult,
} from '../../types';
import { severityColor, categoryColor, probabilityToColor } from '../../utils/helpers';

interface FloodMapProps {
  hotspots: GeoJSONCollection<HotspotProperties> | null;
  wards: GeoJSONCollection<WardProperties> | null;
  drainage: GeoJSONCollection<DrainageProperties> | null;
  pumps: GeoJSONCollection<PumpProperties> | null;
  layers: MapLayers;
  selectedWardId: number | null;
  simulation: SimulationResult | null;
  wardScores?: WardScore[];
  onWardClick: (wardId: number | null) => void;
}

const DELHI_CENTER: [number, number] = [28.6139, 77.209];
const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTR = '&copy; <a href="https://carto.com/">CARTO</a>';

/* ------------------------------------------------------------------ */
/* Heatmap Layer (imperative — no react-leaflet wrapper)              */
/* ------------------------------------------------------------------ */
const HeatmapLayer = React.memo(function HeatmapLayer({
  hotspots,
}: {
  hotspots: GeoJSONCollection<HotspotProperties> | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!hotspots?.features?.length) return;

    const points: [number, number, number][] = hotspots.features.map((f) => [
      f.geometry.coordinates[1] as number,
      f.geometry.coordinates[0] as number,
      f.properties.flood_probability,
    ]);

    const heat = (L as any).heatLayer(points, {
      radius: 18,
      blur: 22,
      maxZoom: 15,
      max: 1,
      gradient: {
        0.2: '#22c55e',
        0.4: '#eab308',
        0.6: '#f97316',
        0.8: '#ef4444',
        1.0: '#991b1b',
      },
    });

    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [map, hotspots]);

  return null;
});

/* ------------------------------------------------------------------ */
/* Fly-to-ward when selection changes                                 */
/* ------------------------------------------------------------------ */
const FlyToWard = React.memo(function FlyToWard({
  wards,
  selectedWardId,
}: {
  wards: GeoJSONCollection<WardProperties> | null;
  selectedWardId: number | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!selectedWardId || !wards) return;
    const feature = wards.features.find(
      (f) => f.properties.ward_id === selectedWardId
    );
    if (feature) {
      const { center_lat, center_lng } = feature.properties;
      map.flyTo([center_lat, center_lng], 13, { duration: 0.8 });
    }
  }, [map, wards, selectedWardId]);

  return null;
});

/* ------------------------------------------------------------------ */
/* Main FloodMap component                                            */
/* ------------------------------------------------------------------ */
function FloodMap({
  hotspots,
  wards,
  drainage,
  pumps,
  layers,
  selectedWardId,
  simulation,
  wardScores,
  onWardClick,
}: FloodMapProps) {
  /* -- ward score lookup ------------------------------------------- */
  const scoreMap = useMemo(() => {
    if (!wardScores) return new Map<number, WardScore>();
    return new Map(wardScores.map((s) => [Number(s.ward_id), s]));
  }, [wardScores]);

  /* -- simulation ward impact lookup ------------------------------- */
  const simImpact = useMemo(() => {
    if (!simulation?.ward_impacts) return new Map<number, string>();
    return new Map(
      simulation.ward_impacts.map((w) => [w.ward_id, w.flood_risk])
    );
  }, [simulation]);

  /* -- ward style -------------------------------------------------- */
  const wardStyle = useCallback(
    (feature: any) => {
      const wardId = feature?.properties?.ward_id;
      const isSelected = wardId === selectedWardId;
      const score = scoreMap.get(wardId);
      const risk = simImpact.get(wardId);

      let fillColor = '#334155';
      let fillOpacity = 0.25;

      if (risk) {
        fillColor = risk === 'High' ? '#ef4444' : risk === 'Moderate' ? '#eab308' : '#22c55e';
        fillOpacity = 0.35;
      } else if (score) {
        fillColor = categoryColor(score.category);
        fillOpacity = 0.3;
      }

      return {
        fillColor,
        fillOpacity,
        color: isSelected ? '#38bdf8' : '#475569',
        weight: isSelected ? 3 : 1.5,
        opacity: isSelected ? 1 : 0.6,
        dashArray: isSelected ? '' : '4 4',
      };
    },
    [selectedWardId, scoreMap, simImpact]
  );

  /* -- ward interaction -------------------------------------------- */
  const onEachWard = useCallback(
    (feature: any, layer: any) => {
      const p = feature.properties;
      const score = scoreMap.get(p.ward_id);
      const tooltip = score
        ? `<strong>${p.ward_name}</strong><br/>Score: ${score.readiness_score.toFixed(0)} (${score.category})`
        : `<strong>${p.ward_name}</strong>`;

      layer.bindTooltip(tooltip, {
        className: 'leaflet-tooltip-dark',
        direction: 'center',
        permanent: false,
      });

      layer.on({
        click: () => onWardClick(p.ward_id),
        mouseover: (e: any) => {
          e.target.setStyle({ weight: 3, opacity: 1, fillOpacity: 0.45 });
        },
        mouseout: (e: any) => {
          e.target.setStyle(wardStyle(feature));
        },
      });
    },
    [onWardClick, scoreMap, wardStyle]
  );

  /* -- drainage style --------------------------------------------- */
  const drainageStyle = useCallback((feature: any) => {
    const p = feature?.properties;
    const util = p?.utilization_pct ?? 0;
    let color = '#22c55e';
    if (util > 90) color = '#ef4444';
    else if (util > 70) color = '#f97316';
    else if (util > 50) color = '#eab308';

    return {
      color,
      weight: p?.is_undersized ? 3 : 1.5,
      opacity: 0.7,
      dashArray: p?.is_undersized ? '6 3' : '',
    };
  }, []);

  const onEachDrain = useCallback((feature: any, layer: any) => {
    const p = feature.properties;
    layer.bindTooltip(
      `<strong>Drain #${p.drain_id}</strong><br/>
       Capacity: ${p.capacity_m3s} m³/s<br/>
       Load: ${p.current_load_m3s} m³/s (${p.utilization_pct.toFixed(0)}%)<br/>
       Condition: ${p.condition}${p.is_undersized ? '<br/><span style="color:#ef4444;font-weight:700">UNDERSIZED</span>' : ''}`,
      { className: 'leaflet-tooltip-dark', sticky: true }
    );
  }, []);

  /* -- render ----------------------------------------------------- */
  return (
    <MapContainer
      center={DELHI_CENTER}
      zoom={11}
      className="w-full h-full"
      zoomControl={false}
      style={{ background: '#1a1a2e' }}
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTR} />
      <ZoomControl position="bottomright" />

      <FlyToWard wards={wards} selectedWardId={selectedWardId} />

      {/* Heatmap */}
      {layers.heatmap && <HeatmapLayer hotspots={hotspots} />}

      {/* Ward boundaries */}
      {layers.wards && wards && (
        <GeoJSON
          key={`wards-${selectedWardId}-${simulation?.intensity_mmh ?? 'none'}`}
          data={wards as any}
          style={wardStyle}
          onEachFeature={onEachWard}
        />
      )}

      {/* Drainage */}
      {layers.drainage && drainage && (
        <GeoJSON
          key="drainage"
          data={drainage as any}
          style={drainageStyle}
          onEachFeature={onEachDrain}
        />
      )}

      {/* Pump stations */}
      {layers.pumps &&
        pumps?.features?.map((f) => {
          const p = f.properties;
          const isOp = p.status === 'Operational';
          return (
            <CircleMarker
              key={`pump-${p.pump_id}`}
              center={[
                f.geometry.coordinates[1] as number,
                f.geometry.coordinates[0] as number,
              ]}
              radius={6}
              pathOptions={{
                fillColor: isOp ? '#38bdf8' : '#f472b6',
                color: isOp ? '#0284c7' : '#be185d',
                weight: 1.5,
                fillOpacity: 0.85,
              }}
            >
              <Popup>
                <div className="text-[12px] space-y-0.5">
                  <p className="font-bold text-white">Pump #{p.pump_id}</p>
                  <p>Capacity: <span className="text-blue-300">{p.capacity_m3h} m³/h</span></p>
                  <p>Status: <span className={isOp ? 'text-green-400' : 'text-red-400'}>{p.status}</span></p>
                  <p>Backup: {p.power_backup ? <span className="text-green-400">Yes</span> : <span className="text-red-400">No</span>}</p>
                  <p className="text-slate-400">Installed: {p.year_installed}</p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

      {/* Hotspot markers */}
      {layers.hotspots &&
        hotspots?.features?.map((f) => {
          const p = f.properties;
          const color = severityColor(p.severity);
          const radius = p.severity === 'Critical' ? 5 : p.severity === 'High' ? 4 : 3;
          return (
            <CircleMarker
              key={`hs-${p.hotspot_id}`}
              center={[
                f.geometry.coordinates[1] as number,
                f.geometry.coordinates[0] as number,
              ]}
              radius={radius}
              pathOptions={{
                fillColor: color,
                color: 'rgba(0,0,0,0.4)',
                weight: 0.5,
                fillOpacity: 0.8,
              }}
            >
              <Tooltip direction="top" offset={[0, -6]} className="leaflet-tooltip-dark">
                <span className="text-[11px]">
                  <strong>{p.severity}</strong> — {(p.flood_probability * 100).toFixed(0)}%
                </span>
              </Tooltip>
              <Popup>
                <div className="text-[12px] space-y-1 min-w-[180px]">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">Hotspot #{p.hotspot_id}</span>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{
                        color,
                        backgroundColor: `${color}22`,
                      }}
                    >
                      {p.severity}
                    </span>
                  </div>
                  <p className="text-slate-400 text-[10px]">{p.ward_name}</p>
                  <div className="h-px bg-slate-700 my-1" />
                  <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                    <span className="text-slate-400">Probability:</span>
                    <span className="text-white font-semibold">{(p.flood_probability * 100).toFixed(1)}%</span>
                    <span className="text-slate-400">Elevation:</span>
                    <span className="text-white">{p.elevation_m.toFixed(1)}m</span>
                    <span className="text-slate-400">Slope:</span>
                    <span className="text-white">{p.slope_deg.toFixed(1)}&deg;</span>
                    <span className="text-slate-400">Impervious:</span>
                    <span className="text-white">{p.impervious_surface_pct.toFixed(0)}%</span>
                    <span className="text-slate-400">Runoff Coeff:</span>
                    <span className="text-white">{p.runoff_coefficient.toFixed(3)}</span>
                    <span className="text-slate-400">Pop. Affected:</span>
                    <span className="text-white">{p.affected_population.toLocaleString()}</span>
                    <span className="text-slate-400">Est. Damage:</span>
                    <span className="text-orange-300">{p.estimated_damage_inr_lakhs.toFixed(0)}L</span>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}

export default React.memo(FloodMap);
