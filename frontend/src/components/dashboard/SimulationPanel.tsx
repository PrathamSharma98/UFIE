import React, { useState, useCallback } from 'react';
import { CloudRain, Play, Loader2, Droplets, Gauge, Zap, AlertTriangle, RefreshCw } from 'lucide-react';
import { simulateRainfall } from '../../services/api';
import type { SimulationResult } from '../../types';

interface SimulationPanelProps {
  onSimulate: (result: SimulationResult) => void;
  currentSimulation: SimulationResult | null;
}

const presets = [20, 50, 80, 100, 150];

function intensityColor(intensity: number): string {
  if (intensity >= 100) return '#ef4444';
  if (intensity >= 75) return '#f97316';
  if (intensity >= 50) return '#eab308';
  return '#22c55e';
}

function SimulationPanel({ onSimulate, currentSimulation }: SimulationPanelProps) {
  const [intensity, setIntensity] = useState(50);
  const [duration, setDuration] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await simulateRainfall(intensity, duration);
      onSimulate(result);
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  }, [intensity, duration, onSimulate]);

  const sim = currentSimulation;

  return (
    <div className="p-3 space-y-3 max-h-[60vh] flex flex-col">
      {/* Controls */}
      <div className="space-y-2.5 flex-shrink-0">
        {/* Intensity Slider */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Intensity</span>
            <span className="text-xs font-bold" style={{ color: intensityColor(intensity) }}>
              {intensity} mm/hr
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={200}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-slate-700 accent-blue-500"
          />
          {/* Severity bar */}
          <div className="h-1 rounded-full bg-slate-800 mt-1.5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${(intensity / 200) * 100}%`,
                backgroundColor: intensityColor(intensity),
              }}
            />
          </div>
        </div>

        {/* Presets */}
        <div className="flex gap-1">
          {presets.map((p) => (
            <button
              key={p}
              onClick={() => setIntensity(p)}
              className={`flex-1 py-1 text-[10px] font-semibold rounded-lg transition-colors ${
                intensity === p
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700/30 hover:bg-slate-700/50'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Duration */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400 font-medium">Duration:</span>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(Math.max(0.5, Math.min(24, Number(e.target.value))))}
            step={0.5}
            min={0.5}
            max={24}
            className="w-14 bg-slate-800/60 border border-slate-700/40 rounded-lg px-2 py-1 text-xs text-white outline-none focus:border-blue-500/50"
          />
          <span className="text-[10px] text-slate-500">hours</span>
        </div>

        {/* Run Button */}
        <button
          onClick={handleSimulate}
          disabled={loading || intensity === 0}
          className="w-full flex items-center justify-center gap-2 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-xs font-semibold text-white transition-colors"
        >
          {loading ? (
            <>
              <Loader2 size={13} className="animate-spin" /> Simulating...
            </>
          ) : (
            <>
              <Play size={13} /> Run Simulation
            </>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 bg-red-950/40 border border-red-800/30 rounded-lg">
            <AlertTriangle size={12} className="text-red-400 flex-shrink-0" />
            <p className="text-[10px] text-red-300 flex-1">{error}</p>
            <button onClick={handleSimulate} className="text-red-400 hover:text-red-300">
              <RefreshCw size={10} />
            </button>
          </div>
        )}
      </div>

      {/* Results */}
      {sim && (
        <div className="flex-1 overflow-y-auto panel-scroll space-y-2.5 pt-2 border-t border-slate-700/30">
          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-1.5">
            <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/20 card-hover">
              <div className="flex items-center gap-1 mb-0.5">
                <CloudRain size={10} className="text-blue-400" />
                <span className="text-[9px] text-slate-500">Rainfall</span>
              </div>
              <p className="text-sm font-bold text-white">{sim.total_rainfall_mm.toFixed(0)} mm</p>
            </div>
            <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/20 card-hover">
              <div className="flex items-center gap-1 mb-0.5">
                <AlertTriangle size={10} className="text-orange-400" />
                <span className="text-[9px] text-slate-500">Activated</span>
              </div>
              <p className="text-sm font-bold text-white">
                {sim.activated_hotspots}
                <span className="text-[9px] text-slate-500 font-normal"> / {sim.total_hotspots}</span>
              </p>
            </div>
            <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/20 card-hover">
              <div className="flex items-center gap-1 mb-0.5">
                <Droplets size={10} className="text-cyan-400" />
                <span className="text-[9px] text-slate-500">Runoff</span>
              </div>
              <p className="text-sm font-bold text-white">{(sim.runoff_volume_m3 / 1e6).toFixed(1)}M m³</p>
            </div>
            <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/20 card-hover">
              <div className="flex items-center gap-1 mb-0.5">
                <Zap size={10} className="text-yellow-400" />
                <span className="text-[9px] text-slate-500">Peak</span>
              </div>
              <p className="text-sm font-bold text-white">{sim.peak_discharge_m3s.toFixed(0)} m³/s</p>
            </div>
          </div>

          {/* Affected wards */}
          <div className="text-[10px] text-slate-400">
            <span className="font-semibold text-white">{sim.affected_wards.length}</span> wards affected
          </div>

          {/* Ward impacts table */}
          {sim.ward_impacts && sim.ward_impacts.length > 0 && (
            <div className="bg-slate-800/30 rounded-lg border border-slate-700/20 overflow-hidden">
              <div className="sticky top-0 bg-slate-800/80 backdrop-blur-sm px-2 py-1.5 border-b border-slate-700/20">
                <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider">Ward Impact</span>
              </div>
              <div className="max-h-32 overflow-y-auto panel-scroll">
                {sim.ward_impacts.slice(0, 15).map((w) => (
                  <div
                    key={w.ward_id}
                    className="flex items-center justify-between px-2 py-1 border-b border-slate-700/10 last:border-0 hover:bg-slate-700/20 transition-colors"
                  >
                    <span className="text-[10px] text-slate-300 truncate max-w-[100px]">{w.ward_name}</span>
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                        style={{
                          color: w.flood_risk === 'High' ? '#ef4444' : w.flood_risk === 'Moderate' ? '#eab308' : '#22c55e',
                          backgroundColor: w.flood_risk === 'High' ? 'rgba(239,68,68,0.15)' : w.flood_risk === 'Moderate' ? 'rgba(234,179,8,0.15)' : 'rgba(34,197,94,0.15)',
                        }}
                      >
                        {w.flood_risk}
                      </span>
                      {w.drainage_capacity_exceeded && (
                        <span className="text-[8px] text-red-400 font-bold">OVR</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default React.memo(SimulationPanel);
