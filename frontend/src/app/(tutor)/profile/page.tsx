import { ProfileForm } from "@/components/profile/ProfileForm";
import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";

export default function StudentProfilePage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-6">
        <h1 className="text-2xl font-bold">My Account</h1>
        <ProfileForm />
        <ChangePasswordForm />
      </div>
    </div>
  );
}
