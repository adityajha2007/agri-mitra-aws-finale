import { useState, useEffect } from "react";
import { Sprout, LayoutDashboard, MessageSquare } from "lucide-react";
import DashboardPanel from "./components/Dashboard/DashboardPanel";
import ChatPanel from "./components/Chat/ChatPanel";

export default function App() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "chat">("chat");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 1024);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-stone-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary-800 to-primary-700 px-6 py-3 flex items-center gap-3 shadow-md">
        <div className="w-9 h-9 bg-white/15 backdrop-blur rounded-lg flex items-center justify-center">
          <Sprout className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-white font-bold text-lg leading-tight">Agri-Mitra</h1>
          <p className="text-primary-200 text-xs">Your Agricultural Assistant</p>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {!isMobile ? (
          <>
            <div className="w-2/5 border-r border-gray-200 overflow-hidden">
              <DashboardPanel />
            </div>
            <div className="w-3/5 overflow-hidden">
              <ChatPanel />
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-hidden">
            {activeTab === "dashboard" ? <DashboardPanel /> : <ChatPanel />}
          </div>
        )}
      </div>

      {/* Mobile bottom tab bar */}
      {isMobile && (
        <nav className="bg-white border-t border-gray-200 flex">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex-1 flex flex-col items-center py-2.5 gap-1 text-xs font-medium transition-colors ${
              activeTab === "dashboard"
                ? "text-primary-700 border-t-2 border-primary-600 -mt-px"
                : "text-gray-400"
            }`}
          >
            <LayoutDashboard className="w-5 h-5" />
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex-1 flex flex-col items-center py-2.5 gap-1 text-xs font-medium transition-colors ${
              activeTab === "chat"
                ? "text-primary-700 border-t-2 border-primary-600 -mt-px"
                : "text-gray-400"
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            Chat
          </button>
        </nav>
      )}
    </div>
  );
}
