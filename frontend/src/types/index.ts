// GeoJSON types
export interface GeoJSONFeature<P = Record<string, any>> {
  type: 'Feature';
  properties: P;
  geometry: {
    type: 'Point' | 'LineString' | 'Polygon' | 'MultiPolygon';
    coordinates: number[] | number[][] | number[][][] | number[][][][];
  };
}

export interface GeoJSONCollection<P = Record<string, any>> {
  type: 'FeatureCollection';
  features: GeoJSONFeature<P>[];
}

// Hotspot types
export interface HotspotProperties {
  hotspot_id: number;
  ward_id: number;
  ward_name: string;
  elevation_m: number;
  slope_deg: number;
  flow_accumulation: number;
  drainage_proximity_m: number;
  impervious_surface_pct: number;
  soil_permeability: number;
  flood_probability: number;
  severity: 'Critical' | 'High' | 'Moderate' | 'Low';
  affected_population: number;
  estimated_damage_inr_lakhs: number;
  runoff_coefficient: number;
  last_flood_year: number | null;
}

// Ward types
export interface WardProperties {
  ward_id: number;
  ward_name: string;
  population: number;
  area_km2: number;
  urban_density: number;
  impervious_surface_pct: number;
  drainage_length_km: number;
  drainage_capacity_m3s: number;
  pump_stations: number;
  emergency_shelters: number;
  historical_flood_events: number;
  avg_elevation_m: number;
  soil_permeability: number;
  green_cover_pct: number;
  center_lat: number;
  center_lng: number;
}

// Drainage types
export interface DrainageProperties {
  drain_id: number;
  ward_id: number;
  capacity_m3s: number;
  current_load_m3s: number;
  utilization_pct: number;
  diameter_mm: number;
  condition: string;
  age_years: number;
  material: string;
  is_undersized: boolean;
}

// Pump station types
export interface PumpProperties {
  pump_id: number;
  ward_id: number;
  capacity_m3h: number;
  status: string;
  power_backup: boolean;
  last_maintenance: string;
  year_installed: number;
}

// Ward Score
export interface WardScore {
  ward_id: number;
  ward_name: string;
  readiness_score: number;
  drainage_capacity_index: number;
  emergency_infrastructure_coverage: number;
  flood_hotspot_density: number;
  rainfall_vulnerability: number;
  pump_station_availability: number;
  category: 'Critical Risk' | 'Moderate Risk' | 'Prepared' | 'Resilient';
  population: number;
  area_km2: number;
}

// Simulation
export interface WardImpact {
  ward_id: number;
  ward_name: string;
  flood_risk: string;
  activated_hotspots: number;
  estimated_runoff_m3: number;
  drainage_capacity_exceeded: boolean;
}

export interface SimulationResult {
  intensity_mmh: number;
  duration_hours: number;
  total_rainfall_mm: number;
  affected_wards: string[];
  activated_hotspots: number;
  total_hotspots: number;
  runoff_volume_m3: number;
  peak_discharge_m3s: number;
  ward_impacts: WardImpact[];
}

// AI
export interface AIResponse {
  query: string;
  response: string;
  sources: string[];
  suggestions: string[];
}

// Infrastructure
export interface InfrastructureGap {
  ward_id: number;
  ward_name: string;
  gap_type: string;
  description: string;
  severity: string;
  recommended_action: string;
  estimated_cost_inr_crores: number;
}

// Dashboard Summary
export interface DashboardSummary {
  total_hotspots: number;
  critical_hotspots: number;
  high_risk_wards: number;
  avg_readiness_score: number;
  total_pump_stations: number;
  undersized_drains: number;
  total_wards: number;
  total_drainage_segments: number;
  infrastructure_gaps: number;
  last_updated: string;
}

// Rainfall data
export interface RainfallRecord {
  year: number;
  month: number;
  total_rainfall_mm: number;
  max_daily_mm: number;
  max_hourly_intensity_mmh: number;
  rainy_days: number;
  flood_events: number;
}

// Risk Alert
export interface RiskAlert {
  ward_id: number;
  ward_name: string;
  alert_type: string;
  message: string;
  severity: string;
}

// Map layer visibility
export interface MapLayers {
  hotspots: boolean;
  heatmap: boolean;
  wards: boolean;
  drainage: boolean;
  pumps: boolean;
}
