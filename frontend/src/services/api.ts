import axios from 'axios';
import type {
  GeoJSONCollection,
  HotspotProperties,
  WardProperties,
  DrainageProperties,
  PumpProperties,
  WardScore,
  SimulationResult,
  AIResponse,
  InfrastructureGap,
  DashboardSummary,
  RainfallRecord,
  RiskAlert,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// Dashboard
export const fetchDashboardSummary = async (): Promise<DashboardSummary> => {
  const { data } = await api.get('/dashboard/summary');
  return data;
};

// Hotspots
export const fetchHotspots = async (params?: {
  ward_id?: number;
  min_probability?: number;
  severity?: string;
  limit?: number;
}): Promise<GeoJSONCollection<HotspotProperties>> => {
  const { data } = await api.get('/hotspots/', { params });
  return data;
};

export const fetchHotspotSummary = async () => {
  const { data } = await api.get('/hotspots/summary');
  return data;
};

export const fetchHotspotClusters = async (method = 'dbscan') => {
  const { data } = await api.get('/hotspots/clusters', { params: { method } });
  return data;
};

// Wards
export const fetchWards = async (): Promise<GeoJSONCollection<WardProperties>> => {
  const { data } = await api.get('/dashboard/wards');
  return data;
};

// Drainage
export const fetchDrainage = async (): Promise<GeoJSONCollection<DrainageProperties>> => {
  const { data } = await api.get('/dashboard/drainage');
  return data;
};

// Pumps
export const fetchPumps = async (): Promise<GeoJSONCollection<PumpProperties>> => {
  const { data } = await api.get('/dashboard/pumps');
  return data;
};

// Rainfall
export const fetchRainfall = async (): Promise<RainfallRecord[]> => {
  const { data } = await api.get('/dashboard/rainfall');
  return data.data;
};

// Ward Scores
export const fetchWardScores = async (): Promise<WardScore[]> => {
  const { data } = await api.get('/ward-score/');
  return data.scores;
};

export const fetchWardRankings = async () => {
  const { data } = await api.get('/ward-score/rankings');
  return data.rankings;
};

export const fetchRiskAlerts = async (): Promise<RiskAlert[]> => {
  const { data } = await api.get('/ward-score/alerts');
  return data.alerts;
};

export const fetchScoreDistribution = async () => {
  const { data } = await api.get('/ward-score/distribution');
  return data;
};

// Flood Prediction
export const predictFloodRisk = async (params: {
  lat: number;
  lng: number;
  rainfall_intensity_mmh: number;
  elevation_m?: number;
  slope_deg?: number;
}) => {
  const { data } = await api.post('/flood-prediction/', params);
  return data;
};

// Simulation
export const simulateRainfall = async (
  intensity_mmh: number,
  duration_hours = 3.0
): Promise<SimulationResult> => {
  const { data } = await api.post('/simulate-rainfall/', {
    intensity_mmh,
    duration_hours,
  });
  return data;
};

export const fetchProgressiveSimulation = async (
  duration_hours = 3.0
): Promise<SimulationResult[]> => {
  const { data } = await api.get('/simulate-rainfall/progressive', {
    params: { duration_hours },
  });
  return data.simulations;
};

// AI Query
export type AIMode = 'auto' | 'chatgpt' | 'gemini';

export const queryAI = async (
  query: string,
  context?: string,
  mode: AIMode = 'auto'
): Promise<AIResponse> => {
  const endpoint = mode === 'auto' ? '/ai-query/' : `/ai-query/${mode}`;
  const { data } = await api.post(endpoint, { query, context });
  return data;
};

// Infrastructure
export const fetchInfrastructureGaps = async (): Promise<InfrastructureGap[]> => {
  const { data } = await api.get('/infrastructure/gaps');
  return data.gaps;
};

export const fetchRecommendations = async () => {
  const { data } = await api.get('/infrastructure/recommendations');
  return data.recommendations;
};

export const fetchInfrastructureSummary = async () => {
  const { data } = await api.get('/infrastructure/summary');
  return data;
};
