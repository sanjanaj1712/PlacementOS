import AuthGuard from "@/components/AuthGuard";
import Sidebar from "@/components/Sidebar";

export default function AppLayout({ children }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        {children}
      </div>
    </AuthGuard>
  );
}
