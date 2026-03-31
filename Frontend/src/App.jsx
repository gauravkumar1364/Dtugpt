import { useState } from "react";
import "./App.css";

function App() {
  // 1. State must live INSIDE the functional component
  // 2. Use camelCase to match the variables in your JSX below
  const [isExpanded, setIsExpanded] = useState(false);
  const [input,setinput] = useState("");
  const [messages,setmessages] = useState([]);
  const [isLoading,setisLoading] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState(null);

  const sendMessage = async () => {
    if(!input.trim()) return; // Prevent sending empty messages
    const usermessage = input;
    setmessages((prev)=>[...prev,{role:"user",content:usermessage}]);
    setinput("");
    setisLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: usermessage }),
      });
      const data = await response.json();
      setmessages((prev)=>[...prev,{role:"assistant",content:data.reply, thinking:data.thinking}]);
    }catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setisLoading(false);
    }
  };

  return (
    <div className="bg-[#0b0b0b] text-[#e5e5e5] w-full h-screen flex flex-col">
      <div className="flex flex-1 overflow-hidden font-sans bg-[#0b0b0b]">
        {/* --- Sidebar Container --- */}
        <div
          className={`bg-[#050505] text-white transition-all duration-300 ease-in-out flex flex-col overflow-hidden border-r border-[#161616] shadow-[2px_0_18px_rgba(0,0,0,0.35)] ${
            isExpanded ? "w-64" : "w-16"
          }`}
        >
          {/* Toggle Button Area */}
          <div className="flex items-center justify-center h-16 border-b border-[#161616]">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 rounded-full hover:bg-[#171717]"
              aria-label="Toggle Sidebar"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 flex flex-col gap-2 p-3 mt-4 overflow-y-auto overflow-x-hidden">
            <a
              href="#"
              className="flex items-center gap-4 p-2 rounded-full hover:bg-[#1a1a1a] transition-colors min-w-0"
            >
              <div className="min-w-[24px]">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                  />
                </svg>
              </div>
              <span
                className={`whitespace-nowrap transition-opacity duration-300 ${isExpanded ? "opacity-100" : "opacity-0"}`}
              >
                Dashboard
              </span>
            </a>

            <a
              href="#"
              className="flex items-center gap-4 p-2 rounded-full hover:bg-[#1a1a1a] transition-colors min-w-0"
            >
              <div className="min-w-[24px]">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </div>
              <span
                className={`whitespace-nowrap transition-opacity duration-300 ${isExpanded ? "opacity-100" : "opacity-0"}`}
              >
                Settings
              </span>
            </a>
          </nav>
        </div>

        {/* --- Main Content Area --- */}
        <div className="flex-1 p-5 text-[#d6d6d6] bg-[#111111] text-xl flex flex-col min-w-0">
          <nav className="border-b border-[#252525] mb-5 p-5 shadow-[0_1px_0_0_rgba(255,255,255,0.04)]">
            <ul className="flex justify-between items-center">
              <li className="font-semibold tracking-wide text-sm text-[#bfbfbf]">PROJECT</li>
              <li>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="w-6 h-6 text-[#8a8a8a]"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
                  />
                </svg>
              </li>
            </ul>
          </nav>
          
          {/* Messages Display Area */}
          <div className="flex-1 overflow-y-auto mb-6 pr-2 flex flex-col gap-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <h1 className="text-[#c9c9c9] text-2xl">Hello, how can I help you today?</h1>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className="max-w-xs lg:max-w-md xl:max-w-lg">
                    <div
                      className={`px-4 py-2 rounded-lg ${
                        msg.role === "user"
                          ? "bg-[#1f6feb] text-white rounded-br-none"
                          : "bg-[#2d2d2d] text-[#e5e5e5] rounded-bl-none"
                      }`}
                    >
                      <p className="text-sm break-words">{msg.content}</p>
                    </div>
                    {msg.thinking && (
                      <div className="mt-2 flex items-center">
                        <button
                          onClick={() => setExpandedThinking(expandedThinking === index ? null : index)}
                          className="flex items-center gap-2 text-xs text-[#888888] hover:text-[#aaaaaa] transition-colors"
                        >
                          <svg
                            className={`w-4 h-4 transition-transform ${expandedThinking === index ? "rotate-90" : ""}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                          Show Thinking
                        </button>
                      </div>
                    )}
                    {expandedThinking === index && msg.thinking && (
                      <div className="mt-2 p-3 bg-[#1a1a1a] rounded border border-[#404040] text-xs text-[#999999] break-words">
                        <p className="font-semibold mb-2 text-[#b0b0b0]">Thinking Process:</p>
                        <p>{msg.thinking}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-[#2d2d2d] text-[#e5e5e5] px-4 py-2 rounded-lg rounded-bl-none">
                  <p className="text-sm">Typing...</p>
                </div>
              </div>
            )}
          </div>
          
          <div className="p-4 flex items-center justify-center">
            <div className="flex items-center bg-[#111111] border border-[#1f1f1f] rounded-full w-full max-w-3xl px-4 py-3 gap-3 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
              <input
                type="text"
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setinput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                className="bg-transparent text-white placeholder:text-[#6b6b6b] flex-1 min-w-0 focus:outline-none focus:ring-0 placeholder:text-sm text-sm"
              />
              <button
                type="button"
                className="flex items-center justify-center w-10 h-10 rounded-full bg-[#1c1c1c] hover:bg-[#242424] text-[#cfcfcf] cursor-pointer transition-colors"
                aria-label="Send"
                onClick={sendMessage}
                disabled={isLoading}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="w-5 h-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
