"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import axios from "axios";
import { register } from "@/lib/api";
import { useAuth } from "@/lib/store";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface School { id: string; name: string; board: string }
interface Cls    { id: string; grade: number }

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [schools, setSchools] = useState<School[]>([]);
  const [classes, setClasses] = useState<Cls[]>([]);
  const [schoolId, setSchoolId] = useState("");
  const [classId, setClassId] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAuth = useAuth((s) => s.setAuth);

  // Load schools on mount
  useEffect(() => {
    axios.get(`${API_URL}/public/schools`).then((r) => setSchools(r.data)).catch(() => {});
  }, []);

  // Load classes when school changes
  useEffect(() => {
    setClassId("");
    if (!schoolId) { setClasses([]); return; }
    axios.get(`${API_URL}/public/schools/${schoolId}/classes`)
      .then((r) => setClasses(r.data))
      .catch(() => setClasses([]));
  }, [schoolId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (role === "student" && (!schoolId || !classId)) {
      toast.error("Please select your school and class");
      return;
    }
    setLoading(true);
    try {
      const payload: any = { email, password, full_name: fullName, role };
      if (role === "student") {
        payload.school_id = schoolId;
        payload.class_id = classId;
      }
      const res = await register(payload);
      setAuth(res.access_token, res.user);
      toast.success("Account created!");
      const landing = role === "teacher" || role === "admin" ? "/teacher" : "/tutor";
      router.push(landing);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Create account</h1>

        <input placeholder="Full name" value={fullName}
          onChange={(e) => setFullName(e.target.value)} required
          className="w-full border rounded-lg px-3 py-2" />

        <input type="email" placeholder="Email" value={email}
          onChange={(e) => setEmail(e.target.value)} required
          className="w-full border rounded-lg px-3 py-2" />

        <input type="password" placeholder="Password (min 8 chars)" value={password}
          onChange={(e) => setPassword(e.target.value)} required minLength={8}
          className="w-full border rounded-lg px-3 py-2" />

        <select value={role} onChange={(e) => setRole(e.target.value)}
          className="w-full border rounded-lg px-3 py-2">
          <option value="student">Student</option>
          <option value="teacher">Teacher</option>
          <option value="parent">Parent</option>
        </select>

        {role === "student" && (
          <>
            <select value={schoolId} onChange={(e) => setSchoolId(e.target.value)}
              className="w-full border rounded-lg px-3 py-2" required>
              <option value="">— Select your school —</option>
              {schools.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.board})</option>
              ))}
            </select>

            <select value={classId} onChange={(e) => setClassId(e.target.value)}
              className="w-full border rounded-lg px-3 py-2" required disabled={!schoolId}>
              <option value="">— Select your class —</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>Class {c.grade}</option>
              ))}
            </select>
          </>
        )}

        <button disabled={loading}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
          {loading ? "Creating…" : "Create account"}
        </button>

        <p className="text-sm text-center text-gray-600">
          Already registered?{" "}
          <Link href="/login" className="text-indigo-600 hover:underline">Login</Link>
        </p>
      </form>
    </div>
  );
}
