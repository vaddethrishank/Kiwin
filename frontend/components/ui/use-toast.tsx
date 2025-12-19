"use client"

import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

type ToastType = {
    id: string
    title?: string
    description?: string
    variant?: "default" | "destructive"
}

type ToastContextType = {
    toasts: ToastType[]
    toast: (t: Omit<ToastType, "id">) => void
    dismiss: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | null>(null)

export function useToast() {
    const context = React.useContext(ToastContext)
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider")
    }
    return context
}

export function Toaster() {
    const { toasts, dismiss } = useToast()

    if (toasts.length === 0) return null

    return (
        <div className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px] gap-2">
            {toasts.map((t) => (
                <div
                    key={t.id}
                    className={cn(
                        "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all",
                        t.variant === "destructive" ? "destructive group border-destructive bg-destructive text-destructive-foreground" : "bg-background border-border text-foreground"
                    )}
                >
                    <div className="grid gap-1">
                        {t.title && <div className="text-sm font-semibold">{t.title}</div>}
                        {t.description && <div className="text-sm opacity-90">{t.description}</div>}
                    </div>
                    <button
                        onClick={() => dismiss(t.id)}
                        className="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
            ))}
        </div>
    )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = React.useState<ToastType[]>([])

    const toast = React.useCallback(({ title, description, variant }: Omit<ToastType, "id">) => {
        const id = Math.random().toString(36).substring(2, 9)
        setToasts((prev) => [...prev, { id, title, description, variant }])

        // Auto dismiss
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
        }, 5000)
    }, [])

    const dismiss = React.useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }, [])

    // Also expose a global implementation if needed, but context is better.
    // However, since components might import `useToast` directly, we need to ensure the Provider is wrapping the app.

    return (
        <ToastContext.Provider value={{ toasts, toast, dismiss }}>
            {children}
            <Toaster />
        </ToastContext.Provider>
    )
}
