import { api } from "./api";

export const schoolSummary = (schoolId: string, days = 30, classId?: string) => {
  const params = new URLSearchParams({ days: String(days) });
  if (classId) params.set("class_id", classId);
  return api.get(`/analytics/school/${schoolId}/summary?${params}`).then(r => r.data);
};

export const schoolTrend = (schoolId: string, days = 14) =>
  api.get(`/analytics/school/${schoolId}/trend?days=${days}`).then(r => r.data);

export const classSummary = (classId: string, days = 30) =>
  api.get(`/analytics/class/${classId}/summary?days=${days}`).then(r => r.data);

export const triggerRollup = (day: string) =>
  api.post(`/analytics/rollup/${day}`).then(r => r.data);
