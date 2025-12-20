"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft, Bot, Save, Trash2, Cpu, Database, Settings, LayoutDashboard, MessageSquare, FileText, Code } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { createClient } from "@/lib/supabase/client"
import { FileUpload } from "@/components/knowledge/file-upload"
import { FileList } from "@/components/knowledge/file-list"
import { ChatInterface } from "@/components/chat/chat-interface"

interface Agent {
    id: string
    name: string
    role: string
    description: string
    model: string
    system_prompt: string
    tools?: string[]
    api_key?: string
    created_at: string
}

export default function AgentDetailsPage() {
    const { agentId } = useParams()
    const router = useRouter()
    const { toast } = useToast()
    const [agent, setAgent] = useState<Agent | null>(null)
    const [loading, setLoading] = useState(true)
    const [refreshFiles, setRefreshFiles] = useState(0)

    // Widget Customization State
    const searchParams = useSearchParams()
    const [activeTab, setActiveTab] = useState(searchParams.get('tab') || "overview")

    // Form Data State
    const [formData, setFormData] = useState({
        name: "",
        role: "",
        description: "",
        system_prompt: "",
        api_key: ""
    })

    // Widget Customization State
    const [widgetColor, setWidgetColor] = useState("#000000")
    const [iconSize, setIconSize] = useState(60)

    useEffect(() => {
        const fetchAgent = async () => {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) {
                router.push("/login")
                return
            }

            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/agents/${agentId}`, {
                    headers: {
                        "Authorization": `Bearer ${session.access_token}`
                    }
                })

                if (!res.ok) throw new Error("Failed to fetch agent")

                const data = await res.json()
                setAgent(data)

                // Initialize form data
                setFormData({
                    name: data.name,
                    role: data.role,
                    description: data.description || "",
                    system_prompt: data.system_prompt || "",
                    api_key: data.api_key || ""
                })
            } catch (error) {
                toast({
                    title: "Error",
                    description: "Could not load agent details",
                    variant: "destructive",
                })
                router.push("/dashboard")
            } finally {
                setLoading(false)
            }
        }

        if (agentId) fetchAgent()
    }, [agentId, router, toast])

    const handleSave = async () => {
        const supabase = createClient()
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) return

        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/agents/${agentId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify(formData)
            })

            if (!res.ok) throw new Error("Failed to update agent")

            // Update local agent state to reflect name change immediately in header
            setAgent(prev => prev ? { ...prev, ...formData } : null)

            toast({
                title: "Success",
                description: "Agent updated successfully",
            })
        } catch (error) {
            toast({
                title: "Error",
                description: "Failed to save changes",
                variant: "destructive",
            })
        }
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
            </div>
        )
    }

    if (!agent) return null

    return (
        <div className="min-h-screen bg-background p-8">
            {/* Header */}
            <div className="max-w-5xl mx-auto mb-8 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")}>
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
                        <p className="text-muted-foreground">{agent.role}</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setActiveTab("chat")}>Test Chat</Button>
                    <Button onClick={handleSave}>Save Changes</Button>
                </div>
            </div>

            <div className="max-w-5xl mx-auto">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-6">
                    <TabsList className="grid w-full grid-cols-5 lg:w-[750px]">
                        <TabsTrigger value="overview" className="flex items-center gap-2">
                            <LayoutDashboard className="h-4 w-4" />
                            Overview
                        </TabsTrigger>
                        <TabsTrigger value="chat" className="flex items-center gap-2">
                            <MessageSquare className="h-4 w-4" />
                            Chat (Playground)
                        </TabsTrigger>
                        <TabsTrigger value="knowledge" className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            Knowledge Base
                        </TabsTrigger>
                        <TabsTrigger value="integration" className="flex items-center gap-2">
                            <Code className="h-4 w-4" />
                            Integration
                        </TabsTrigger>
                        <TabsTrigger value="settings" className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Settings
                        </TabsTrigger>
                    </TabsList>

                    {/* OVERVIEW TAB */}
                    <TabsContent value="overview" className="space-y-6">
                        <div className="grid gap-6 md:grid-cols-2">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Core Identity</CardTitle>
                                    <CardDescription>Define how your agent introduces itself and behaves.</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Name</label>
                                        <Input
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Role</label>
                                        <Input
                                            value={formData.role}
                                            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Description</label>
                                        <Textarea
                                            value={formData.description}
                                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        />
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Model Configuration</CardTitle>
                                    <CardDescription>Select the AI model and adjust parameters.</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Gemini API Key</label>
                                        <Input
                                            type="password"
                                            value={formData.api_key}
                                            onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                                            placeholder="Update API Key"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Model</label>
                                        <Input defaultValue={agent.model} disabled />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">System Prompt</label>
                                        <Textarea
                                            className="min-h-[200px] font-mono text-sm"
                                            value={formData.system_prompt}
                                            onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>

                    {/* CHAT TAB */}
                    <TabsContent value="chat" className="space-y-4">
                        <Card>
                            <CardHeader>
                                <CardTitle>Chat Playground</CardTitle>
                                <CardDescription>Test your agent's responses in real-time.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ChatInterface agentId={agent.id} />
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* KNOWLEDGE TAB */}
                    < TabsContent value="knowledge" >
                        <Card>
                            <CardHeader>
                                <CardTitle>Knowledge Base</CardTitle>
                                <CardDescription>
                                    Upload documents (PDF, TXT) that your agent can reference during conversations.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <FileUpload
                                    agentId={agent.id}
                                    onUploadComplete={() => setRefreshFiles(prev => prev + 1)}
                                />
                                <div className="mt-6">
                                    <h3 className="text-sm font-medium mb-3">Uploaded Files</h3>
                                    <FileList agentId={agent.id} refreshTrigger={refreshFiles} />
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                    {/* INTEGRATION TAB */}
                    <TabsContent value="integration">
                        <Card>
                            <CardHeader>
                                <CardTitle>Embed Your Agent</CardTitle>
                                <CardDescription>Add this agent to your website with a single line of code.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid gap-6 md:grid-cols-2 mb-6">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Widget Color</label>
                                        <div className="flex items-center gap-2">
                                            <Input
                                                type="color"
                                                value={widgetColor}
                                                onChange={(e) => setWidgetColor(e.target.value)}
                                                className="w-12 h-10 p-1 cursor-pointer"
                                            />
                                            <Input
                                                value={widgetColor}
                                                onChange={(e) => setWidgetColor(e.target.value)}
                                                className="font-mono"
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">Icon Size (px)</label>
                                        <Input
                                            type="number"
                                            value={iconSize}
                                            onChange={(e) => setIconSize(Number(e.target.value))}
                                            min={30}
                                            max={100}
                                        />
                                    </div>
                                </div>

                                <div className="rounded-lg border bg-muted p-4">
                                    <pre className="overflow-x-auto text-sm">
                                        <code>
                                            {`<script 
  src="${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/widget.js" 
  data-agent-id="${agent.id}"
  data-color="${widgetColor}"
  data-icon-size="${iconSize}"
></script>`}
                                        </code>
                                    </pre>
                                    <div className="mt-4 flex justify-end">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => {
                                                const script = `<script 
  src="${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/widget.js" 
  data-agent-id="${agent.id}"
  data-color="${widgetColor}"
  data-icon-size="${iconSize}"
></script>`
                                                navigator.clipboard.writeText(script)
                                                toast({ title: "Copied!", description: "Script copied to clipboard" })
                                            }}
                                        >
                                            Copy Code
                                        </Button>
                                    </div>
                                </div>

                                <div className="text-sm text-muted-foreground">
                                    <p><strong>Instructions:</strong></p>
                                    <ol className="list-decimal ml-4 mt-2 space-y-1">
                                        <li>Copy the code snippet above.</li>
                                        <li>Paste it anywhere in your website's <code>&lt;body&gt;</code> tag.</li>
                                        <li>A chat bubble will appear in the bottom-right corner.</li>
                                    </ol>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* SETTINGS TAB */}
                    <TabsContent value="settings">
                        <Card>
                            <CardHeader>
                                <CardTitle>Danger Zone</CardTitle>
                                <CardDescription>Irreversible actions.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <Button variant="destructive" className="gap-2">
                                    <Trash2 className="w-4 h-4" /> Delete Agent
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    )
}
