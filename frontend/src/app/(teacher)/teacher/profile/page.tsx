import { ProfileForm } from "@/components/profile/ProfileForm";
import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";

export default function TeacherProfilePage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">My Account</h1>
      <ProfileForm />
      <ChangePasswordForm />
    </div>
  );
}
