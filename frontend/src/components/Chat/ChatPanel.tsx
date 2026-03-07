import { useState, useRef, useEffect, useCallback } from "react";
import { Bot, Sparkles, Volume2, VolumeX } from "lucide-react";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";
import { api, ChatMessage } from "../../services/api";

const quickActions = [
  "What are today's mandi prices?",
  "Weather forecast for my area",
  "Suggest crops for this season",
  "Government schemes for farmers",
];

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const ttsSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const speakText = useCallback((text: string) => {
    if (!ttsSupported || !voiceEnabled) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    // Try to pick a Hindi voice if the text contains Devanagari, else default
    const voices = window.speechSynthesis.getVoices();
    const hasHindi = /[\u0900-\u097F]/.test(text);
    if (hasHindi) {
      const hindiVoice = voices.find((v) => v.lang.startsWith("hi"));
      if (hindiVoice) utterance.voice = hindiVoice;
      utterance.lang = "hi-IN";
    } else {
      const enVoice = voices.find((v) => v.lang.startsWith("en") && v.name.includes("Google"));
      if (enVoice) utterance.voice = enVoice;
      utterance.lang = "en-IN";
    }
    window.speechSynthesis.speak(utterance);
  }, [ttsSupported, voiceEnabled]);

  const handleSend = async (text: string, imageFile?: File) => {
    // Stop any ongoing TTS when user sends a new message
    if (ttsSupported) window.speechSynthesis.cancel();

    let imageKey: string | undefined;
    let imagePreview: string | undefined;

    if (imageFile) {
      // Create preview URL for display in chat history
      const reader = new FileReader();
      imagePreview = await new Promise<string>((resolve) => {
        reader.onloadend = () => resolve(reader.result as string);
        reader.readAsDataURL(imageFile);
      });

      try {
        const uploadResult = await api.uploadImage(imageFile);
        imageKey = uploadResult.s3_key;
      } catch {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: "Failed to upload image. Please try again.",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        return;
      }
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: text,
      image_key: imageKey,
      image_preview: imagePreview,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const response = await api.sendChatMessage(text, imageKey, history);
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.response,
        tools_used: response.tools_used,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      // Auto-speak the response
      speakText(response.response);
    } catch {
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "I'm sorry, I encountered an error. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleVoice = () => {
    if (voiceEnabled && ttsSupported) {
      window.speechSynthesis.cancel();
    }
    setVoiceEnabled(!voiceEnabled);
  };

  return (
    <div className="flex flex-col h-full bg-stone-50">
      {/* Chat header */}
      <div className="bg-white border-b border-gray-200 px-5 py-3 flex items-center gap-3">
        <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-primary-700" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-900">Agri-Mitra Assistant</h3>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
            <span className="text-xs text-gray-500">Online</span>
          </div>
        </div>
        {ttsSupported && (
          <button
            onClick={toggleVoice}
            className={`p-2 rounded-lg transition-colors ${
              voiceEnabled
                ? "text-primary-600 bg-primary-50 hover:bg-primary-100"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            }`}
            title={voiceEnabled ? "Disable voice responses" : "Enable voice responses"}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-sm animate-fade-in">
              <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                How can I help you today?
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                Ask about crop prices, weather, government policies, or upload a crop image for diagnosis.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {quickActions.map((action) => (
                  <button
                    key={action}
                    onClick={() => handleSend(action)}
                    className="text-left text-xs bg-white border border-gray-200 rounded-xl px-3 py-2.5 text-gray-700 hover:border-primary-300 hover:bg-primary-50 transition-all duration-150"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className="animate-fade-in">
            <MessageBubble message={msg} />
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-3 animate-fade-in">
            <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-500" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
