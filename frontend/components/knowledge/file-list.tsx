"use client"

import { useEffect, useRef, useState } from "react"
import { Trash2, File as FileIcon, Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/use-toast"
import { createClient } from "@/lib/supabase/client"
import { getApiUrl } from "@/lib/utils"

// ── Types ────────────────────────────────────────────────────────────────────

type FileStatus = "pending" | "processing" | "ready" | "error"

interface FileItem {
    id: string
    agent_id: string
    file_name: string
    file_type?: string
    file_size?: number
    created_at: string
    /** Client-side only — not persisted in DB */
    _status?: FileStatus
    /** Client-side only — SSE progress stage label */
    _stage?: string
    /** Client-side only — error message */
    _error?: string
}

interface FileListProps {
    agentId: string
    /** Bump this to force a full re-fetch from the server */
    refreshTrigger: number
    /** Optimistically-injected files from the parent (just uploaded, status = pending) */
    pendingFiles?: FileItem[]
}

// ── Stage labels ─────────────────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
    downloading: "Downloading…",
    extracting: "Extracting text…",
    chunking: "Chunking…",
    embedding: "Generating embeddings…",
    storing: "Storing vectors…",
}

// ── Sub-component: status badge ───────────────────────────────────────────────

function StatusBadge({ status, stage, error }: { status: FileStatus; stage?: string; error?: string }) {
    if (status === "processing" || status === "pending") {
        return (
            <span className="flex items-center gap-1.5 text-xs font-medium text-amber-500 bg-amber-500/10 px-2 py-1 rounded-full whitespace-nowrap">
                <Loader2 className="w-3 h-3 animate-spin" />
                {stage ? (STAGE_LABELS[stage] ?? "Processing…") : "Processing…"}
            </span>
        )
    }
    if (status === "error") {
        return (
            <span
                title={error}
                className="flex items-center gap-1.5 text-xs font-medium text-red-500 bg-red-500/10 px-2 py-1 rounded-full"
            >
                <AlertCircle className="w-3 h-3" />
                Failed
            </span>
        )
    }
    // ready
    return (
        <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Ready
        </span>
    )
}

// ── Main component ────────────────────────────────────────────────────────────

export function FileList({ agentId, refreshTrigger, pendingFiles = [] }: FileListProps) {
    const [files, setFiles] = useState<FileItem[]>([])
    const [loading, setLoading] = useState(true)
    const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
    const { toast } = useToast()
    const supabase = createClient()

    // Track active SSE connections so we can close them on unmount
    const sseRefs = useRef<Map<string, EventSource>>(new Map())

    // ── Fetch existing files ─────────────────────────────────────────────────

    useEffect(() => {
        fetchFiles()
    }, [agentId, refreshTrigger])

    const fetchFiles = async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            const res = await fetch(`${getApiUrl()}/api/v1/files/?agent_id=${agentId}`, {
                headers: { "Authorization": `Bearer ${session.access_token}` }
            })

            if (res.ok) {
                const data: FileItem[] = await res.json()
                // Mark server-fetched files as ready (they're already processed)
                setFiles(data.map(f => ({ ...f, _status: "ready" as FileStatus })))
            }
        } catch (error) {
            console.error("Failed to fetch files", error)
        } finally {
            setLoading(false)
        }
    }

    // ── Merge optimistic (pending) files from parent ─────────────────────────

    useEffect(() => {
        if (!pendingFiles.length) return

        setFiles(prev => {
            const existingIds = new Set(prev.map(f => f.id))
            const newOnes = pendingFiles.filter(f => !existingIds.has(f.id))
            if (!newOnes.length) return prev
            return [
                ...newOnes.map(f => ({ ...f, _status: "pending" as FileStatus })),
                ...prev,
            ]
        })
    }, [pendingFiles])

    // ── SSE: open progress stream for every pending/processing file ──────────

    useEffect(() => {
        files.forEach(file => {
            if (
                (file._status === "pending" || file._status === "processing") &&
                !sseRefs.current.has(file.id)
            ) {
                openSSE(file.id)
            }
        })
    }, [files])

    const openSSE = async (fileId: string) => {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) return

        // SSE with auth via query param (EventSource doesn't support custom headers)
        const url = `${getApiUrl()}/api/v1/files/progress/${fileId}?token=${session.access_token}`
        const es = new EventSource(url)

        sseRefs.current.set(fileId, es)

        es.addEventListener("progress", (e: MessageEvent) => {
            setFiles(prev =>
                prev.map(f => f.id === fileId
                    ? { ...f, _status: "processing", _stage: e.data }
                    : f
                )
            )
        })

        es.addEventListener("complete", () => {
            setFiles(prev =>
                prev.map(f => f.id === fileId
                    ? { ...f, _status: "ready", _stage: undefined, _error: undefined }
                    : f
                )
            )
            closeSSE(fileId)
        })

        es.addEventListener("error", (e: MessageEvent) => {
            const errMsg = e.data || "Processing failed"
            setFiles(prev =>
                prev.map(f => f.id === fileId
                    ? { ...f, _status: "error", _error: errMsg }
                    : f
                )
            )
            closeSSE(fileId)
            toast({
                title: "Processing failed",
                description: `Could not process file. ${errMsg}`,
                variant: "destructive",
            })
        })

        // Network-level error (e.g., connection lost)
        es.onerror = () => {
            // Don't spam — only mark as error if still processing
            setFiles(prev => prev.map(f =>
                f.id === fileId && (f._status === "pending" || f._status === "processing")
                    ? { ...f, _status: "error", _error: "Connection lost" }
                    : f
            ))
            closeSSE(fileId)
        }
    }

    const closeSSE = (fileId: string) => {
        sseRefs.current.get(fileId)?.close()
        sseRefs.current.delete(fileId)
    }

    // Close all SSE connections on unmount
    useEffect(() => {
        return () => {
            sseRefs.current.forEach(es => es.close())
            sseRefs.current.clear()
        }
    }, [])

    // ── Delete — optimistic removal, background server delete ────────────────

    const handleDelete = async (fileId: string) => {
        // Instantly remove from UI
        setFiles(prev => prev.filter(f => f.id !== fileId))
        closeSSE(fileId)

        const deletedFile = files.find(f => f.id === fileId)

        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            const res = await fetch(`${getApiUrl()}/api/v1/files/${fileId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${session.access_token}` }
            })

            if (!res.ok) throw new Error("Delete failed")

            toast({
                title: "File removed",
                description: `"${deletedFile?.file_name}" deleted from knowledge base.`,
            })
        } catch (error) {
            // Rollback: put the file back if server delete failed
            if (deletedFile) {
                setFiles(prev => [deletedFile, ...prev])
                toast({
                    title: "Delete failed",
                    description: "Could not delete the file. It has been restored.",
                    variant: "destructive",
                })
            }
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-sm text-muted-foreground p-4">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading files…
            </div>
        )
    }

    if (files.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground p-10 border rounded-xl border-dashed">
                <FileIcon className="w-8 h-8 opacity-30" />
                <p>No files uploaded yet.</p>
            </div>
        )
    }

    return (
        <div className="space-y-2">
            {files.map((file) => (
                <div
                    key={file.id}
                    className={`
                        flex items-center justify-between p-3 border rounded-lg 
                        bg-card transition-all duration-200
                        ${file._status === "error"
                            ? "border-red-500/30 bg-red-500/5"
                            : file._status === "ready"
                            ? "hover:bg-accent/40"
                            : "border-amber-500/30 bg-amber-500/5"
                        }
                    `}
                >
                    <div className="flex items-center gap-3 min-w-0">
                        <div className={`
                            p-2 rounded-lg shrink-0
                            ${file._status === "error" ? "bg-red-500/10" : "bg-primary/10"}
                        `}>
                            <FileIcon className={`w-4 h-4 ${file._status === "error" ? "text-red-500" : "text-primary"}`} />
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{file.file_name}</p>
                            <p className="text-xs text-muted-foreground">
                                {file.file_size ? `${(file.file_size / 1024).toFixed(1)} KB` : "—"} •{" "}
                                {new Date(file.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 ml-3 shrink-0">
                        <StatusBadge
                            status={file._status ?? "ready"}
                            stage={file._stage}
                            error={file._error}
                        />
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(file.id)}
                            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                            title="Delete file"
                        >
                            <Trash2 className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            ))}
        </div>
    )
}
