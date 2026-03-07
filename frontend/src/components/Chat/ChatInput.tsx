import { useState, useRef, useEffect } from "react";
import { Send, ImagePlus, X, Mic, MicOff } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string, imageFile?: File) => void;
  disabled: boolean;
}

// TypeScript declarations for Web Speech API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

type SpeechRecognitionType = new () => {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
};

function getSpeechRecognition(): SpeechRecognitionType | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as SpeechRecognitionType | null;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<InstanceType<SpeechRecognitionType> | null>(null);

  const speechSupported = !!getSpeechRecognition();

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "hi-IN"; // Hindi + English auto-detected

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setText(transcript);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() && !imageFile) return;
    recognitionRef.current?.stop();
    setIsListening(false);
    onSend(text.trim(), imageFile || undefined);
    setText("");
    setImageFile(null);
    setImagePreview(null);
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setImagePreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white border-t border-gray-200 p-4">
      {imagePreview && (
        <div className="mb-3 relative inline-block animate-fade-in">
          <img
            src={imagePreview}
            alt="Upload preview"
            className="h-16 w-16 object-cover rounded-xl border border-gray-200"
          />
          <button
            type="button"
            onClick={removeImage}
            className="absolute -top-1.5 -right-1.5 bg-gray-800 text-white rounded-full p-0.5 hover:bg-red-500 transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
      <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-2xl px-3 py-1.5 focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
        <input
          type="file"
          ref={fileInputRef}
          accept="image/*"
          onChange={handleImageSelect}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="p-1.5 text-gray-400 hover:text-primary-600 transition-colors rounded-lg hover:bg-white"
          disabled={disabled}
        >
          <ImagePlus className="w-5 h-5" />
        </button>
        {speechSupported && (
          <button
            type="button"
            onClick={toggleListening}
            className={`p-1.5 transition-colors rounded-lg ${
              isListening
                ? "text-red-500 bg-red-50 animate-pulse"
                : "text-gray-400 hover:text-primary-600 hover:bg-white"
            }`}
            disabled={disabled}
            title={isListening ? "Stop listening" : "Voice input"}
          >
            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
        )}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={isListening ? "Listening..." : "Ask about crops, prices, weather..."}
          className="flex-1 bg-transparent text-sm py-2 focus:outline-none placeholder:text-gray-400"
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={disabled || (!text.trim() && !imageFile)}
          className="p-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      {isListening && (
        <p className="text-xs text-red-500 mt-1.5 ml-1 animate-pulse">
          Listening... speak now
        </p>
      )}
    </form>
  );
}
