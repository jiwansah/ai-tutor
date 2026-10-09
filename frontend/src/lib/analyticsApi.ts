import { api } from "./api";

export const schoolSummary = (schoolId: string, days = 30) =>
  api.get(`/analytics/school/${schoolId}/summary?days=${days}`).then(r => r.data);

export const schoolTrend = (schoolId: string, days = 14) =>
  api.get(`/analytics/school/${schoolId}/trend?days=${days}`).then(r => r.data);

export const classSummary = (classId: string, days = 30) =>
  api.get(`/analytics/class/${classId}/summary?days=${days}`).then(r => r.data);

export const triggerRollup = (day: string) =>
  api.post(`/analytics/rollup/${day}`).then(r => r.data);
