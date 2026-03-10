import React, { useState, useEffect, useMemo, useCallback, Suspense, lazy } from 'react';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import FloodMap from './components/map/FloodMap';
import MapControls from './components/map/MapControls';
import MapLegend from './components/map/MapLegend';
import SimulationPanel from './components/dashboard/SimulationPanel';
import AlertsPanel from './components/dashboard/AlertsPanel';
import AICopilotPanel from './components/ai/AICopilotPanel';
import {
  fetchDashboardSummary,
  fetchWardScores,
  fetchHotspots,
  fetchWards,
  fetchDrainage,
  fetchPumps,
} from './services/api';
import type {
  DashboardSummary,
  WardScore,
  GeoJSONCollection,
  HotspotProperties,
  WardProperties,
  DrainageProperties,
  PumpProperties,
  MapLayers,
  SimulationResult,
} from './types';

const AnalyticsView = lazy(() => import('./components/dashboard/AnalyticsView'));

export default function App() {
  // UI state
  const [activeTab, setActiveTab] = useState<'map' | 'analytics' | 'alerts'>('map');
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedWardId, setSelectedWardId] = useState<number | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);
  const [simPanelOpen, setSimPanelOpen] = useState(true);
  const [mapLayers, setMapLayers] = useState<MapLayers>({
    hotspots: true,
    heatmap: false,
    wards: true,
    drainage: false,
    pumps: false,
  });
  const [currentSimulation, setCurrentSimulation] = useState<SimulationResult | null>(null);

  // Data state
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null);
  const [wardScores, setWardScores] = useState<WardScore[] | null>(null);
  const [hotspots, setHotspots] = useState<GeoJSONCollection<HotspotProperties> | null>(null);
  const [wards, setWards] = useState<GeoJSONCollection<WardProperties> | null>(null);
  const [drainage, setDrainage] = useState<GeoJSONCollection<DrainageProperties> | null>(null);
  const [pumps, setPumps] = useState<GeoJSONCollection<PumpProperties> | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [summaryData, scoresData, hotspotsData, wardsData, drainageData, pumpsData] =
        await Promise.all([
          fetchDashboardSummary(),
          fetchWardScores(),
          fetchHotspots({ limit: 2700 }),
          fetchWards(),
          fetchDrainage(),
          fetchPumps(),
        ]);
      setDashboardSummary(summaryData);
      setWardScores(scoresData);
      setHotspots(hotspotsData);
      setWards(wardsData);
      setDrainage(drainageData);
      setPumps(pumpsData);
    } catch (err: any) {
      console.error('Failed to load data:', err);
      setLoadError(err.message || 'Failed to connect to the server. Ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Derived data
  const wardList = useMemo(() => {
    if (!wards) return [];
    return wards.features.map((f) => ({
      ward_id: f.properties.ward_id,
      ward_name: f.properties.ward_name,
    }));
  }, [wards]);

  const filteredHotspots = useMemo(() => {
    if (!hotspots) return null;
    let features = hotspots.features;
    if (selectedSeverity) {
      features = features.filter((f) => f.properties.severity === selectedSeverity);
    }
    if (selectedWardId !== null) {
      features = features.filter((f) => f.properties.ward_id === selectedWardId);
    }
    return { type: 'FeatureCollection' as const, features };
  }, [hotspots, selectedSeverity, selectedWardId]);

  // Handlers
  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab as 'map' | 'analytics' | 'alerts');
  }, []);

  const handleWardSelect = useCallback((wardId: number | null) => {
    setSelectedWardId(wardId);
  }, []);

  const handleSeverityFilter = useCallback((severity: string | null) => {
    setSelectedSeverity(severity);
  }, []);

  const handleLayerChange = useCallback((layers: MapLayers) => {
    setMapLayers(layers);
  }, []);

  const handleSimulate = useCallback((result: SimulationResult) => {
    setCurrentSimulation(result);
  }, []);

  // Loading screen
  if (loading) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center mx-auto mb-5 shadow-xl shadow-blue-500/30 animate-pulse">
            <Loader2 size={32} className="animate-spin text-white" />
          </div>
          <h2 className="text-lg font-bold text-white mb-1">Loading UFIE</h2>
          <p className="text-sm text-slate-400 mb-6">Urban Flood Intelligence Engine</p>
          <div className="flex items-center justify-center gap-2">
            <div className="loading-shimmer h-2 w-48 rounded-full" />
          </div>
        </div>
      </div>
    );
  }

  // Error screen
  if (loadError) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <div className="w-16 h-16 rounded-2xl bg-red-500/20 border border-red-500/30 flex items-center justify-center mx-auto mb-5">
            <AlertCircle size={32} className="text-red-400" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Connection Error</h2>
          <p className="text-sm text-slate-400 mb-6">{loadError}</p>
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-semibold text-white mx-auto transition-colors"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  // Suspense fallback
  const SuspenseFallback = (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <Loader2 size={32} className="animate-spin text-blue-400 mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading...</p>
      </div>
    </div>
  );

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden">
      <Header
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onToggleAI={() => setAiPanelOpen((p) => !p)}
        onToggleSidebar={() => setSidebarOpen((p) => !p)}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          summary={dashboardSummary}
          wardScores={wardScores}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <main className="flex-1 lg:ml-72 flex flex-col overflow-hidden relative">
          {/* MAP TAB */}
          {activeTab === 'map' && (
            <div className="flex-1 relative tab-content">
              <FloodMap
                hotspots={filteredHotspots}
                wards={wards}
                drainage={drainage}
                pumps={pumps}
                layers={mapLayers}
                selectedWardId={selectedWardId}
                simulation={currentSimulation}
                wardScores={wardScores ?? undefined}
                onWardClick={handleWardSelect}
              />

              <MapControls
                layers={mapLayers}
                onLayerChange={handleLayerChange}
                wards={wardList}
                onWardSelect={handleWardSelect}
                onSeverityFilter={handleSeverityFilter}
                selectedWardId={selectedWardId}
              />

              <MapLegend />

              {/* Simulation Panel */}
              <div className="absolute bottom-4 left-4 z-[1000] w-80">
                <div className="glass-panel-sm overflow-hidden">
                  <button
                    onClick={() => setSimPanelOpen((p) => !p)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/40 transition-colors"
                  >
                    <span>Rainfall Simulation</span>
                    <span className="text-[10px] text-slate-500">
                      {simPanelOpen ? 'Collapse' : 'Expand'}
                    </span>
                  </button>
                  {simPanelOpen && (
                    <div className="animate-fade-in">
                      <SimulationPanel
                        onSimulate={handleSimulate}
                        currentSimulation={currentSimulation}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ANALYTICS TAB */}
          {activeTab === 'analytics' && (
            <div className="flex-1 tab-content overflow-hidden">
              <Suspense fallback={SuspenseFallback}>
                <AnalyticsView />
              </Suspense>
            </div>
          )}

          {/* ALERTS TAB */}
          {activeTab === 'alerts' && (
            <div className="flex-1 overflow-y-auto p-4 tab-content panel-scroll">
              <AlertsPanel />
            </div>
          )}
        </main>
      </div>

      {/* Floating AI Copilot Widget */}
      <AICopilotPanel
        isOpen={aiPanelOpen}
        onToggle={() => setAiPanelOpen((p) => !p)}
      />
    </div>
  );
}
