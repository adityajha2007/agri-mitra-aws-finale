import { CloudSun, Droplets, Thermometer, CloudRain } from "lucide-react";
import { WeatherData } from "../../services/api";

interface WeatherWidgetProps {
  weather: WeatherData | null;
}

export default function WeatherWidget({ weather }: WeatherWidgetProps) {
  if (!weather) {
    return (
      <div className="card p-5">
        <p className="text-sm text-gray-400">No weather data available</p>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CloudSun className="w-5 h-5 text-sky-500" />
          <h3 className="text-sm font-semibold text-gray-900">Weather</h3>
        </div>
        <span className="text-xs text-gray-400">{weather.district} &middot; {weather.date}</span>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="text-3xl font-bold text-gray-900">
          {weather.temperature_max}&deg;
        </div>
        <div className="text-sm text-gray-500">
          <span className="text-gray-400">Low </span>
          {weather.temperature_min}&deg;C
        </div>
        <div className="ml-auto text-sm font-medium text-gray-600">
          {weather.description}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-sky-50 rounded-xl p-3 text-center">
          <Thermometer className="w-4 h-4 text-sky-600 mx-auto mb-1" />
          <p className="text-xs text-gray-500">Feels like</p>
          <p className="text-sm font-semibold text-gray-800">{weather.temperature_max}&deg;</p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3 text-center">
          <Droplets className="w-4 h-4 text-blue-600 mx-auto mb-1" />
          <p className="text-xs text-gray-500">Humidity</p>
          <p className="text-sm font-semibold text-gray-800">{weather.humidity}%</p>
        </div>
        <div className="bg-indigo-50 rounded-xl p-3 text-center">
          <CloudRain className="w-4 h-4 text-indigo-600 mx-auto mb-1" />
          <p className="text-xs text-gray-500">Rainfall</p>
          <p className="text-sm font-semibold text-gray-800">{weather.rainfall_mm}mm</p>
        </div>
      </div>

      {weather.agricultural_advisory && (
        <div className="bg-primary-50 border border-primary-100 rounded-xl p-3">
          <p className="text-xs font-semibold text-primary-800 mb-1">Advisory</p>
          <p className="text-sm text-primary-700 leading-relaxed">
            {weather.agricultural_advisory}
          </p>
        </div>
      )}
    </div>
  );
}
