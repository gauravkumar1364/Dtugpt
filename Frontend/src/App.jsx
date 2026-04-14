import { useState, useEffect } from "react";
import "./App.css";
import FileUpload from "./file_upload";
import MessageDisplay from "./MessageDisplay";
import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/react";
import { Analytics } from '@vercel/analytics/react';
function App() {

  const [isExpanded, setIsExpanded] = useState(false);
  const [input,setinput] = useState("");
  const [messages,setmessages] = useState([]);
  const [isLoading,setisLoading] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

  // 📝 Load chat history from localStorage on component mount
  useEffect(() => {
    const savedMessages = localStorage.getItem("chatHistory");
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages);
        setmessages(parsedMessages);
        console.log("✅ Loaded chat history from localStorage");
      } catch (error) {
        console.error("Error loading chat history:", error);
      }
    }
  }, []);

  //  Save chat history to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("chatHistory", JSON.stringify(messages));
      console.log("💾 Chat history saved to localStorage");
    }
  }, [messages]);

  // 🗑️ Clear chat history
  const clearChatHistory = () => {
    if (window.confirm("Are you sure you want to clear all chat history? This cannot be undone.")) {
      setmessages([]);
      localStorage.removeItem("chatHistory");
      setExpandedThinking(null);
      console.log("🗑️  Chat history cleared");
    }
  };

  const sendMessage = async () => {
    if(!input.trim()) return; // Prevent sending empty messages
    const usermessage = input;
    setmessages((prev)=>[...prev,{role:"user",content:usermessage}]);
    setinput("");
    setisLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      const response = await fetch("https://dtugpt.onrender.com/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        signal: controller.signal,
        body: JSON.stringify({ message: usermessage }),
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();
      // Handle both new structured format and legacy string format
      const responseContent = data.reply?.title ? data.reply : (typeof data.reply === 'string' ? data.reply : data.reply?.formatted_markdown || data.reply);
      setmessages((prev)=>[...prev,{role:"assistant",content: responseContent, thinking:data.thinking}]);
    }catch (error) {
      console.error("Error sending message:", error);
      const errorText = error?.name === "AbortError"
        ? "Request timed out. Please try again."
        : "Server is temporarily unavailable. Please try again.";

      setmessages((prev) => [
        ...prev,
        { role: "assistant", content: errorText, thinking: null },
      ]);
    } finally {
      setisLoading(false);
    }
  };

  const handleFileUpload = (uploadData) => {
    if (uploadData.error) {
      setmessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error uploading file: ${uploadData.error}`,
          thinking: null,
        },
      ]);
      return;
    }

    // Add extracted text summary
    setmessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `📄 **File Uploaded Successfully**\n\nExtracted Text Preview:\n"${uploadData.extracted_text}..."\n\n**AI Analysis:**\n${uploadData.reply}`,
        thinking: uploadData.thinking,
      },
    ]);
  };

  return (
    <div className="bg-[#0b0b0b] text-[#e5e5e5] w-full h-screen flex flex-col">
      <Analytics />
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="sm:hidden fixed top-3 left-3 z-50 p-2 rounded-full bg-[#171717] border border-[#2a2a2a] text-white"
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

      {isExpanded && (
        <div
          className="sm:hidden fixed inset-0 bg-black/40 z-30"
          onClick={() => setIsExpanded(false)}
          aria-hidden="true"
        />
      )}

      <div className="flex flex-1 overflow-hidden font-sans bg-[#0b0b0b]">
        {/* --- Sidebar Container --- */}
        <div
          className={`bg-[#050505] text-white transition-all duration-300 ease-in-out flex flex-col overflow-hidden border-r border-[#161616] shadow-[2px_0_18px_rgba(0,0,0,0.35)] fixed sm:static top-0 left-0 h-full z-40 sm:z-auto ${
            isExpanded ? "w-64 translate-x-0" : "w-64 -translate-x-full sm:w-16 sm:translate-x-0"
          }`}
        >
          {/* Toggle Button Area */}
          <div className="hidden sm:flex items-center justify-center h-16 border-b border-[#161616]">
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
            {/* New Chat Button */}
            <button
              onClick={() => {
                setmessages([]);
                setExpandedThinking(null);
              }}
              className="flex items-center gap-4 p-2 rounded-lg hover:bg-[#1a1a1a] transition-colors min-w-0 text-left w-full bg-[#1f6feb] text-white font-medium"
              title="Start a new chat"
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
                    d="M12 4v16m8-8H4"
                  />
                </svg>
              </div>
              <span
                className={`whitespace-nowrap transition-opacity duration-300 ${isExpanded ? "opacity-100" : "opacity-0"}`}
              >
                New Chat
              </span>
            </button>

            {/* Clear Chat Button */}
            <button
              onClick={clearChatHistory}
              className="flex items-center gap-4 p-2 rounded-full hover:bg-[#1a1a1a] transition-colors min-w-0 text-left w-full mt-auto"
              title="Clear all chat history"
            >
              <div className="min-w-[24px]">
                <svg
                  className="w-5 h-5 text-[#ff6b6b]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </div>
              <span
                className={`whitespace-nowrap transition-opacity duration-300 text-[#ff6b6b] ${isExpanded ? "opacity-100" : "opacity-0"}`}
              >
                Clear Chat
              </span>
            </button>
          </nav>
        </div>

        {/* --- Main Content Area --- */}
        <div className="flex-1 p-5 text-[#d6d6d6] bg-[#111111] text-xl flex flex-col min-w-0">
          <nav className="border-b border-[#252525] mb-5 p-5 shadow-[0_1px_0_0_rgba(255,255,255,0.04)]">
            <ul className="flex justify-between items-center">
              <li className="font-semibold tracking-wide text-sm text-[#bfbfbf] pl-10 sm:pl-0">DTU GPT</li>
              <li className="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
                {/* Clerk Auth UI */}
                <Show when="signed-out">
                  <div className="flex gap-2 sm:gap-3 flex-wrap justify-end">
                    <SignInButton 
                      mode="modal"
                      forceRedirectUrl="/"
                      fallbackRedirectUrl="/"
                      appearance={{
                        baseTheme: undefined,
                        elements: {
                          button: "px-4 py-2 rounded-lg font-medium text-sm bg-[#1f6feb] text-white hover:bg-[#1a5fd9] transition-colors border-0",
                          buttonBase: "transition-colors"
                        }
                      }}
                    />
                    <SignUpButton 
                      mode="modal"
                      forceRedirectUrl="/"
                      fallbackRedirectUrl="/"
                      appearance={{
                        baseTheme: undefined,
                        elements: {
                          button: "px-4 py-2 rounded-lg font-medium text-sm bg-[#2d2d2d] text-white hover:bg-[#3a3a3a] border border-[#404040] transition-colors",
                          buttonBase: "transition-colors"
                        }
                      }}
                    />
                  </div>
                </Show>
                <Show when="signed-in">
                  <UserButton 
                    afterSignOutUrl="/"
                    userProfileMode="navigation"
                    userProfileUrl="/user-profile"
                    appearance={{
                      elements: {
                        avatarBox: "w-10 h-10 rounded-lg",
                        userButtonPopoverCard: "bg-[#1a1a1a] border border-[#404040]",
                        userButtonPopoverActionButtonText: "text-[#e5e5e5]",
                      }
                    }}
                  />
                </Show>
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
                  <div className="max-w-[85vw] sm:max-w-xs lg:max-w-md xl:max-w-lg">
                  <div
                      className={`px-4 py-2 rounded-lg ${
                        msg.role === "user"
                          ? "bg-[#1f6feb] text-white rounded-br-none"
                          : "bg-[#2d2d2d] text-[#e5e5e5] rounded-bl-none"
                      }`}
                    >
                      <div className="text-sm break-words">
                        <MessageDisplay message={msg.content} />
                      </div>
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
          
          <div className="p-2 sm:p-4 flex flex-col gap-3 justify-center items-center">
            {/* File Preview Area */}
            {selectedFile && (
              <div className="flex justify-center w-full">
                <div className="flex items-center gap-2 bg-[#1a1a1a] border border-[#404040] rounded-lg px-3 py-2 max-w-3xl w-full">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-5 h-5 text-[#888888] flex-shrink-0"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12.75l3 3m0 0l3-3m-3 3v-7.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#e5e5e5] truncate">{selectedFile.name}</p>
                    <p className="text-xs text-[#888888]">{(selectedFile.size / 1024).toFixed(2)} KB</p>
                  </div>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="flex-shrink-0 p-1 text-[#888888] hover:text-[#e5e5e5] transition-colors"
                    aria-label="Remove file"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        fillRule="evenodd"
                        d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 11-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            )}
            
            <div className="flex gap-2 sm:gap-3 bg-[#111111] border border-[#1f1f1f] rounded-xl sm:rounded-full w-full max-w-3xl px-3 sm:px-4 py-2 sm:py-3 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
              {/* File Upload Button */}
              <FileUpload selectedFile={selectedFile} setSelectedFile={setSelectedFile} onUpload={handleFileUpload} />
              <textarea
                placeholder="Type your message..."
                value={input}
                onChange={(e) => {
                  setinput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px";
                }}
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                className="bg-transparent text-white placeholder:text-[#6b6b6b] flex-1 min-w-0 focus:outline-none focus:ring-0 placeholder:text-sm text-sm resize-none max-h-[200px] overflow-y-auto"
                style={{ height: "40px", fontFamily: "inherit" }}
              />
              <button
                type="button"
                className="flex items-center justify-center w-10 h-10 rounded-full bg-[#1c1c1c] hover:bg-[#242424] text-[#cfcfcf] cursor-pointer transition-colors flex-shrink-0"
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
