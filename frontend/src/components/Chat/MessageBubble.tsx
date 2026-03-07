import { Bot, User } from "lucide-react";
import { ChatMessage } from "../../services/api";

interface MessageBubbleProps {
  message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? "bg-primary-100" : "bg-gray-100"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-primary-700" />
        ) : (
          <Bot className="w-4 h-4 text-gray-600" />
        )}
      </div>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary-600 text-white"
            : "bg-white border border-gray-200 border-l-2 border-l-primary-400 text-gray-800"
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        {message.tools_used && message.tools_used.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.tools_used.map((tool) => (
              <span
                key={tool}
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  isUser
                    ? "bg-white/20 text-white/90"
                    : "bg-primary-50 text-primary-700"
                }`}
              >
                {tool}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
