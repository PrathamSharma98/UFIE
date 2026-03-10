import React, { useState, useEffect, useCallback } from 'react';
import { BarChart3, TrendingUp, Wrench, MapPin, RefreshCw, AlertTriangle } from 'lucide-react';
import ReadinessBarChart from '../charts/ReadinessBarChart';
import FloodRiskTrend from '../charts/FloodRiskTrend';
import RainfallFloodChart from '../charts/RainfallFloodChart';
import InfrastructureGapChart from '../charts/InfrastructureGapChart';
import HotspotDensityChart from '../charts/HotspotDensityChart';
import {
  fetchWardScores,
  fetchRainfall,
  fetchProgressiveSimulation,
  fetchInfrastructureGaps,
  fetchHotspotSummary,
} from '../../services/api';
import type { WardScore, RainfallRecord, SimulationResult, InfrastructureGap } from '../../types';

function ChartShimmer({ height = 300 }: { height?: number }) {
  return (
    <div className="glass-panel p-4">
      <div className="loading-shimmer h-4 w-48 mb-4 rounded" />
      <div className="loading-shimmer rounded-lg" style={{ height }} />
    </div>
  );
}

function AnalyticsView() {
  const [wardScores, setWardScores] = useState<WardScore[] | null>(null);
  const [rainfall, setRainfall] = useState<RainfallRecord[] | null>(null);
  const [simResults, setSimResults] = useState<SimulationResult[] | null>(null);
  const [gaps, setGaps] = useState<InfrastructureGap[] | null>(null);
  const [hotspotSummary, setHotspotSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ws, rf, sr, gp, hs] = await Promise.all([
        fetchWardScores(),
        fetchRainfall(),
        fetchProgressiveSimulation(),
        fetchInfrastructureGaps(),
        fetchHotspotSummary(),
      ]);
      setWardScores(ws);
      setRainfall(rf);
      setSimResults(sr);
      setGaps(gp);
      setHotspotSummary(hs);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <AlertTriangle size={40} className="text-red-400 mb-3" />
        <p className="text-sm text-slate-400 mb-4">{error}</p>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-semibold text-white transition-colors"
        >
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 panel-scroll p-4 space-y-4">
        <div className="loading-shimmer h-8 w-56 rounded-lg" />
        <ChartShimmer height={480} />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ChartShimmer />
          <ChartShimmer />
          <ChartShimmer />
          <ChartShimmer height={380} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 panel-scroll p-4 space-y-4">
      {/* Sticky Header */}
      <div className="sticky-header -mx-4 px-4 py-2 -mt-4 mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <BarChart3 size={16} className="text-blue-400" />
          Analytics Dashboard
        </h2>
        <button
          onClick={loadData}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold bg-slate-800/60 hover:bg-slate-700/60 rounded-lg text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw size={11} /> Refresh
        </button>
      </div>

      {/* Ward Readiness Scores (full width) */}
      <div className="glass-panel p-4 tab-content">
        <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 uppercase tracking-wider">
          <BarChart3 size={14} className="text-blue-400" />
          Ward Pre-Monsoon Readiness Scores
        </h3>
        <div className="h-[500px]">
          {wardScores && <ReadinessBarChart wardScores={wardScores} />}
        </div>
      </div>

      {/* 2-column grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Flood Risk Trend */}
        <div className="glass-panel p-4 tab-content" style={{ animationDelay: '0.05s' }}>
          <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 uppercase tracking-wider">
            <TrendingUp size={14} className="text-blue-400" />
            Flood Risk Trend
          </h3>
          <div className="h-[300px]">
            {rainfall && <FloodRiskTrend rainfallData={rainfall} />}
          </div>
        </div>

        {/* Rainfall vs Flood Impact */}
        <div className="glass-panel p-4 tab-content" style={{ animationDelay: '0.1s' }}>
          <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 uppercase tracking-wider">
            <TrendingUp size={14} className="text-orange-400" />
            Rainfall Intensity vs Flood Impact
          </h3>
          <div className="h-[300px]">
            {simResults && <RainfallFloodChart simulationResults={simResults} />}
          </div>
        </div>

        {/* Infrastructure Gaps */}
        <div className="glass-panel p-4 tab-content" style={{ animationDelay: '0.15s' }}>
          <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 uppercase tracking-wider">
            <Wrench size={14} className="text-yellow-400" />
            Infrastructure Gaps
          </h3>
          <div className="h-[300px]">
            {gaps && <InfrastructureGapChart gaps={gaps} />}
          </div>
        </div>

        {/* Hotspot Density */}
        <div className="glass-panel p-4 tab-content" style={{ animationDelay: '0.2s' }}>
          <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 uppercase tracking-wider">
            <MapPin size={14} className="text-red-400" />
            Hotspot Density by Ward
          </h3>
          <div className="h-[400px]">
            {hotspotSummary && <HotspotDensityChart hotspotSummary={hotspotSummary} />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default React.memo(AnalyticsView);
