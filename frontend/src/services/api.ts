const BASE_URL = "https://2j6vbtud08.execute-api.ap-south-1.amazonaws.com/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  image_key?: string;
  image_preview?: string; // Base64 data URL for displaying uploaded images
  tools_used?: string[];
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  tools_used: string[];
  farmer_id: string;
}

export interface DashboardPrices {
  crop_name: string;
  market_name: string;
  price_per_quintal: number;
  date: string;
  state: string;
}

export interface WeatherData {
  district: string;
  date: string;
  temperature_min: number;
  temperature_max: number;
  humidity: number;
  rainfall_mm: number;
  description: string;
  agricultural_advisory: string;
}

export interface NewsItem {
  title: string;
  summary: string;
  source_url: string;
  category: string;
  timestamp: string;
  relevance_tags: string[];
}

export interface UploadResponse {
  s3_key: string;
  filename: string;
}

export const api = {
  async sendChatMessage(
    message: string,
    imageKey?: string,
    history?: { role: string; content: string }[]
  ): Promise<ChatResponse> {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, image_key: imageKey, history }),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
    return res.json();
  },

  async uploadImage(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },

  async getDashboardPrices(): Promise<DashboardPrices[]> {
    const res = await fetch(`${BASE_URL}/dashboard/prices`);
    if (!res.ok) throw new Error(`Prices failed: ${res.status}`);
    return res.json();
  },

  async getDashboardWeather(): Promise<WeatherData> {
    const res = await fetch(`${BASE_URL}/dashboard/weather`);
    if (!res.ok) throw new Error(`Weather failed: ${res.status}`);
    return res.json();
  },

  async getDashboardNews(): Promise<NewsItem[]> {
    const res = await fetch(`${BASE_URL}/dashboard/news`);
    if (!res.ok) throw new Error(`News failed: ${res.status}`);
    return res.json();
  },
};
