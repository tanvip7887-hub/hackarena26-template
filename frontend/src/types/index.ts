export interface Threat {
  person_id:           number;
  bbox:                [number, number, number, number];
  in_zone:             boolean;
  near_zone:           boolean;
  loiter_seconds:      number;
  peripheral_seconds:  number;
  crowd_count:         number;
  behaviour_summary:   string;
  behaviour_anomalies: string[];
  threat_score:        number;
  risk_level:          "Low" | "Medium" | "High";
  explanation:         string;
  weapon_detected:     boolean;
  gun_detected:        boolean;
}

export interface CurrentStatus {
  mode:           "live" | "demo";
  active_persons: number;
  threats:        Threat[];
  latest_alert:   Alert | null;
  video_file:     string;
}

export interface Alert {
  id:              number;
  timestamp:       string;
  person_id:       number;
  zone_name:       string;   // backend sends zone_name
  loiter_time:     number;   // backend sends loiter_time
  threat_score:    number;   // backend sends threat_score
  risk_level:      "Low" | "Medium" | "High";  // backend sends risk_level
  explanation:     string;
  llm_explanation?: string;
}

export interface AlertsResponse {
  status: string;
  count:  number;
  alerts: Alert[];
}

export interface VideosResponse {
  status: string;
  videos: string[];
}    index.ts