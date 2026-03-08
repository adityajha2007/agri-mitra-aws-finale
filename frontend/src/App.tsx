import { useState, useEffect } from "react";
import { LayoutDashboard, MessageSquare, MapPin } from "lucide-react";
import DashboardPanel from "./components/Dashboard/DashboardPanel";
import ChatPanel from "./components/Chat/ChatPanel";
import agrimitraLogo from "./agrimitra_logo.png";

const DISTRICTS = [
  "Lucknow", "Pune", "Mumbai", "Jaipur", "Bhopal", "Varanasi",
  "Nagpur", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
  "Patna", "Indore", "Nashik", "Agra"
];

export default function App() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "chat">("chat");
  const [isMobile, setIsMobile] = useState(false);
  const [selectedDistrict, setSelectedDistrict] = useState<string>(() => {
    return localStorage.getItem("selectedDistrict") || "Bangalore";
  });

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 1024);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    localStorage.setItem("selectedDistrict", selectedDistrict);
  }, [selectedDistrict]);

  return (
    <div className="h-screen flex flex-col bg-stone-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary-800 to-primary-700 px-6 py-3 flex items-center gap-3 shadow-md">
        <img 
          src={agrimitraLogo} 
          alt="Agri-Mitra Logo" 
          className="w-9 h-9 rounded-lg object-contain bg-white/10 backdrop-blur p-1"
        />
        <div className="flex-1">
          <h1 className="text-white font-bold text-lg leading-tight">Agri-Mitra</h1>
          <p className="text-primary-200 text-xs">Built for Farmers</p>
        </div>
        
        {/* District Selector */}
        <div className="flex items-center gap-2 bg-white/10 backdrop-blur rounded-lg px-3 py-1.5">
          <MapPin className="w-4 h-4 text-white" />
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="bg-transparent text-white text-sm font-medium border-none outline-none cursor-pointer"
          >
            {DISTRICTS.map((district) => (
              <option key={district} value={district} className="text-gray-900">
                {district}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {!isMobile ? (
          <>
            <div className="w-2/5 border-r border-gray-200 overflow-hidden">
              <DashboardPanel district={selectedDistrict} />
            </div>
            <div className="w-3/5 overflow-hidden">
              <ChatPanel district={selectedDistrict} />
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-hidden">
            {activeTab === "dashboard" ? (
              <DashboardPanel district={selectedDistrict} />
            ) : (
              <ChatPanel district={selectedDistrict} />
            )}
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
