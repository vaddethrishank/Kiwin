'use client'

import { Button } from '@/components/ui/button'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Suspense } from 'react'

function AuthCodeErrorContent() {
    const searchParams = useSearchParams()
    const error = searchParams.get('error')

    return (
        <div className="flex h-screen w-full items-center justify-center p-4">
            <div className="mx-auto w-full max-w-md space-y-6 text-center">
                <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl">Authentication Error</h1>
                    <p className="text-muted-foreground">
                        There was a problem verifying your authentication code.
                    </p>
                </div>
                
                {error && (
                    <div className="rounded-md bg-red-100 p-4 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800 break-words">
                        <strong>Error details:</strong> {error}
                    </div>
                )}

                <div className="space-y-4 text-left text-sm text-muted-foreground">
                    <p className="font-semibold text-foreground">Common reasons for this error:</p>
                    <ul className="list-disc pl-5 space-y-2">
                        <li><strong>Link Expired:</strong> The magic link or password reset link can only be used once. If you already clicked it, you need to request a new one.</li>
                        <li><strong>Email Scanners:</strong> If the email went to your spam folder, your email provider (like Gmail or Outlook) might have automatically "scanned" the link to check for viruses. This consumes the single-use token before you even click it!</li>
                        <li><strong>No Code Provided:</strong> Your Supabase settings might not be sending the authentication code properly.</li>
                    </ul>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row justify-center mt-6">
                    <Button asChild>
                        <Link href="/login">Return to Login</Link>
                    </Button>
                    <Button asChild variant="outline">
                        <Link href="/forgot-password">Request New Reset Link</Link>
                    </Button>
                </div>
            </div>
        </div>
    )
}

export default function AuthCodeErrorPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <AuthCodeErrorContent />
        </Suspense>
    )
}
