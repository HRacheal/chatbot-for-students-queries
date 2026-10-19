import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import SpotlightCard from "./ui/SpotlightCard";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { IoSend, IoClose } from "react-icons/io5";
import { Label } from "./ui/label";
import GradientText from "./ui/GradientText";
import { IoMdSettings } from "react-icons/io";
import { SkeletonDemo } from "./ui/SkeletonDemo";
import { FaHistory, FaCalendarAlt, FaChevronDown, FaChevronUp } from "react-icons/fa";
import { BiExpandAlt, BiCollapseAlt } from "react-icons/bi"; // Added resize icons
import { FiLogOut, FiLogIn } from "react-icons/fi"; // More distinct login/logout icons
import { getChatHistory, submitQuery } from "../lib/api";
import { format } from "date-fns";

function ChatBox({ onClose }) {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [userChatHistory, setUserChatHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [showConversation, setShowConversation] = useState(false);
  const [isTyping, setIsTyping] = useState(false); // Add loading state
  const [typingText, setTypingText] = useState({}); // Add state for typing text animation
  const [expandedChat, setExpandedChat] = useState(null); // Track expanded history item
  const conversationRef = useRef(null);
  const chatBoxRef = useRef(null);
  const messagesEndRef = useRef(null); // New ref for scroll target
  
  // New state for chatbot size and position
  const [size, setSize] = useState(() => {
    const savedSize = localStorage.getItem('chatbotSize');
    // Ensure initial size is within limits
    const defaultSize = { width: 40, height: 80 };
    if (savedSize) {
      const parsedSize = JSON.parse(savedSize);
      return { 
        width: Math.max(parsedSize.width, 40), // Minimum width is now 40%
        height: Math.max(parsedSize.height, 50) // Minimum height is now 50%
      };
    }
    return defaultSize;
  });
  
  // Track window dimensions for responsive positioning
  const [windowDimensions, setWindowDimensions] = useState({
    height: window.innerHeight,
    width: window.innerWidth
  });

  // Update window dimensions when resized
  useEffect(() => {
    function handleResize() {
      setWindowDimensions({
        height: window.innerHeight,
        width: window.innerWidth
      });
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Adjust position if necessary when size changes
  useEffect(() => {
    if (chatBoxRef.current) {
      const rect = chatBoxRef.current.getBoundingClientRect();
      if (rect.top < 0) {
        // If the top is off-screen, adjust position
        chatBoxRef.current.style.bottom = 'auto';
        chatBoxRef.current.style.top = '10px';
      } else {
        // Default positioning from bottom - moved closer to bottom
        chatBoxRef.current.style.bottom = '2rem'; // Changed from 6rem to 2rem
        chatBoxRef.current.style.top = 'auto';
      }
    }
  }, [size, windowDimensions]);

  useEffect(() => {
    // Check if user is logged in
    const userToken = localStorage.getItem("userToken");
    setIsLoggedIn(!!userToken);
  }, []);

  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [chatHistory, showConversation]);
  
  // Save size preferences to localStorage
  useEffect(() => {
    localStorage.setItem('chatbotSize', JSON.stringify(size));
  }, [size]);

  // Improved scroll to bottom function
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };
  
  // Enhanced auto-scrolling with MutationObserver
  useEffect(() => {
    // Scroll immediately when chat history changes
    scrollToBottom();
    
    // Set up mutation observer to detect content changes and scroll
    if (conversationRef.current) {
      const observer = new MutationObserver(scrollToBottom);
      
      // Observe both child additions and attribute changes
      observer.observe(conversationRef.current, {
        childList: true,
        subtree: true,
        characterData: true,
      });
      
      return () => observer.disconnect();
    }
  }, [chatHistory, showConversation, isTyping]);

  const handleSettingsClick = () => {
    navigate("/admin");
  };

  const handleLoginClick = () => {
    navigate("/login");
  };

  const handleLogout = () => {
    localStorage.removeItem("userToken");
    setIsLoggedIn(false);
    setShowHistory(false);
  };
  
  // Size adjustment functions with screen boundary check
  const increaseSize = () => {
    setSize(prevSize => {
      const newHeight = Math.min(prevSize.height + 5, 95);
      
      // Calculate if new height would fit in viewport
      const availableHeight = windowDimensions.height - 32; // Changed from 96 to 32 (2rem)
      const maxHeight = (availableHeight / windowDimensions.height) * 100;
      
      return {
        width: Math.min(prevSize.width + 5, 80),
        height: Math.min(newHeight, maxHeight)
      };
    });
  };
  
  const decreaseSize = () => {
    setSize(prevSize => ({
      width: Math.max(prevSize.width - 5, 40),  // Increased from 30 to 40
      height: Math.max(prevSize.height - 5, 50)  // Increased from 40 to 50
    }));
  };

  const handleHistoryClick = async () => {
    const newState = !showHistory;
    setShowHistory(newState);
    
    // Only fetch history if we're showing history and we haven't loaded it yet
    if (newState && isLoggedIn && userChatHistory.length === 0) {
      setHistoryLoading(true);
      try {
        const token = localStorage.getItem("userToken");
        const response = await getChatHistory(token);
        setUserChatHistory(response.history || []);
      } catch (error) {
        console.error("Error fetching chat history:", error);
      } finally {
        setHistoryLoading(false);
      }
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim() || isTyping) return;

    const currentMessage = message;
    const messageId = Date.now().toString(); // Create unique ID for this message
    setMessage(""); // Clear input immediately
    setIsTyping(true); // Start loading state
    
    // Add user message to chat history immediately with ID
    setChatHistory((prev) => [
      ...prev,
      { id: messageId, query: currentMessage, response: null, timestamp: new Date() },
    ]);
    setShowConversation(true);
    
    // Force immediate scroll after user message is added
    setTimeout(scrollToBottom, 50);

    try {
      const token = localStorage.getItem("userToken");
      const response = await submitQuery(
        {
          question: currentMessage,
        },
        token
      );

      // Get the response text
      const responseText = response.answer || "No answer found";
      
      // Update the last message with the response
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = responseText;
        return updated;
      });
      
      // Start typing animation for this response
      setTypingText(prev => ({
        ...prev,
        [messageId]: {
          text: responseText,
          displayedChars: 0,
          completed: false
        }
      }));
      
      // Force scroll after response is added
      setTimeout(scrollToBottom, 50);
    } catch (error) {
      let errorResponse;
      
      if (error.response) {
        if (error.response.status === 404) {
          errorResponse = "We couldn't find an answer to your question at the moment. Don't worry — your query has been logged, and if you're logged in, you'll be notified as soon as we have a response.";
        } else if (error.response.status === 503 && error.response.data && error.response.data.error) {
          // Use the user-friendly error message from the backend
          errorResponse = error.response.data.error;
        } else {
          errorResponse = "Sorry, something went wrong. Please try again.";
        }
      } else {
        errorResponse = "Network error. Please check your connection and try again.";
      }
      
      // Update the last message with the error response
      setChatHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].response = errorResponse;
        updated[updated.length - 1].id = messageId;
        return updated;
      });
      
      // Start typing animation for the error response too
      setTypingText(prev => ({
        ...prev,
        [messageId]: {
          text: errorResponse,
          displayedChars: 0,
          completed: false
        }
      }));
      
      // Force scroll after error response is added
      setTimeout(scrollToBottom, 50);
    } finally {
      setIsTyping(false); // End loading state
      // One final scroll after typing indicator is removed
      setTimeout(scrollToBottom, 100);
    }
  };

  // Handle typing animation
  useEffect(() => {
    const typingTimers = {};
    
    // Process each typing animation
    Object.keys(typingText).forEach(id => {
      const data = typingText[id];
      
      // If animation is not complete
      if (!data.completed && data.displayedChars < data.text.length) {
        // Set timer to add next character
        typingTimers[id] = setTimeout(() => {
          setTypingText(prev => ({
            ...prev,
            [id]: {
              ...prev[id],
              displayedChars: prev[id].displayedChars + 1,
              // Mark as completed if this is the last character
              completed: prev[id].displayedChars + 1 >= prev[id].text.length
            }
          }));
          
          // Scroll down as text appears
          scrollToBottom();
        }, Math.random() * 25 + 15); // Random delay between 15-40ms for natural typing effect
      }
    });
    
    // Clean up timers when component unmounts or typing state changes
    return () => {
      Object.values(typingTimers).forEach(timer => clearTimeout(timer));
    };
  }, [typingText]);

  const TypingIndicator = () => (
    <div className="bg-gray-800 rounded-lg p-3 animate-pulse">
      <p className="text-blue-400 font-medium">Sahayak is thinking...</p>
      <div className="flex space-x-1 mt-2">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
      </div>
    </div>
  );

  // Group chat history by date
  const groupChatHistoryByDate = (history) => {
    const grouped = {};
    
    if (history && history.length > 0) {
      history.forEach(chat => {
        const date = format(new Date(chat.timestamp), 'yyyy-MM-dd');
        if (!grouped[date]) {
          grouped[date] = [];
        }
        grouped[date].push(chat);
      });
    }
    
    return grouped;
  };
  
  // Toggle expanded chat in history
  const toggleExpandChat = (chatId) => {
    setExpandedChat(expandedChat === chatId ? null : chatId);
  };
  
  return (
    <div 
      ref={chatBoxRef}
      className="fixed right-8" 
      style={{ 
        height: `${size.height}%`, 
        width: `${size.width}%`, 
        bottom: '2rem',
        transition: 'all 0.3s ease'
      }}
    >
      <SpotlightCard
        className="custom-spotlight-card h-full flex flex-col"
        spotlightColor="rgba(0, 229, 255, 0.2)"
      >
        <div className="p-2 border-b border-neutral-800 flex justify-between items-center">
          {isLoggedIn && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleHistoryClick}
              className="text-blue-500 text-3xl hover:bg-blue-800 hover:text-white"
              title="View history"
            >
              <FaHistory />
            </Button>
          )}
          <GradientText
            colors={["#b185db", "#5a8dee", "#59c3e3", "#ff85a1", "#d25ca8"]}
            animationSpeed={3}
            showBorder={false}
            className="custom-class text-3xl mb-3"
          >
            Welcome to Sahayak
          </GradientText>

          <div className="flex items-center space-x-1">
            {/* Resize buttons */}
            <Button
              variant="ghost"
              size="icon"
              onClick={decreaseSize}
              className="text-yellow-500 hover:bg-yellow-800 hover:text-white"
              title="Decrease size"
            >
              <BiCollapseAlt className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={increaseSize}
              className="text-yellow-500 hover:bg-yellow-800 hover:text-white"
              title="Increase size"
            >
              <BiExpandAlt className="h-5 w-5" />
            </Button>

            {isLoggedIn ? (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="text-pink-500 text-3xl hover:bg-pink-800 hover:text-white"
                title="Log out"
              >
                <FiLogOut className="h-5 w-5" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLoginClick}
                className="text-pink-500 text-3xl hover:bg-pink-800 hover:text-white"
                title="Log in"
              >
                <FiLogIn className="h-5 w-5" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleSettingsClick}
              className="text-blue-500 text-3xl hover:bg-blue-800 hover:text-white"
              title="Admin Login"
            >
              <IoMdSettings />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-red-500 hover:bg-red-800 hover:text-white"
              title="Close"
            >
              <IoClose className="h-6 w-6" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {showHistory ? (
            isLoggedIn ? (
              historyLoading ? (
                <div className="flex justify-center items-center h-full">
                  <div className="animate-pulse space-y-6 w-full">
                    <div className="h-6 bg-gray-700 rounded w-1/3"></div>
                    <div className="space-y-3 w-full">
                      <div className="h-20 bg-gray-800 rounded-lg w-full"></div>
                      <div className="h-20 bg-gray-800 rounded-lg w-full"></div>
                      <div className="h-20 bg-gray-800 rounded-lg w-full"></div>
                    </div>
                  </div>
                </div>
              ) : userChatHistory.length > 0 ? (
                <div className="space-y-6">
                  <h2 className="text-xl text-white flex items-center font-medium">
                    <FaCalendarAlt className="mr-2 text-blue-400" />
                    Chat History
                  </h2>
                  
                  {Object.entries(groupChatHistoryByDate(userChatHistory)).map(([date, chats]) => (
                    <div key={date} className="mb-4">
                      <div className="text-blue-300 font-medium mb-2 border-b border-gray-700 pb-1">
                        {format(new Date(date), 'EEEE, MMMM d, yyyy')}
                      </div>
                      
                      <div className="space-y-3">
                        {chats.map((chat) => (
                          <div 
                            key={chat._id} 
                            className="bg-gray-800 rounded-lg p-3 hover:border-blue-500 border border-transparent transition-all duration-200 cursor-pointer"
                            onClick={() => toggleExpandChat(chat._id)}
                          >
                            <div className="flex justify-between items-start">
                              <div className="flex items-start">
                                <span className="text-red-400 mr-2 font-medium">You:</span>
                                <span className="text-white">
                                  {chat.question.length > 60 && expandedChat !== chat._id 
                                    ? `${chat.question.substring(0, 60)}...` 
                                    : chat.question}
                                </span>
                              </div>
                              <div className="flex items-center">
                                <div className="text-gray-400 text-xs mr-2">
                                  {format(new Date(chat.timestamp), 'h:mm a')}
                                </div>
                                {expandedChat === chat._id ? 
                                  <FaChevronUp className="text-blue-400" /> : 
                                  <FaChevronDown className="text-blue-400" />
                                }
                              </div>
                            </div>
                            
                            {expandedChat === chat._id && (
                              <div className="mt-3 pt-3 border-t border-gray-700">
                                <div className="mb-3">
                                  <div className="text-blue-400 text-sm font-medium mb-1">Question:</div>
                                  <div className="text-white bg-blue-800/30 p-2 rounded-md">{chat.question}</div>
                                </div>
                                <div>
                                  <div className="text-green-400 text-sm font-medium mb-1">Answer:</div>
                                  <div 
                                    className="text-white bg-gray-700/50 p-2 rounded-md chat-response"
                                    dangerouslySetInnerHTML={{ __html: chat.answer }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center flex flex-col items-center justify-center h-full">
                  <div className="bg-gray-800 rounded-lg p-6 shadow-lg max-w-md">
                    <div className="text-blue-400 text-4xl mb-4 opacity-60">
                      <FaCalendarAlt />
                    </div>
                    <h3 className="text-white text-xl mb-2">No chat history found</h3>
                    <p className="text-gray-400">Your conversations will appear here after you start chatting</p>
                  </div>
                </div>
              )
            ) : (
              <div className="text-center flex flex-col items-center justify-center h-full">
                <div className="bg-gray-800 rounded-lg p-6 shadow-lg max-w-md">
                  <div className="text-pink-500 text-4xl mb-4 opacity-60">
                    <FiLogIn />
                  </div>
                  <h3 className="text-white text-xl mb-4">Please login to see chat history</h3>
                  <Button
                    variant="outline"
                    onClick={handleLoginClick}
                    className="text-pink-500 hover:bg-pink-800 hover:text-white border-pink-500"
                    title="Log in to view history"
                  >
                    Login
                  </Button>
                </div>
              </div>
            )
          ) : showConversation ? (
            <div
              ref={conversationRef}
              className="space-y-4"
            >
              {chatHistory.map((chat, index) => (
                <div key={index} className="space-y-3">
                  {/* User message */}
                  <div className="bg-blue-800 rounded-lg p-3 ml-28">
                    <p className="font-medium">
                      <span className="text-red-400 mr-1">You:</span>
                      <span className="text-white"> {chat.query}</span>
                    </p>
                    <div className="text-blue-200 text-xs mt-1">
                      {chat.timestamp && format(new Date(chat.timestamp), 'h:mm a')}
                    </div>
                  </div>
                  
                  {/* Bot response or loading */}
                  {chat.response ? (
                    <div className="bg-gray-800 rounded-lg p-3 mr-28">
                      <p className="text-green-400 font-medium">Sahayak:</p>
                      <div className="text-white mt-2 chat-response">
                        {/* Show typing animation if this message has an ID and is in typingText state */}
                        {chat.id && typingText[chat.id] ? (
                          <>
                            <span dangerouslySetInnerHTML={{ 
                              __html: typingText[chat.id].text.substring(0, typingText[chat.id].displayedChars) 
                            }} />
                            {!typingText[chat.id].completed && (
                              <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse"></span>
                            )}
                          </>
                        ) : (
                          <span dangerouslySetInnerHTML={{ __html: chat.response }} />
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mr-8">
                      <TypingIndicator />
                    </div>
                  )}
                </div>
              ))}
              {/* Invisible element at the end to scroll to */}
              <div ref={messagesEndRef} style={{ height: "1px" }} />
            </div>
          ) : (
            <>
              <div className="mt-3">
                <SkeletonDemo className="mt-3" />
              </div>
              <div className="mt-3">
                <SkeletonDemo className="mt-3" />
              </div>
            </>
          )}
        </div>
        
        <div className="mt-auto p-4">
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Label htmlFor="message" className="text-white sr-only">
                Your Query
              </Label>
              <Textarea
                placeholder={isTyping ? "Please wait..." : "Type your message here."}
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="min-h-[50px] max-h-[100px] text-white"
                disabled={isTyping}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !isTyping) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
            </div>
            <Button 
              className={`h-[50px] px-4 ${isTyping ? 'opacity-50 cursor-not-allowed' : ''}`} 
              onClick={handleSendMessage} 
              disabled={isTyping}
              title={isTyping ? "Generating response..." : "Send message"}
            >
              <IoSend className="h-5 w-5" />
            </Button>
          </div>
          {isTyping && (
            <div className="text-center text-gray-400 text-sm mt-2">
              Generating response...
            </div>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}

export default ChatBox;