'use client'

import { createClient } from '@/lib/supabase/client'
import { getApiUrl } from '@/lib/utils'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { ArrowLeft, Info } from 'lucide-react'
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card'

export default function NewAgentPage() {
    const router = useRouter()
    const supabase = createClient()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault()
        setLoading(true)
        setError(null)

        const formData = new FormData(event.currentTarget)
        const data = {
            name: formData.get('name') as string,
            role: formData.get('role') as string,
            description: formData.get('description') as string,
            model: formData.get('model') as string,
            system_prompt: formData.get('system_prompt') as string,
            api_key: formData.get('api_key') as string,
        }

        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) throw new Error('Not authenticated')

            const res = await fetch(`${getApiUrl()}/api/v1/agents/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`
                },
                body: JSON.stringify(data)
            })

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({ detail: 'Failed to create agent' }));
                console.error("Backend Error:", errorData);
                throw new Error(errorData.detail || 'Failed to create agent');
            }

            router.push('/dashboard')
            router.refresh()
        } catch (e: any) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container max-w-2xl mx-auto py-10">
            <Link href="/dashboard" className="flex items-center text-sm text-muted-foreground mb-6 hover:text-foreground transition-colors">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Dashboard
            </Link>

            <Card>
                <CardHeader>
                    <CardTitle>Create New Agent</CardTitle>
                    <CardDescription>
                        Configure your AI agent's personality and capabilities.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={onSubmit} className="space-y-6">
                        {error && (
                            <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-200">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="name">Name</Label>
                            <Input id="name" name="name" placeholder="e.g. Support Bot 3000" required />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="role">Role</Label>
                            <Input id="role" name="role" placeholder="e.g. Customer Support Specialist" defaultValue="Assistant" required />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">Description (Optional)</Label>
                            <Input id="description" name="description" placeholder="Short description for the dashboard" />
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <Label htmlFor="api_key">Gemini API Key</Label>
                                <HoverCard>
                                    <HoverCardTrigger>
                                        <Info className="h-4 w-4 text-muted-foreground cursor-pointer" />
                                    </HoverCardTrigger>
                                    <HoverCardContent className="w-80">
                                        <div className="space-y-2">
                                            <h4 className="text-sm font-semibold">How to get a key</h4>
                                            <ol className="text-xs list-decimal ml-4 space-y-1">
                                                <li>Go to <a href="https://aistudio.google.com/" target="_blank" className="underline text-blue-500">Google AI Studio</a></li>
                                                <li>Sign in with your Google account</li>
                                                <li>Select "Get API Key" on the left</li>
                                                <li>Click "Create API Key"</li>
                                                <li>Copy and paste it here</li>
                                            </ol>
                                        </div>
                                    </HoverCardContent>
                                </HoverCard>
                            </div>
                            <Input id="api_key" name="api_key" type="password" placeholder="AIzaSy..." required />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="model">Model</Label>
                            <Select name="model" defaultValue="gemini-2.5-flash-lite">
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a model" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite - Fast & Cost Effective</SelectItem>
                                    <SelectItem value="gemini-1.5-flash">Gemini 1.5 Flash - Balanced Performance</SelectItem>
                                    <SelectItem value="gemini-1.5-pro">Gemini 1.5 Pro - High Reasoning</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="system_prompt">System Prompt</Label>
                            <Textarea
                                id="system_prompt"
                                name="system_prompt"
                                placeholder="You are a helpful AI assistant..."
                                className="min-h-[150px]"
                            />
                            <p className="text-xs text-muted-foreground">
                                Instructions that define how the agent behaves.
                            </p>
                        </div>

                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? 'Creating...' : 'Create Agent'}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
