import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold text-indigo-600 mb-4">AI Tutor</h1>
      <p className="text-gray-600 mb-8">Personalized learning for every student</p>
      <div className="flex gap-3">
        <Link href="/login" className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          Login
        </Link>
        <Link href="/register" className="px-6 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50">
          Register
        </Link>
      </div>
    </main>
  );
}
