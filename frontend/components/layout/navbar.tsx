"use client"

import Link from "next/link"
import { createClient } from "@/lib/supabase/client"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { LogOut, LayoutDashboard } from "lucide-react"
import { signout } from "@/app/auth/actions"
import { User } from "@supabase/supabase-js"

interface NavbarProps {
    user: User | null
}

export function Navbar({ user: initialUser }: NavbarProps) {
    const [user, setUser] = useState<User | null>(initialUser)
    const router = useRouter()
    // Create client once
    const [supabase] = useState(() => createClient())

    useEffect(() => {
        const checkUser = async () => {
            if (!initialUser) {
                const { data: { session } } = await supabase.auth.getSession()
                setUser(session?.user ?? null)
            }
        }

        checkUser()

        const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
            setUser(session?.user ?? null)
            if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
                router.refresh()
            }
            if (event === 'SIGNED_OUT') {
                setUser(null)
                router.refresh()
            }
        })

        return () => subscription.unsubscribe()
    }, [supabase, router, initialUser])

    const handleSignOut = async () => {
        await signout()
    }

    return (
        <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
            <div className="container flex h-14 max-w-screen-2xl items-center justify-between px-8">
                <div className="flex items-center gap-6">
                    <Link href="/" className="mr-6 flex items-center space-x-2">
                        <span className="font-bold text-xl inline-block bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
                            Kiwin
                        </span>
                    </Link>



                    {user && (
                        <nav className="flex items-center gap-6 text-sm font-medium">
                            <Link
                                href="/dashboard"
                                className="transition-colors hover:text-foreground/80 text-foreground/60 flex items-center gap-1"
                            >
                                <LayoutDashboard className="w-4 h-4" />
                                Dashboard
                            </Link>
                        </nav>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    <Link
                        href="/about"
                        className="text-sm font-medium transition-colors hover:text-foreground/80 text-foreground/60 mr-2"
                    >
                        About
                    </Link>
                    <Link
                        href="/contact"
                        className="text-sm font-medium transition-colors hover:text-foreground/80 text-foreground/60 mr-2"
                    >
                        Contact
                    </Link>

                    {user ? (
                        <div className="flex items-center gap-4">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleSignOut}
                                className="text-muted-foreground hover:text-foreground"
                            >
                                <LogOut className="w-4 h-4 mr-2" />
                                Sign Out
                            </Button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-4">
                            <Link href="/login">
                                <Button variant="ghost" size="sm">Login</Button>
                            </Link>
                            <Link href="/login?mode=signup">
                                <Button size="sm">Sign Up</Button>
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    )
}
