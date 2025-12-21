'use client'

import { createClient } from '@/lib/supabase/client'
import { getApiUrl } from '@/lib/utils'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Plus } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'

interface Agent {
    id: string
    name: string
    role: string
    description: string
    model: string
}

export default function DashboardPage() {
    const [agents, setAgents] = useState<Agent[]>([])
    const [loading, setLoading] = useState(true)
    const supabase = createClient()

    useEffect(() => {
        async function fetchAgents() {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            // Fetch from our backend API, passing the Supabase JWT
            const res = await fetch(`${getApiUrl()}/api/v1/agents/`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            })

            if (res.ok) {
                const data = await res.json()
                setAgents(data)
            }
            setLoading(false)
        }

        fetchAgents()
    }, [])

    return (
        <div className="container mx-auto py-10">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Your Agents</h1>
                    <p className="text-muted-foreground">Manage and deploy your AI workforce.</p>
                </div>
                <Link href="/agents/new">
                    <Button>
                        <Plus className="mr-2 h-4 w-4" /> New Agent
                    </Button>
                </Link>
            </div>

            {loading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="flex flex-col space-y-3">
                            <Skeleton className="h-[125px] w-full rounded-xl" />
                            <div className="space-y-2">
                                <Skeleton className="h-4 w-[250px]" />
                                <Skeleton className="h-4 w-[200px]" />
                            </div>
                        </div>
                    ))}
                </div>
            ) : agents.length === 0 ? (
                <div className="text-center py-20 border rounded-lg bg-muted/50 dashed">
                    <h3 className="text-lg font-medium">No agents yet</h3>
                    <p className="text-muted-foreground mb-4">Create your first AI agent to get started.</p>
                    <Link href="/agents/new">
                        <Button variant="outline">Create Agent</Button>
                    </Link>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {agents.map((agent) => (
                        <Card key={agent.id} className="hover:shadow-lg transition-shadow">
                            <CardHeader>
                                <CardTitle>{agent.name}</CardTitle>
                                <CardDescription>{agent.role}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-gray-500 mb-4 truncate">{agent.description || "No description"}</p>
                                <div className="flex justify-between items-center">
                                    <div className="text-xs font-mono bg-secondary px-2 py-1 rounded">
                                        {agent.model}
                                    </div>
                                    <Link href={`/agents/${agent.id}?tab=chat`}>
                                        <Button variant="ghost" size="sm">Chat</Button>
                                    </Link>
                                    <Link href={`/agents/${agent.id}`}>
                                        <Button variant="outline" size="sm">Manage</Button>
                                    </Link>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
