
// import React, { useState, useEffect, useRef } from "react";
// import Plot from "react-plotly.js";
// import Plotly from "plotly.js-basic-dist-min";

// export default function Chatbot() {
//   const [messages, setMessages] = useState([
//     { sender: "bot", text: "Hello! Ask me about float data 🚢", time: new Date() },
//   ]);
//   const [input, setInput] = useState("");
//   const [isTyping, setIsTyping] = useState(false); // Typing indicator
//   const chatEndRef = useRef(null);
//   const plotRefs = useRef({});

//   useEffect(() => {
//     chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages, isTyping]);

//   useEffect(() => {
//     Object.values(plotRefs.current).forEach((plotRef) => {
//       if (plotRef && plotRef.el) {
//         Plotly.Plots.resize(plotRef.el);
//       }
//     });
//   }, [messages]);

//   const handleSend = async () => {
//     if (!input.trim()) return;

//     const userMessage = { sender: "user", text: input, time: new Date() };
//     setMessages((prev) => [...prev, userMessage]);
//     setInput("");
//     setIsTyping(true);

//     try {
//       const response = await fetch("http://127.0.0.1:8000/chat", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ query: input }),
//       });
//       const data = await response.json();
//       setIsTyping(false);

//       let botMsg = { sender: "bot", text: "", time: new Date() };

//       if (data.visualization && data.visualization.figure) {
//         const fig = data.visualization.figure;
//         if (fig && Array.isArray(fig.data) && fig.data.length > 0) {
//           botMsg.text = "Here’s the plot:";
//           botMsg.plot = fig;
//         } else {
//           botMsg.text = "No plot data available.";
//         }
//       } else if (data.values) {
//         // Card style structured data
//         botMsg.values = data.values;
//         botMsg.platform_number = data.platform_number;
//         botMsg.closest_depth = data.closest_depth;
//       } else if (data.response) {
//         botMsg.text = data.response;
//       } else if (data.count !== undefined) {
//         botMsg.text = `Found ${data.count} records for your query.`;
//       } else {
//         botMsg.text = data.error || "Something went wrong.";
//         botMsg.error = true; // For error bubble
//       }

//       setMessages((prev) => [...prev, botMsg]);
//     } catch (error) {
//       console.error(error);
//       setIsTyping(false);
//       setMessages((prev) => [
//         ...prev,
//         {
//           sender: "bot",
//           text: `Error: ${error.message}`,
//           time: new Date(),
//           error: true, // Red bubble for errors
//         },
//       ]);
//     }
//   };

//   const getPlotHeight = (plot) => {
//     if (!plot || !plot.data) return 400;
//     return Math.min(800, 150 + plot.data.length * 200);
//   };

//   const formatTime = (date) => {
//     return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
//   };

//   return (
//     <div
//       className="flex flex-col flex-1 h-full"
//       style={{
//         backgroundColor: "#FFF1F1",
//         scrollbarWidth: "thin",
//         scrollbarColor: "#A97CFF #FFF1F1",
//       }}
//     >
//       {/* Messages */}
//       <div
//         className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
//         style={{
//           scrollbarWidth: "thin",
//         }}
//       >
//         {messages.map((msg, idx) => (
//           <div
//             key={idx}
//             className={`flex items-start gap-3 max-w-2xl ${
//               msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
//             }`}
//           >
//             {/* Avatar */}
//             <div
//               className={`flex items-center justify-center w-10 h-10 rounded-full ${
//                 msg.sender === "user"
//                   ? "bg-[#3B0270] text-white"
//                   : msg.error
//                   ? "bg-red-600 text-white"
//                   : "bg-white border border-[#3B0270] text-[#3B0270]"
//               }`}
//             >
//               {msg.sender === "user" ? "👤" : "🤖"}
//             </div>

//             {/* Message Bubble */}
//             <div
//               className={`p-4 rounded-2xl ${
//                 msg.sender === "user"
//                   ? "bg-[#3B0270] text-white"
//                   : msg.error
//                   ? "bg-red-100 text-red-700 border border-red-400"
//                   : "bg-white border border-[#3B0270] text-gray-800"
//               }`}
//             >
//               {/* If structured data exists */}
//               {msg.values ? (
//                 <div className="space-y-2">
//                   {Object.entries(msg.values).map(([k, v]) => (
//                     <div
//                       key={k}
//                       className="p-2 border border-gray-300 rounded flex justify-between text-sm bg-gray-50"
//                     >
//                       <span className="font-medium text-gray-700">{k}</span>
//                       <span className="text-gray-900">{v}</span>
//                     </div>
//                   ))}
//                   {msg.platform_number && (
//                     <div className="text-xs mt-1 opacity-70">
//                       Platform: {msg.platform_number}, Closest Depth: {msg.closest_depth} dbar
//                     </div>
//                   )}
//                 </div>
//               ) : (
//                 msg.text && <div>{msg.text}</div>
//               )}

//               {/* Timestamp */}
//               <span className="block text-xs opacity-50 mt-1 text-right">
//                 {formatTime(msg.time)}
//               </span>

//               {/* Plot */}
//               {msg.plot && msg.plot.data && msg.plot.data.length > 0 && (
//                 <div
//                   className="mt-3 rounded-xl overflow-hidden border border-[#3B0270]"
//                   style={{
//                     width: "100%",
//                     minHeight: 350,
//                     height: getPlotHeight(msg.plot),
//                   }}
//                 >
//                   <Plot
//                     ref={(el) => (plotRefs.current[idx] = el)}
//                     data={msg.plot.data}
//                     layout={{
//                       ...msg.plot.layout,
//                       autosize: true,
//                       height: getPlotHeight(msg.plot),
//                       margin: { l: 70, r: 50, t: 50, b: 70 },
//                       paper_bgcolor: "#FFF1F1",
//                       plot_bgcolor: "#FFF1F1",
//                       font: { family: "Inter, sans-serif", size: 14 },
//                     }}
//                     useResizeHandler={true}
//                     style={{ width: "100%", height: "100%" }}
//                     config={{ responsive: true }}
//                   />
//                 </div>
//               )}
//             </div>
//           </div>
//         ))}

//         {/* Typing Indicator */}
//         {isTyping && (
//           <div className="flex items-start gap-3 max-w-2xl mr-auto animate-pulse">
//             <div className="flex items-center justify-center w-10 h-10 rounded-full bg-white border border-[#3B0270] text-[#3B0270]">
//               🤖
//             </div>
//             <div className="p-4 rounded-2xl border border-[#3B0270] bg-white text-gray-600 text-sm">
//               FloatChat is responding...
//             </div>
//           </div>
//         )}

//         <div ref={chatEndRef} />
//       </div>

//       {/* Input Area */}
//       <div className="flex items-center p-4 border-t border-gray-300" style={{ backgroundColor: "#FFF1F1" }}>
//         <input
//           type="text"
//           className="flex-1 p-3 rounded-l-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#3B0270]"
//           value={input}
//           onChange={(e) => setInput(e.target.value)}
//           onKeyDown={(e) => e.key === "Enter" && handleSend()}
//           placeholder="Type your message..."
//         />
//         <button
//           className="text-white px-6 py-3 rounded-r-full font-medium"
//           style={{ backgroundColor: "#3B0270" }}
//           onClick={handleSend}
//         >
//           Send
//         </button>
//       </div>
//     </div>
//   );
// }


import React, { useState, useEffect, useRef } from "react";
import Plot from "react-plotly.js";
import Plotly from "plotly.js-basic-dist-min";

export default function Chatbot() {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! Ask me about float data 🚢", time: new Date() },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);
  const plotRefs = useRef({});

  // Scroll to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Resize plots when messages change
  useEffect(() => {
    Object.values(plotRefs.current).forEach((plotRef) => {
      if (plotRef && plotRef.el) {
        Plotly.Plots.resize(plotRef.el);
      }
    });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input, time: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });
      const data = await response.json();
      setIsTyping(false);

            let botMsg = { sender: "bot", text: data.response || "", time: new Date() };

      const figs = [];
      if (data.visualization && data.visualization.figure) figs.push(data.visualization.figure);
      if (data.visualizations) {
        Object.values(data.visualizations).forEach((v) => v && v.figure && figs.push(v.figure));
      }
      const valid = figs.filter((f) => f && Array.isArray(f.data) && f.data.length > 0);

      if (valid.length > 0) {
        botMsg.plots = valid;
        if (!botMsg.text) botMsg.text = "Here’s the plot:";
      } else if (!botMsg.text) {
        botMsg.text = data.error || "Something went wrong.";
        botMsg.error = true;
      }

      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error(error);
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Error: ${error.message}`,
          time: new Date(),
          error: true,
        },
      ]);
    }
  };

   const getPlotHeight = () => 420;

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div
      className="flex flex-col flex-1 h-full"
      style={{ backgroundColor: "#FFF1F1", scrollbarWidth: "thin", scrollbarColor: "#A97CFF #FFF1F1" }}
    >
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-3 max-w-2xl ${
              msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            }`}
          >
            {/* Avatar */}
            <div
              className={`flex items-center justify-center w-10 h-10 rounded-full ${
                msg.sender === "user"
                  ? "bg-[#3B0270] text-white"
                  : msg.error
                  ? "bg-red-600 text-white"
                  : "bg-white border border-[#3B0270] text-[#3B0270]"
              }`}
            >
              {msg.sender === "user" ? "👤" : "🤖"}
            </div>

            {/* Message Bubble */}
            <div
              className={`p-4 rounded-2xl ${
                msg.sender === "user"
                  ? "bg-[#3B0270] text-white"
                  : msg.error
                  ? "bg-red-100 text-red-700 border border-red-400"
                  : "bg-white border border-[#3B0270] text-gray-800"
              }`}
              style={{ width: "100%" }}
            >
              {/* Structured data */}
              {msg.values ? (
                <div className="space-y-2">
                  {Object.entries(msg.values).map(([k, v]) => (
                    <div
                      key={k}
                      className="p-2 border border-gray-300 rounded flex justify-between text-sm bg-gray-50"
                    >
                      <span className="font-medium text-gray-700">{k}</span>
                      <span className="text-gray-900">{v}</span>
                    </div>
                  ))}
                  {msg.platform_number && (
                    <div className="text-xs mt-1 opacity-70">
                      Platform: {msg.platform_number}, Closest Depth: {msg.closest_depth} dbar
                    </div>
                  )}
                </div>
              ) : (
                msg.text && <div style={{ whiteSpace: "pre-line" }}>{msg.text}</div>
              )}

              {/* Timestamp */}
              <span className="block text-xs opacity-50 mt-1 text-right">{formatTime(msg.time)}</span>

              {/* Plot */}
                            {(msg.plots || []).map((plot, pi) => (
                <div
                  key={pi}
                  className="mt-3 rounded-xl overflow-hidden border border-[#3B0270] flex justify-center"
                  style={{ width: "100%", minHeight: 350 }}
                >
                  <Plot
                    ref={(el) => (plotRefs.current[`${idx}-${pi}`] = el)}
                    data={plot.data}
                    layout={{
                      ...plot.layout,
                      autosize: true,
                      width: undefined,
                      height: getPlotHeight(),
                      margin: { l: 70, r: 50, t: 50, b: 70 },
                      paper_bgcolor: "#FFF1F1",
                      plot_bgcolor: "#FFF1F1",
                      font: { family: "Inter, sans-serif", size: 14 },
                    }}
                    useResizeHandler={true}
                    style={{ width: "100%", height: getPlotHeight() }}
                    config={{ responsive: true }}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex items-start gap-3 max-w-2xl mr-auto animate-pulse">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-white border border-[#3B0270] text-[#3B0270]">
              🤖
            </div>
            <div className="p-4 rounded-2xl border border-[#3B0270] bg-white text-gray-600 text-sm">
              FloatChat is responding...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex items-center p-4 border-t border-gray-300" style={{ backgroundColor: "#FFF1F1" }}>
        <input
          type="text"
          className="flex-1 p-3 rounded-l-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#3B0270]"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type your message..."
        />
        <button
          className="text-white px-6 py-3 rounded-r-full font-medium"
          style={{ backgroundColor: "#3B0270" }}
          onClick={handleSend}
        >
          Send
        </button>
      </div>
    </div>
  );
}
