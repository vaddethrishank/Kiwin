"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { Bot, Send, User } from "lucide-react"
import { createClient } from "@/lib/supabase/client"
import { getApiUrl } from "@/lib/utils"
import ReactMarkdown from "react-markdown"

interface Message {
    role: "user" | "assistant"
    content: string
}

interface ChatInterfaceProps {
    agentId: string
}

export function ChatInterface({ agentId }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)   // waiting for first token
    const [isStreaming, setIsStreaming] = useState(false) // tokens are arriving
    const scrollRef = useRef<HTMLDivElement>(null)
    const { toast } = useToast()

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages])

    // Load History on Mount
    useEffect(() => {
        const loadHistory = async () => {
            try {
                const supabase = createClient()
                const { data: { session } } = await supabase.auth.getSession()
                if (!session) return

                const res = await fetch(`${getApiUrl()}/api/v1/chat/${agentId}`, {
                    headers: {
                        "Authorization": `Bearer ${session.access_token}`
                    }
                })
                if (res.ok) {
                    const history = await res.json()
                    setMessages(history)
                }
            } catch (error) {
                console.error("Failed to load history", error)
            }
        }
        loadHistory()
    }, [agentId])

    const handleSend = async () => {
        if (!input.trim() || isLoading || isStreaming) return

        const userMessage: Message = { role: "user", content: input }
        setMessages(prev => [...prev, userMessage])
        setInput("")
        setIsLoading(true)  // show bouncing dots while waiting for first token

        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) throw new Error("Not authenticated")

            const res = await fetch(`${getApiUrl()}/api/v1/chat/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    agent_id: agentId,
                    message: userMessage.content
                })
            })

            if (!res.ok) throw new Error("Failed to send message")
            if (!res.body) throw new Error("No response body")

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let aiMessage = ""
            let firstChunk = true

            // Add empty placeholder for the AI message
            setMessages(prev => [...prev, { role: "assistant", content: "" }])

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                // First token arrived — switch from "waiting" to "streaming" mode
                if (firstChunk) {
                    setIsLoading(false)
                    setIsStreaming(true)
                    firstChunk = false
                }

                const text = decoder.decode(value, { stream: true })
                aiMessage += text

                setMessages(prev => {
                    const newMsgs = [...prev]
                    newMsgs[newMsgs.length - 1] = { role: "assistant", content: aiMessage }
                    return newMsgs
                })
            }
        } catch (error: any) {
            console.error(error)
            toast({
                title: "Error",
                description: "Failed to send message",
                variant: "destructive",
            })
        } finally {
            setIsLoading(false)
            setIsStreaming(false)
        }
    }

    return (
        <div className="flex flex-col h-[500px] rounded-md bg-muted/10">
            <div className="flex-1 p-4 overflow-y-auto space-y-4" ref={scrollRef}>
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground opacity-50">
                        <Bot className="w-8 h-8 mb-2" />
                        <p>Start a conversation...</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        {msg.role === "assistant" && (
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <Bot className="w-5 h-5 text-primary" />
                            </div>
                        )}

                        <div
                            className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                                msg.role === "user"
                                    ? "bg-primary text-primary-foreground rounded-br-none"
                                    : "bg-card border text-card-foreground rounded-bl-none"
                            }`}
                        >
                            {msg.role === "user" ? (
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            ) : (
                                <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed
                                    [&>p]:mb-2 [&>p:last-child]:mb-0
                                    [&>ul]:mb-2 [&>ul]:pl-4 [&>ul>li]:list-disc
                                    [&>ol]:mb-2 [&>ol]:pl-4 [&>ol>li]:list-decimal
                                    [&>strong]:font-semibold
                                    [&>code]:bg-muted [&>code]:px-1 [&>code]:rounded [&>code]:text-xs
                                    [&>pre]:bg-muted [&>pre]:p-2 [&>pre]:rounded [&>pre]:text-xs [&>pre]:overflow-x-auto
                                ">
                                    <ReactMarkdown>
                                        {/* Append blinking cursor while this is the last streaming message */}
                                        {isStreaming && idx === messages.length - 1
                                            ? msg.content + "▊"
                                            : msg.content}
                                    </ReactMarkdown>
                                </div>
                            )}
                        </div>

                        {msg.role === "user" && (
                            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
                                <span className="text-xs font-bold">You</span>
                            </div>
                        )}
                    </div>
                ))}

                {/* Bouncing dots: only while waiting for the VERY FIRST token */}
                {isLoading && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Bot className="w-5 h-5 text-primary" />
                        </div>
                        <div className="bg-muted max-w-[80%] rounded-2xl rounded-bl-none px-4 py-2">
                            <div className="flex space-x-1 h-5 items-center">
                                <div className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce " style={{ animationDelay: '0ms' }}></div>
                                <div className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="p-3 bg-background border-t">
                <form
                    onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    className="flex gap-2"
                >
                    <Input
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        placeholder="Type your message..."
                        disabled={isLoading || isStreaming}
                        className="flex-1"
                    />
                    <Button type="submit" disabled={isLoading || isStreaming} size="icon">
                        <Send className="w-4 h-4" />
                    </Button>
                </form>
            </div>
        </div>
    )
}


