import React from "react";

export default function MapPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#FFF1F1] p-6">
      <h1 className="text-2xl font-bold mb-6 text-[#3B0270]">Map View</h1>
      <img
        src="/map-placeholder.png"
        alt="Map"
        className="max-w-full rounded-xl shadow-lg border border-[#3B0270]"
      />
      <p className="mt-4 text-gray-700">This is your map display.</p>
    </div>
  );
}
