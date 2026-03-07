import { TrendingUp, IndianRupee } from "lucide-react";
import { DashboardPrices } from "../../services/api";

interface PriceTickerProps {
  prices: DashboardPrices[];
}

export default function PriceTicker({ prices }: PriceTickerProps) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-amber-600" />
          <h3 className="text-sm font-semibold text-gray-900">Mandi Prices</h3>
        </div>
        <span className="text-xs text-gray-400">{prices.length} crops</span>
      </div>

      {prices.length === 0 ? (
        <p className="text-sm text-gray-400">No price data available</p>
      ) : (
        <div className="space-y-1 max-h-64 overflow-y-auto scrollbar-thin">
          {prices.slice(0, 20).map((p, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {p.crop_name}
                </p>
                <p className="text-xs text-gray-400 truncate">
                  {p.market_name}, {p.state}
                </p>
              </div>
              <div className="text-right flex-shrink-0 ml-3">
                <div className="flex items-center gap-0.5 text-sm font-bold text-amber-700">
                  <IndianRupee className="w-3.5 h-3.5" />
                  {p.price_per_quintal.toLocaleString("en-IN")}
                </div>
                <p className="text-xs text-gray-400">per quintal</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
