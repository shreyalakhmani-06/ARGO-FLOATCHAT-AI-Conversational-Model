import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Chatbot from "./Chatbot";
import AuthPage from "./AuthPage";
import MapPage from "./MapPage";
import GenerateAPI from "./GenerateAPI";
import AnomalyAlerts from "./AnomalyAlerts";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatbotLayout />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/anomaly-alerts" element={<AnomalyAlerts />} />
        <Route path="/generate-api" element={<GenerateAPI />} />
      </Routes>
    </Router>
  );
}

// Layout with Sidebar + Chatbot
function ChatbotLayout() {
  return (
    <div className="flex h-screen w-screen text-gray-800">
      {/* Sidebar */}
      <aside
        className="hidden md:flex flex-col w-1/4 p-6 justify-between"
        style={{ backgroundColor: "#3B0270", color: "white" }}
      >
        <div>
          <h1 className="text-2xl font-bold mb-6">FloatChat 🌊</h1>
          <p className="text-sm opacity-90 mb-6">
            Explore float data interactively. Ask me about temperature, salinity,
            depth, or request plots.
          </p>
          <nav className="flex flex-col space-y-3 text-sm">
          <a
            href="/anomaly-alerts"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full block px-4 py-3 rounded-lg bg-[#4A0F8C] hover:bg-[#2B0050] transition-colors text-white text-center"
          >
          Anomaly Alerts
           </a>
          <a
            href="/generate-api"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full block px-4 py-3 rounded-lg bg-[#4A0F8C] hover:bg-[#2B0050] transition-colors text-white text-center"
          >
            Generate API
          </a>
          <a
            href="https://incois.gov.in/OON/index.jsp"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full block px-4 py-3 rounded-lg bg-[#4A0F8C] hover:bg-[#2B0050] transition-colors text-white text-center"
          >
            Show Map
          </a>
          </nav>


        
        </div>

        <div className="flex flex-col space-y-3 text-sm">
          <a
            href="/auth"
            target="_blank"
            className="w-full px-4 py-3 rounded-lg border border-white hover:bg-white hover:text-[#3B0270] transition-colors text-center"
          >
            Login / Signup
          </a>
          
        </div>
      </aside>
        
      {/* Chatbot */}
      <div className="flex flex-col flex-1 h-full">
        <header
          className="md:hidden text-white text-center py-3"
          style={{ backgroundColor: "#3B0270" }}
        >
          <h1 className="text-lg font-bold"> FloatChat 🌊</h1>
        </header>
        <Chatbot />
      </div>
    </div>
  );
}
