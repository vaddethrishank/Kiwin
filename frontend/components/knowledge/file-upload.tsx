"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Upload, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/ui/use-toast"
import { createClient } from "@/lib/supabase/client"

interface FileUploadProps {
    agentId: string
    onUploadComplete: () => void
}

export function FileUpload({ agentId, onUploadComplete }: FileUploadProps) {
    const [uploading, setUploading] = useState(false)
    const router = useRouter()
    const { toast } = useToast()
    const supabase = createClient()

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        try {
            // Get session for auth token
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) throw new Error("Not authenticated")

            const formData = new FormData()
            formData.append("file", file)
            formData.append("agent_id", agentId)

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/files/upload`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: formData
            })

            if (!res.ok) {
                const error = await res.json()
                let errorMessage = "Upload failed"
                if (typeof error.detail === 'string') {
                    errorMessage = error.detail
                } else if (Array.isArray(error.detail)) {
                    // Handle Pydantic validation errors
                    errorMessage = error.detail.map((e: any) => e.msg).join(', ')
                } else if (error.message) {
                    errorMessage = error.message
                }
                throw new Error(errorMessage)
            }

            toast({
                title: "Success",
                description: "File uploaded successfully",
            })

            onUploadComplete()
            e.target.value = "" // Reset input
        } catch (error: any) {
            toast({
                title: "Error",
                description: error.message,
                variant: "destructive",
            })
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="flex items-center gap-4 p-4 border rounded-lg border-dashed bg-card/50">
            <div className="flex-1">
                <Input
                    id="file-upload"
                    type="file"
                    onChange={handleUpload}
                    disabled={uploading}
                    className="cursor-pointer"
                />
            </div>
            {uploading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
        </div>
    )
}
