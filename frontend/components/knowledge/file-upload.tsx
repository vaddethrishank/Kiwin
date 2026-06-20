"use client"

import { useState } from "react"
import { Upload, Loader2, FileUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/ui/use-toast"
import { createClient } from "@/lib/supabase/client"
import { getApiUrl } from "@/lib/utils"

interface FileItem {
    id: string
    agent_id: string
    file_name: string
    file_type?: string
    file_size?: number
    created_at: string
}

interface FileUploadProps {
    agentId: string
    /** Called immediately with the new file record once storage upload completes.
     *  RAG processing will continue in the background. */
    onUploadComplete: (newFile: FileItem) => void
}

export function FileUpload({ agentId, onUploadComplete }: FileUploadProps) {
    const [uploading, setUploading] = useState(false)
    const [dragOver, setDragOver] = useState(false)
    const { toast } = useToast()
    const supabase = createClient()

    const handleUpload = async (file: File) => {
        if (!file) return

        setUploading(true)
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) throw new Error("Not authenticated")

            const formData = new FormData()
            formData.append("file", file)
            formData.append("agent_id", agentId)

            const res = await fetch(`${getApiUrl()}/api/v1/files/upload`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: formData
            })

            if (!res.ok) {
                const error = await res.json()
                let errorMessage = "Upload failed"
                if (typeof error.detail === "string") {
                    errorMessage = error.detail
                } else if (Array.isArray(error.detail)) {
                    errorMessage = error.detail.map((e: any) => e.msg).join(", ")
                } else if (error.message) {
                    errorMessage = error.message
                }
                throw new Error(errorMessage)
            }

            // ── Server responds instantly with the new file record ──────────
            // RAG processing runs in the background. We call onUploadComplete
            // immediately so the UI adds the file with a "processing" badge
            // — no freeze, no waiting for embeddings.
            const newFile: FileItem = await res.json()
            onUploadComplete(newFile)

            toast({
                title: "File uploaded",
                description: `"${file.name}" added. Processing in background…`,
            })
        } catch (error: any) {
            toast({
                title: "Upload failed",
                description: error.message,
                variant: "destructive",
            })
        } finally {
            setUploading(false)
        }
    }

    const onFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) await handleUpload(file)
        e.target.value = ""  // Reset so the same file can be re-uploaded
    }

    const onDrop = async (e: React.DragEvent<HTMLLabelElement>) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer.files?.[0]
        if (file) await handleUpload(file)
    }

    return (
        <label
            htmlFor="file-upload-input"
            className={`
                flex flex-col items-center justify-center gap-3 p-8 
                border-2 border-dashed rounded-xl cursor-pointer 
                transition-all duration-200 select-none
                ${dragOver
                    ? "border-primary bg-primary/10 scale-[1.01]"
                    : "border-border bg-card/50 hover:border-primary/60 hover:bg-accent/30"
                }
                ${uploading ? "pointer-events-none opacity-70" : ""}
            `}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
        >
            <Input
                id="file-upload-input"
                type="file"
                onChange={onFileInput}
                disabled={uploading}
                className="hidden"
                accept=".pdf,.txt,.md,.csv"
            />

            {uploading ? (
                <>
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                    <div className="text-center">
                        <p className="text-sm font-medium">Uploading file…</p>
                        <p className="text-xs text-muted-foreground">Processing will continue in background</p>
                    </div>
                </>
            ) : (
                <>
                    <div className="p-3 rounded-full bg-primary/10">
                        <FileUp className="w-6 h-6 text-primary" />
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-medium">
                            {dragOver ? "Drop to upload" : "Drop file here or click to browse"}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">PDF, TXT, MD, CSV supported</p>
                    </div>
                </>
            )}
        </label>
    )
}
