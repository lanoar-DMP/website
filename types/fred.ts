export interface FredObservation {
  date: string;
  value: string;
}

export interface FredSeriesResponse {
  observations: FredObservation[];
}

export interface MacroDataPoint {
  date: string;
  value: number;
}

export interface MacroSeries {
  id: string;
  label: string;
  unit: string;
  data: MacroDataPoint[];
}
