"use client"

import { getApiUrl } from "@/lib/utils"

export default function DebugPage() {
    const envVar = process.env.NEXT_PUBLIC_API_URL
    const helperUrl = getApiUrl()

    return (
        <div className="p-8 space-y-4 font-mono">
            <h1 className="text-xl font-bold">Environment Variable Debugger</h1>
            <div className="border p-4 rounded bg-muted/20">
                <p><strong>Raw process.env.NEXT_PUBLIC_API_URL:</strong> {envVar || "(undefined)"}</p>
                <p><strong>Helper getApiUrl():</strong> {helperUrl}</p>
            </div>

            <div className="text-sm text-muted-foreground bg-yellow-100 p-4 rounded text-yellow-800">
                <strong>Checklist:</strong>
                <ul className="list-disc ml-4 space-y-1 mt-2">
                    <li>Go to Vercel Project Settings &rarr; Environment Variables.</li>
                    <li>Ensure <code>NEXT_PUBLIC_API_URL</code> is set.</li>
                    <li>Ensure it is enabled for <strong>Production</strong> environment.</li>
                    <li><strong>Did you click "Redeploy" after adding it?</strong></li>
                </ul>
            </div>
        </div>
    )
}
