import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import PriceTicker from "./PriceTicker";
import WeatherWidget from "./WeatherWidget";
import NewsFeed from "./NewsFeed";
import { api, DashboardPrices, WeatherData, NewsItem } from "../../services/api";

interface DashboardPanelProps {
  district: string;
}

export default function DashboardPanel({ district }: DashboardPanelProps) {
  const [prices, setPrices] = useState<DashboardPrices[]>([]);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDashboard() {
      setLoading(true);
      setError(null);
      try {
        const [pricesData, weatherData, newsData] = await Promise.all([
          api.getDashboardPrices(district),
          api.getDashboardWeather(district),
          api.getDashboardNews(),
        ]);
        setPrices(pricesData);
        setWeather(weatherData);
        setNews(newsData);
      } catch (err) {
        setError("Failed to load dashboard data. Please refresh.");
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchDashboard();
  }, [district]);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-5 space-y-4 scrollbar-thin">
        <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="card p-5 space-y-3">
          <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
          <div className="h-20 bg-gray-100 rounded animate-pulse" />
        </div>
        <div className="card p-5 space-y-3">
          <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
        <div className="card p-5 space-y-3">
          <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
          {[1, 2].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-5 space-y-4 scrollbar-thin">
      <div className="animate-fade-in">
        <h2 className="text-xl font-bold text-gray-900">{greeting()}</h2>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm animate-fade-in">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="space-y-4 animate-slide-up">
        <WeatherWidget weather={weather} />
        <PriceTicker prices={prices} />
        <NewsFeed news={news} />
      </div>
    </div>
  );
}
