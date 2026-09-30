import Sidebar from "@/components/Sidebar";

export default function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      {children}
    </div>
  );
}