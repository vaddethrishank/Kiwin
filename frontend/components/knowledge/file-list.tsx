"use client"

import { useEffect, useState } from "react"
import { Trash2, FileText, File as FileIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/use-toast"
import { createClient } from "@/lib/supabase/client"
import { formatBytes, getApiUrl } from "@/lib/utils"

interface FileItem {
    id: string
    file_name: string
    file_size: number
    created_at: string
}

interface FileListProps {
    agentId: string
    refreshTrigger: number
}

export function FileList({ agentId, refreshTrigger }: FileListProps) {
    const [files, setFiles] = useState<FileItem[]>([])
    const [loading, setLoading] = useState(true)
    const { toast } = useToast()
    const supabase = createClient()

    useEffect(() => {
        fetchFiles()
    }, [agentId, refreshTrigger])

    const fetchFiles = async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            const res = await fetch(`${getApiUrl()}/api/v1/files/?agent_id=${agentId}`, {
                headers: {
                    "Authorization": `Bearer ${session.access_token}`
                }
            })

            if (res.ok) {
                const data = await res.json()
                setFiles(data)
            }
        } catch (error) {
            console.error("Failed to fetch files", error)
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (fileId: string) => {
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            const res = await fetch(`${getApiUrl()}/api/v1/files/${fileId}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${session.access_token}`
                }
            })

            if (!res.ok) throw new Error("Delete failed")

            setFiles(files.filter(f => f.id !== fileId))
            toast({
                title: "Deleted",
                description: "File removed from knowledge base",
            })
        } catch (error) {
            toast({
                title: "Error",
                description: "Failed to delete file",
                variant: "destructive",
            })
        }
    }

    if (loading) return <div className="text-sm text-muted-foreground">Loading files...</div>

    if (files.length === 0) {
        return <div className="text-sm text-muted-foreground p-8 text-center border rounded-lg border-dashed">No files uploaded yet.</div>
    }

    return (
        <div className="space-y-2">
            {files.map((file) => (
                <div key={file.id} className="flex items-center justify-between p-3 border rounded-md bg-card hover:bg-accent/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded">
                            <FileIcon className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <p className="text-sm font-medium">{file.file_name}</p>
                            <p className="text-xs text-muted-foreground">
                                {(file.file_size / 1024).toFixed(1)} KB • {new Date(file.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(file.id)} className="text-destructive hover:text-destructive hover:bg-destructive/10">
                        <Trash2 className="w-4 h-4" />
                    </Button>
                </div>
            ))}
        </div>
    )
}
