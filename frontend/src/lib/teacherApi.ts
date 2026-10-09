import { api } from "./api";

// --- Curriculum ---
export const listSchools = () => api.get("/teacher/schools").then(r => r.data);
export const createSchool = (p: { name: string; board: string; city?: string }) =>
  api.post("/teacher/schools", p).then(r => r.data);

export const listClasses = (schoolId: string) =>
  api.get(`/teacher/schools/${schoolId}/classes`).then(r => r.data);
export const createClass = (p: { school_id: string; grade: number }) =>
  api.post("/teacher/classes", p).then(r => r.data);

export const listSubjects = (classId: string) =>
  api.get(`/teacher/classes/${classId}/subjects`).then(r => r.data);
export const createSubject = (p: { class_id: string; name: string }) =>
  api.post("/teacher/subjects", p).then(r => r.data);

export const listBooks = (subjectId: string) =>
  api.get(`/teacher/subjects/${subjectId}/books`).then(r => r.data);
export const createBook = (p: { subject_id: string; title: string; publisher?: string }) =>
  api.post("/teacher/books", p).then(r => r.data);

export const listChapters = (bookId: string) =>
  api.get(`/teacher/books/${bookId}/chapters`).then(r => r.data);
export const createChapter = (p: { book_id: string; number: number; title: string }) =>
  api.post("/teacher/chapters", p).then(r => r.data);

export const listSections = (chapterId: string) =>
  api.get(`/teacher/chapters/${chapterId}/sections`).then(r => r.data);
export const createSection = (p: {
  chapter_id: string; number: string; title: string;
  start_page?: number; end_page?: number;
}) => api.post("/teacher/sections", p).then(r => r.data);

export const listChunks = (sectionId: string) =>
  api.get(`/teacher/sections/${sectionId}/chunks`).then(r => r.data);
export const ingestSection = (sectionId: string, text: string) =>
  api.post(`/teacher/sections/${sectionId}/ingest`, { text }).then(r => r.data);
export const deleteChunks = (sectionId: string) =>
  api.delete(`/teacher/sections/${sectionId}/chunks`);

// --- Concepts ---
export const listConcepts = (classId?: string) => {
  const params = classId ? `?class_id=${classId}` : "";
  return api.get(`/teacher/concepts${params}`).then(r => r.data);
};
export const createConcept = (p: any) => api.post("/teacher/concepts", p).then(r => r.data);
export const updateConcept = (key: string, p: any) =>
  api.patch(`/teacher/concepts/${key}`, p).then(r => r.data);
export const deleteConcept = (key: string) =>
  api.delete(`/teacher/concepts/${key}`);

export const addPrerequisite = (key: string, prerequisite_key: string, strength = "required") =>
  api.post(`/teacher/concepts/${key}/prerequisites`, { prerequisite_key, strength }).then(r => r.data);
export const removePrerequisite = (key: string, prereqKey: string) =>
  api.delete(`/teacher/concepts/${key}/prerequisites/${prereqKey}`);

export const addMisconception = (key: string, p: { label: string; description?: string; remedy?: string }) =>
  api.post(`/teacher/concepts/${key}/misconceptions`, p).then(r => r.data);
export const removeMisconception = (key: string, id: string) =>
  api.delete(`/teacher/concepts/${key}/misconceptions/${id}`);

export const getGraph = () => api.get("/teacher/graph").then(r => r.data);
