import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
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
        {/* Image preview for user messages with uploaded images */}
        {isUser && message.image_preview && (
          <div className="mb-3">
            <img
              src={message.image_preview}
              alt="Uploaded crop"
              className="max-w-full h-auto max-h-64 rounded-lg border border-white/20"
            />
          </div>
        )}
        
        {/* Render markdown for assistant messages, plain text for user */}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="text-sm leading-relaxed prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-800 prose-strong:text-gray-900 prose-ul:text-gray-800 prose-ol:text-gray-800 prose-li:text-gray-800">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        
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
