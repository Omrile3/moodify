import React from "react";
import { motion } from "framer-motion";
import { Bot, User } from "lucide-react";

export default function ChatMessage({ message, isBot }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`flex gap-3 ${isBot ? "justify-start" : "justify-end"}`}
    >
      {isBot && (
        <div className="clay-element bg-gradient-to-br from-purple-200 to-pink-200 p-3 w-fit">
          <Bot className="w-5 h-5 text-purple-600" />
        </div>
      )}
      
      <div
        className={`max-w-md clay-element p-4 ${
          isBot
            ? "bg-gradient-to-br from-white to-purple-50"
            : "bg-gradient-to-br from-blue-200 to-purple-200"
        }`}
      >
        <p className={`text-sm leading-relaxed ${
          isBot ? "text-gray-700" : "text-gray-800 font-medium"
        }`}>
          {message.message}
        </p>
        <p className="text-xs text-gray-500 mt-2">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
          })}
        </p>
      </div>
      
      {!isBot && (
        <div className="clay-element bg-gradient-to-br from-blue-200 to-mint-200 p-3 w-fit">
          <User className="w-5 h-5 text-blue-600" />
        </div>
      )}
    </motion.div>
  );
}