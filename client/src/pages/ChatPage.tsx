import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Bot, User, Loader2, LogOut, CheckCircle2, Circle, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { VoiceInput, speakText } from "@/components/VoiceInput";
import { LanguageSelector } from "@/components/LanguageSelector";
import { ChatSidebar } from "@/components/ChatSidebar";
import QuerySuggestions from "@/components/QuerySuggestions";
import { apiRequest } from "@/lib/queryClient";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  timestamp: number;
  messages: Message[];
  language: string;
}

const STORAGE_KEY = "chat_sessions";
const ACTIVE_SESSION_KEY = "active_session_id";

// Helper functions for localStorage
const loadSessions = (): ChatSession[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const saveSessions = (sessions: ChatSession[]) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error("Failed to save sessions:", e);
  }
};

const generateSessionTitle = (firstMessage: string): string => {
  // Generate title from first user message (max 50 chars)
  const title = firstMessage.slice(0, 50);
  return title.length < firstMessage.length ? title + "..." : title;
};

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [suggestionIndex, setSuggestionIndex] = useState(-1);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [progressSteps, setProgressSteps] = useState<Array<{step: number, message: string, status: 'pending' | 'active' | 'completed'}>>([
    { step: 1, message: 'Analyzing your question', status: 'pending' },
    { step: 2, message: 'Searching for information', status: 'pending' },
    { step: 3, message: 'Generating response..', status: 'pending' },
    { step: 4, message: 'Finalizing answer..', status: 'pending' },
  ]);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  // Load sessions on mount
  useEffect(() => {
    const loadedSessions = loadSessions();
    setSessions(loadedSessions);
    
    // Load active session or create new one
    const lastActiveId = localStorage.getItem(ACTIVE_SESSION_KEY);
    if (lastActiveId && loadedSessions.find(s => s.id === lastActiveId)) {
      const activeSession = loadedSessions.find(s => s.id === lastActiveId)!;
      setActiveSessionId(lastActiveId);
      setMessages(activeSession.messages);
      setLanguage(activeSession.language);
    } else if (loadedSessions.length > 0) {
      // Load most recent session
      const recent = loadedSessions[0];
      setActiveSessionId(recent.id);
      setMessages(recent.messages);
      setLanguage(recent.language);
      localStorage.setItem(ACTIVE_SESSION_KEY, recent.id);
    } else {
      // Create first session
      createNewSession();
    }
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current && !showScrollButton) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent, isStreaming]);

  // Handle scroll to detect if user scrolled up
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100;
    setShowScrollButton(!isNearBottom);
  };

  // Scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Save current session whenever messages change
  useEffect(() => {
    if (!activeSessionId || messages.length === 0) return;
    
    setSessions(prevSessions => {
      const updated = prevSessions.map(session => {
        if (session.id === activeSessionId) {
          const title = session.title === "New Chat" && messages.length > 0
            ? generateSessionTitle(messages[0].content)
            : session.title;
          
          return {
            ...session,
            title,
            messages,
            language,
            timestamp: Date.now(),
          };
        }
        return session;
      });
      
      saveSessions(updated);
      return updated;
    });
  }, [messages, activeSessionId, language]);

  const createNewSession = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: "New Chat",
      timestamp: Date.now(),
      messages: [],
      language: "en",
    };
    
    setSessions(prev => {
      const updated = [newSession, ...prev];
      saveSessions(updated);
      return updated;
    });
    
    setActiveSessionId(newSession.id);
    setMessages([]);
    setLanguage("en");
    localStorage.setItem(ACTIVE_SESSION_KEY, newSession.id);
    
    toast({
      title: "New Chat",
      description: "Started a new conversation",
    });
  };

  const switchSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;
    
    setActiveSessionId(sessionId);
    setMessages(session.messages);
    setLanguage(session.language);
    localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  };

  const deleteSession = (sessionId: string) => {
    if (sessions.length === 1) {
      toast({
        title: "Cannot Delete",
        description: "You must have at least one chat session",
        variant: "destructive",
      });
      return;
    }
    
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId);
      saveSessions(updated);
      return updated;
    });
    
    // If deleting active session, switch to another
    if (sessionId === activeSessionId) {
      const remaining = sessions.filter(s => s.id !== sessionId);
      if (remaining.length > 0) {
        switchSession(remaining[0].id);
      }
    }
    
    toast({
      title: "Chat Deleted",
      description: "Conversation removed from history",
    });
  };

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("userEmail");
    toast({
      title: "Logged Out",
      description: "You have been successfully logged out.",
    });
    setLocation("/");
  };

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      setIsStreaming(true);
      setStreamingContent("");
      setProgressSteps([
        { step: 1, message: 'Analyzing your question', status: 'pending' },
        { step: 2, message: 'Searching for information', status: 'pending' },
        { step: 3, message: 'Generating response..', status: 'pending' },
        { step: 4, message: 'Finalizing answer..', status: 'pending' },
      ]);
      
      setLoadingMessage("Processing...");
      
      // Send conversation history for context
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const API_BASE_URL = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message, 
          language,
          history 
        }),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Streaming request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let finalData: any = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'progress') {
                // Update progress steps based on step number and status
                setProgressSteps(prev => 
                  prev.map(p => 
                    p.step === data.step 
                      ? { ...p, status: data.status }
                      : p.step < data.step 
                        ? { ...p, status: 'completed' }
                        : p
                  )
                );
              } else if (data.type === 'content') {
                fullContent += data.content;
                setStreamingContent(fullContent);
                setLoadingMessage("");
              } else if (data.type === 'complete') {
                finalData = data;
              } else if (data.type === 'error') {
                throw new Error(data.content);
              }
            }
          }
        }
      }

      setIsStreaming(false);
      setProgressSteps([
        { step: 1, message: 'Analyzing your question', status: 'pending' },
        { step: 2, message: 'Searching for information', status: 'pending' },
        { step: 3, message: 'Generating response..', status: 'pending' },
        { step: 4, message: 'Finalizing answer..', status: 'pending' },
      ]);
      return finalData || { response: fullContent };
    },
    onSuccess: (data, variables) => {
      setLoadingMessage("");
      setStreamingContent("");
      setProgressSteps([
        { step: 1, message: 'Analyzing your question', status: 'pending' },
        { step: 2, message: 'Searching for information', status: 'pending' },
        { step: 3, message: 'Generating response..', status: 'pending' },
        { step: 4, message: 'Finalizing answer..', status: 'pending' },
      ]);
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: data.response || data.content,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      
      if (voiceOutputEnabled && (data.response || data.content)) {
        speakText(data.response || data.content, language);
      }
    },
    onError: () => {
      setLoadingMessage("");
      setIsStreaming(false);
      setStreamingContent("");
      setProgressSteps([
        { step: 1, message: 'Analyzing your question', status: 'pending' },
        { step: 2, message: 'Searching for information', status: 'pending' },
        { step: 3, message: 'Generating response..', status: 'pending' },
        { step: 4, message: 'Finalizing answer..', status: 'pending' },
      ]);
    },
  });

  const handleSend = () => {
    if (!input.trim() || chatMutation.isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };
    setMessages((prev) => [...prev, userMessage]);
    chatMutation.mutate(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Arrow key navigation for suggestions
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSuggestionIndex(prev => prev + 1);
      return;
    }
    
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setSuggestionIndex(prev => Math.max(-1, prev - 1));
      return;
    }
    
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionSelect = (suggestion: string) => {
    setInput(suggestion);
    setSuggestionIndex(-1);
  };

  const handleVoiceTranscript = (text: string) => {
    setInput(text);
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar - Fixed */}
      <ChatSidebar
        sessions={sessions.map(s => ({
          id: s.id,
          title: s.title,
          timestamp: s.timestamp,
          messageCount: s.messages.length,
        }))}
        activeSessionId={activeSessionId}
        onSelectSession={switchSession}
        onNewChat={createNewSession}
        onDeleteSession={deleteSession}
      />

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header - Fixed */}
        <header className="flex-shrink-0 flex items-center justify-between gap-4 p-4 border-b bg-card">
          <div className="flex items-center gap-3">
            <Bot className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-lg font-semibold" data-testid="text-app-title">
                Procurement AI
              </h1>
              <p className="text-xs text-muted-foreground">Powered by OpenAI GPT-4o</p>
            </div>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <LanguageSelector value={language} onChange={setLanguage} />
            <VoiceInput
              onTranscript={handleVoiceTranscript}
              language={language}
              voiceOutputEnabled={voiceOutputEnabled}
              onVoiceOutputToggle={setVoiceOutputEnabled}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
            <div className="h-8 w-px bg-border mx-2" />
            <img 
              src="/liztek.jpeg" 
              alt="Liztek" 
              className="h-10 w-auto object-contain"
            />
          </div>
        </header>

        {/* Messages Area - Scrollable */}
        <div className="flex-1 relative overflow-hidden bg-gradient-to-b from-background to-muted/20">
          <div 
            className="h-full overflow-y-auto scroll-smooth" 
            onScroll={handleScroll}
            style={{ 
              scrollbarWidth: 'thin',
              scrollbarColor: 'rgb(203 213 225) transparent'
            }}
          >
            <div className="p-6 space-y-6 max-w-6xl mx-auto min-h-full">
              {messages.length === 0 && (
                <div className="text-center py-20 space-y-4" data-testid="text-empty-state">
                  <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                    <Bot className="h-8 w-8 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold mb-2">Welcome to Procurement AI</h2>
                    <p className="text-muted-foreground">Ask me anything about your procurement data</p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center mt-6">
                    <div className="px-4 py-2 rounded-full bg-muted/50 text-sm border border-border/50">"What is the total budget?"</div>
                    <div className="px-4 py-2 rounded-full bg-muted/50 text-sm border border-border/50">"Show high risk projects"</div>
                    <div className="px-4 py-2 rounded-full bg-muted/50 text-sm border border-border/50">"List approved requests"</div>
                  </div>
                </div>
              )}
            
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-4 ${message.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2 duration-300`}
                data-testid={`message-${message.role}-${message.id}`}
              >
                {message.role === "assistant" && (
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center shadow-sm border border-primary/10">
                    <Bot className="h-5 w-5 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3.5 shadow-sm ${
                    message.role === "user"
                      ? "bg-gradient-to-br from-primary to-primary/90 text-primary-foreground"
                      : "bg-card border border-border/50"
                  }`}
                >
                  {message.role === "user" ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div>
                      <div className="prose prose-base dark:prose-invert max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({ node, ...props }) => (
                              <div className="overflow-x-auto my-4 rounded-lg border border-border">
                                <table className="border-collapse w-full text-sm" {...props} />
                              </div>
                            ),
                            th: ({ node, ...props }) => (
                              <th className="border-b-2 border-border px-4 py-3 bg-muted/80 font-semibold text-left text-xs uppercase tracking-wider" {...props} />
                            ),
                            td: ({ node, ...props }) => (
                              <td className="border-b border-border/50 px-4 py-3 hover:bg-muted/30 transition-colors" {...props} />
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
                {message.role === "user" && (
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/90 flex items-center justify-center shadow-md">
                    <User className="h-5 w-5 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}
            
            {(isStreaming || (chatMutation.isPending && progressSteps.length > 0)) && (
              <div className="flex gap-4 justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center shadow-sm border border-primary/10">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <div className="bg-card border border-border/50 rounded-2xl px-5 py-4 max-w-[75%] space-y-3 shadow-sm">
                  {/* Progress Steps */}
                  {progressSteps.length > 0 && (
                    <div className="space-y-3">
                      {progressSteps.map((step, index) => (
                        <div key={index} className="flex items-center gap-3 text-sm">
                          {step.status === 'completed' ? (
                            <div className="flex-shrink-0 w-5 h-5 rounded-sm bg-green-500 flex items-center justify-center">
                              <CheckCircle2 className="h-4 w-4 text-white" />
                            </div>
                          ) : step.status === 'active' ? (
                            <div className="flex-shrink-0 w-5 h-5 rounded-sm bg-orange-500 flex items-center justify-center">
                              <Loader2 className="h-3 w-3 animate-spin text-white" />
                            </div>
                          ) : (
                            <div className="flex-shrink-0 w-5 h-5 rounded-sm border-2 border-gray-300"></div>
                          )}
                          <span className={step.status === 'completed' ? "text-muted-foreground" : step.status === 'active' ? "text-foreground font-medium" : "text-muted-foreground/50"}>
                            {step.message}
                          </span>
                        </div>
                      ))}
                      
                      {/* Progress Bar */}
                      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden mt-2">
                        <div 
                          className="absolute h-full bg-blue-500 transition-all duration-300 rounded-full"
                          style={{ 
                            width: `${(progressSteps.filter(s => s.status === 'completed').length / progressSteps.length) * 100}%` 
                          }}
                        ></div>
                      </div>
                      <p className="text-xs text-center text-muted-foreground">Processing...</p>
                    </div>
                  )}
                  
                  {/* Streaming Content */}
                  {streamingContent && (
                    <div className="prose prose-sm dark:prose-invert max-w-none border-t border-border/50 pt-3 mt-3">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamingContent}
                      </ReactMarkdown>
                      <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1"></span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {chatMutation.isPending && !isStreaming && progressSteps.length === 0 && (
              <div className="flex gap-3 justify-start" data-testid="loading-indicator">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-3 flex items-center gap-3">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  {loadingMessage && (
                    <span className="text-sm text-muted-foreground">{loadingMessage}</span>
                  )}
                </div>
              </div>
            )}
              
              {/* Invisible div for scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          </div>
          
          {/* Scroll to Bottom Button */}
          {showScrollButton && (
            <Button
              onClick={scrollToBottom}
              size="icon"
              className="absolute  bottom-20 left-[92%] rounded-full shadow-xl hover:shadow-2xl transition-all hover:scale-110 z-50 bg-primary"
              variant="default"
            >
              <ArrowDown className="h-5 w-5" />
            </Button>
          )}
        </div>

        {/* Input Area - Fixed */}
        <div className="flex-shrink-0 border-t bg-card/95 backdrop-blur-sm p-4 shadow-lg">
          <div className="max-w-6xl mx-auto space-y-3">
            {/* Query Suggestions */}
            <QuerySuggestions
              input={input}
              language={language}
              conversationContext={messages.filter(m => m.role === "user").map(m => m.content)}
              onSelect={handleSuggestionSelect}
              selectedIndex={suggestionIndex}
              onIndexChange={setSuggestionIndex}
            />
            
            <div className="flex gap-3 items-end">
              <Textarea
                value={input}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about procurement data..."
                className="min-h-[56px] max-h-32 resize-none rounded-2xl border-2 focus:border-primary/50 transition-colors shadow-sm"
                data-testid="input-chat"
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || chatMutation.isPending}
                size="icon"
                className="h-14 w-14 rounded-2xl shadow-md hover:shadow-lg transition-all hover:scale-105"
                data-testid="button-send"
              >
                {chatMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
