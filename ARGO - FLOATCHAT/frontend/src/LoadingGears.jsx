import React from "react";

export default function LoadingGears() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#FFF1F1]">
      <div className="relative w-32 h-32">
        {/* Gear 1 */}
        <div className="absolute top-0 left-0 w-12 h-12 border-4 border-blue-600 rounded-full animate-spin-slow origin-center"></div>

        {/* Gear 2 */}
        <div className="absolute top-4 left-4 w-12 h-12 border-4 border-[#3B0270] rounded-full animate-spin origin-center"></div>

        {/* Gear 3 */}
        <div className="absolute top-8 left-8 w-12 h-12 border-4 border-purple-400 rounded-full animate-spin-reverse origin-center"></div>
      </div>
      <p className="mt-6 text-[#3B0270] font-medium text-lg">
        Under Development...
      </p>
    </div>
  );
}
