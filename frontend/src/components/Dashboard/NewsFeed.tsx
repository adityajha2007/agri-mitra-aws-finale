import { Newspaper, ExternalLink } from "lucide-react";
import { NewsItem } from "../../services/api";

interface NewsFeedProps {
  news: NewsItem[];
}

export default function NewsFeed({ news }: NewsFeedProps) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-orange-500" />
          <h3 className="text-sm font-semibold text-gray-900">Agri News</h3>
        </div>
        <span className="text-xs text-gray-400">{news.length} articles</span>
      </div>

      {news.length === 0 ? (
        <p className="text-sm text-gray-400">No news available</p>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto scrollbar-thin">
          {news.slice(0, 10).map((item, idx) => (
            <div key={idx} className="group">
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2 text-sm font-medium text-gray-900 group-hover:text-primary-700 transition-colors"
              >
                <span className="flex-1 line-clamp-2">{item.title}</span>
                <ExternalLink className="w-3.5 h-3.5 text-gray-300 group-hover:text-primary-500 flex-shrink-0 mt-0.5" />
              </a>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {item.summary}
              </p>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <span className="text-xs text-gray-400">
                  {new Date(item.timestamp).toLocaleDateString("en-IN")}
                </span>
                {item.relevance_tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full font-medium"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
