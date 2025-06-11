import React from "react";
import { motion } from "framer-motion";
import { Loader2, Music } from "lucide-react";

export default function LoadingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex items-center gap-3 clay-element bg-gradient-to-br from-white to-purple-50 p-4 w-fit"
    >
      <div className="clay-element bg-gradient-to-br from-purple-200 to-pink-200 p-3">
        <Music className="w-5 h-5 text-purple-600" />
      </div>
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
        <span className="text-sm text-gray-600">Thinking about music...</span>
      </div>
    </motion.div>
  );
}