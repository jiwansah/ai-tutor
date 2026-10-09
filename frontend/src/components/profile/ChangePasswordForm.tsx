"use client";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export function ChangePasswordForm() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirm) {
      toast.error("New password and confirmation do not match");
      return;
    }
    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/change-password", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      toast.success("Password updated");
      setOldPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to change password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border bg-white p-6 space-y-4">
      <h2 className="font-semibold text-lg">Change password</h2>

      <div className="space-y-1">
        <label className="text-sm text-gray-600">Current password</label>
        <input type="password" value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)} required
          className="w-full border rounded-lg px-3 py-2 text-sm" />
      </div>

      <div className="space-y-1">
        <label className="text-sm text-gray-600">New password</label>
        <input type="password" value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)} required minLength={8}
          className="w-full border rounded-lg px-3 py-2 text-sm" />
        <p className="text-xs text-gray-400">At least 8 characters</p>
      </div>

      <div className="space-y-1">
        <label className="text-sm text-gray-600">Confirm new password</label>
        <input type="password" value={confirm}
          onChange={(e) => setConfirm(e.target.value)} required
          className="w-full border rounded-lg px-3 py-2 text-sm" />
      </div>

      <div className="flex justify-end">
        <button disabled={loading}
          className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50">
          {loading ? "Updating…" : "Change password"}
        </button>
      </div>
    </form>
  );
}
