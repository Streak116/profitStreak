"use client";

import React from "react";
import { useState, useRef, useEffect } from "react";

import Image from "next/image";

const LLM_NAMES = ["llama3", "deepseek-chat:8b", "gemma:7b", "mistral"];

const StockMarketQuery = () => {
  const [userInput, setUserInput] = useState("");
  const [disableSend, setDisableSend] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [isBotTyping, setIsBotTyping] = useState(false);

  const [messagesByLLM, setMessagesByLLM] = useState(() =>
    LLM_NAMES.reduce((acc, name) => {
      acc[name] = [
        {
          sender: "bot",
          text: `Hi, I'm ${name}. How can I help you?`,
          timestamp: new Date(),
        },
      ];
      return acc;
    }, {} as Record<string, { sender: string; text: string; timestamp: Date }[]>)
  );

  const messageEndRefs = useRef(
    LLM_NAMES.reduce((acc, name) => {
      acc[name] = React.createRef<HTMLDivElement>();
      return acc;
    }, {} as Record<string, React.RefObject<HTMLDivElement | null>>)
  );

  useEffect(() => {
    LLM_NAMES.forEach((name) => {
      messageEndRefs.current[name]?.current?.scrollIntoView({
        behavior: "smooth",
      });
    });
  }, [messagesByLLM, isBotTyping]);

  const sendMessageToLLM = async (
    llm: string,
    message: string
  ): Promise<string> => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/queryProcessor/processQuery/?model=${llm}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: message }),
      });
      const data = await response.json();
      return (
        data.response || `(${llm}) Sorry, I couldn't process your request.`
      );
    } catch (error) {
      return `(${llm}) Error processing request.`;
    }
  };

  const handleSendMessage = async () => {
    if (!userInput.trim()) return;

    const message = userInput.trim();
    setDisableSend(true);
    setIsBotTyping(true);
    setUserInput("");

    // Add user message to all LLMs
    const updated = { ...messagesByLLM };
    LLM_NAMES.forEach((name) => {
      updated[name].push({
        sender: "user",
        text: message,
        timestamp: new Date(),
      });
    });
    setMessagesByLLM(updated);

    // Get replies for each LLM
    await Promise.all(
      LLM_NAMES.map(async (llm) => {
        setLoadingByLLM((prev) => ({ ...prev, [llm]: true }));
        const reply = await sendMessageToLLM(llm, message);
        setMessagesByLLM((prev) => ({
          ...prev,
          [llm]: [
            ...prev[llm],
            { sender: "bot", text: reply, timestamp: new Date() },
          ],
        }));
        setLoadingByLLM((prev) => ({ ...prev, [llm]: false }));
      })
    );

    setIsBotTyping(false);
    setDisableSend(false);
  };

  const [loadingByLLM, setLoadingByLLM] = useState<Record<string, boolean>>(
    () => LLM_NAMES.reduce((acc, name) => ({ ...acc, [name]: false }), {})
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <>
      <div style={{ textAlign: "center", marginBottom: "20px", display: "flex", justifyContent: "center" }}>
        <Image
          src="/vignan-logo.png"
          alt={"Vignan's Institute of Information Technology"}
          width={750}
          height={100}
        ></Image>
      </div>
      <div className={`chat-container ${darkMode ? "dark" : "light"}`}>
        <div className="chat-header">
          <h2>ProfitStreak Multi-LLM Chat</h2>
          <button onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "Light Mode" : "Dark Mode"}
          </button>
        </div>

        <div className="chat-box multi-llm">
          {LLM_NAMES.map((llm) => (
            <div key={llm} className="llm-column">
              <div className="llm-title">{llm}</div>
              <div className="messages">
                {messagesByLLM[llm].map((msg, idx) => (
                  <div key={idx} className={`message ${msg.sender}`}>
                    <p
                      dangerouslySetInnerHTML={{
                        __html: msg.text.replace(/\n/g, "<br />"),
                      }}
                    />
                    <span className="timestamp">
                      {msg.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                ))}
                {loadingByLLM[llm] && (
                  <div className="message bot">
                    <p className="typing">
                      <span>.</span>
                      <span>.</span>
                      <span>.</span>
                    </p>
                  </div>
                )}
                <div ref={messageEndRefs.current[llm]} />
              </div>
            </div>
          ))}
        </div>

        <div className="input-container">
          <textarea
            className="textarea"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask your stock market question..."
            rows={2}
            disabled={disableSend}
          />
          <button onClick={handleSendMessage} disabled={disableSend}>
            {disableSend ? <span className="spinner"></span> : "Send"}
          </button>
        </div>
      </div>
    </>
  );
};

export default StockMarketQuery;
