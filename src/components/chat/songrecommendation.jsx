import React from "react";
import { Music } from "lucide-react";
import { motion } from "framer-motion";

export default function SongRecommendation({ song, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="clay-element bg-gradient-to-br from-white to-mint-50 p-4"
    >
      <div className="flex items-start gap-3">
        <div className="clay-element bg-gradient-to-br from-mint-200 to-blue-200 p-3 flex-shrink-0">
          <Music className="w-5 h-5 text-mint-600" />
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="font-bold text-gray-800 truncate">{song.title}</h4>
          <p className="text-sm text-gray-600 truncate">{song.artist}</p>
          {song.album && (
            <p className="text-xs text-gray-500 truncate mt-1">{song.album}</p>
          )}
          
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-xs bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 px-2 py-1 rounded-full">
              {song.genre}
            </span>
            {song.subgenre && (
              <span className="text-xs bg-gradient-to-r from-blue-100 to-mint-100 text-blue-700 px-2 py-1 rounded-full">
                {song.subgenre}
              </span>
            )}
            {song.mood && (
              <span className="text-xs bg-gradient-to-r from-pink-100 to-purple-100 text-pink-700 px-2 py-1 rounded-full">
                {song.mood}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}