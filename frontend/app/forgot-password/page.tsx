'use client'

import { forgotPassword } from '@/app/auth/actions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Suspense } from 'react'

import { useFormStatus } from 'react-dom'

function SubmitButton({ formAction, children }: { formAction: (payload: FormData) => void, children: React.ReactNode }) {
    const { pending } = useFormStatus()
    return (
        <Button formAction={formAction} type="submit" className="w-full" disabled={pending}>
            {pending ? "Sending..." : children}
        </Button>
    )
}

function ForgotPasswordContent() {
    const searchParams = useSearchParams()
    const error = searchParams.get('error')
    const message = searchParams.get('message')

    return (
        <div className="w-full lg:grid lg:min-h-[600px] lg:grid-cols-2 xl:min-h-[800px] h-screen">
            <div className="flex items-center justify-center py-12">
                <div className="mx-auto grid w-[350px] gap-6">
                    <div className="grid gap-2 text-center">
                        <h1 className="text-3xl font-bold">Forgot Password</h1>
                        <p className="text-balance text-muted-foreground">
                            Enter your email below to receive a password reset link
                        </p>
                    </div>
                    <form className="grid gap-4">
                        {error && (
                            <div className='p-3 text-sm text-red-500 bg-red-100 rounded-md'>
                                {error}
                            </div>
                        )}
                        {message && (
                            <div className='p-3 text-sm text-green-500 bg-green-100 rounded-md'>
                                {message}
                            </div>
                        )}
                        <div className="grid gap-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                name="email"
                                type="email"
                                placeholder="m@example.com"
                                required
                            />
                        </div>
                        <SubmitButton formAction={forgotPassword}>
                            Send Reset Link
                        </SubmitButton>
                    </form>
                    <div className="mt-4 text-center text-sm">
                        Remember your password?{" "}
                        <Link href="/login" className="underline">
                            Login
                        </Link>
                    </div>
                </div>
            </div>
            <div className="hidden bg-muted lg:block h-full relative">
                <div className="absolute inset-0 bg-zinc-900 border-l border-zinc-800" />
                <div className="relative z-20 flex items-center justify-center h-full">
                    <h2 className="text-3xl font-bold text-white">AI Agent Platform</h2>
                </div>
            </div>
        </div>
    )
}

export default function ForgotPasswordPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <ForgotPasswordContent />
        </Suspense>
    )
}
