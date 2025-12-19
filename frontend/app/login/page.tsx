'use client'

import { login, signup } from '@/app/auth/actions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Suspense } from 'react'

function LoginContent() {
    const searchParams = useSearchParams()
    const error = searchParams.get('error')
    const mode = searchParams.get('mode')
    const isSignup = mode === 'signup'

    return (
        <div className="w-full lg:grid lg:min-h-[600px] lg:grid-cols-2 xl:min-h-[800px] h-screen">
            <div className="flex items-center justify-center py-12">
                <div className="mx-auto grid w-[350px] gap-6">
                    <div className="grid gap-2 text-center">
                        <h1 className="text-3xl font-bold">{isSignup ? 'Create account' : 'Login'}</h1>
                        <p className="text-balance text-muted-foreground">
                            {isSignup ? "Enter your email below to create your account" : "Enter your email below to login to your account"}
                        </p>
                    </div>
                    <form className="grid gap-4">
                        {error && (
                            <div className='p-3 text-sm text-red-500 bg-red-100 rounded-md'>
                                {error}
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
                        <div className="grid gap-2">
                            <div className="flex items-center">
                                <Label htmlFor="password">Password</Label>
                                {!isSignup && (
                                    <Link
                                        href="/forgot-password"
                                        className="ml-auto inline-block text-sm underline"
                                    >
                                        Forgot your password?
                                    </Link>
                                )}
                            </div>
                            <Input id="password" name="password" type="password" required />
                        </div>

                        {isSignup ? (
                            <Button formAction={signup} type="submit" className="w-full">
                                Sign Up
                            </Button>
                        ) : (
                            <Button formAction={login} type="submit" className="w-full">
                                Login
                            </Button>
                        )}
                    </form>
                    <div className="mt-4 text-center text-sm">
                        {isSignup ? "Already have an account? " : "Don't have an account? "}
                        <Link href={isSignup ? "/login" : "/login?mode=signup"} className="underline">
                            {isSignup ? "Login" : "Sign up"}
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

export default function LoginPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <LoginContent />
        </Suspense>
    )
}
