'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'

import { createClient } from '@/lib/supabase/server'

export async function login(formData: FormData) {
    const supabase = await createClient()

    const email = formData.get('email') as string
    const password = formData.get('password') as string

    const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
    })

    if (error) {
        redirect('/login?error=Invalid credentials')
    }

    revalidatePath('/', 'layout')
    redirect('/dashboard')
}

export async function signup(formData: FormData) {
    const supabase = await createClient()

    const email = formData.get('email') as string
    const password = formData.get('password') as string

    const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            emailRedirectTo: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/auth/callback`,
        },
    })

    if (error) {
        console.error("Signup Error:", error.message)
        redirect(`/login?error=${encodeURIComponent(error.message)}`)
    }

    // revalidatePath('/', 'layout') 
    // Instead of redirecting to dashboard, we redirect to login with a message
    redirect('/login?mode=signup&message=Check your email for verification link')
}

export async function signout() {
    const supabase = await createClient()
    await supabase.auth.signOut()
    revalidatePath('/', 'layout')
    redirect('/')
}

export async function forgotPassword(formData: FormData) {
    const supabase = await createClient()
    const email = formData.get('email') as string

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/auth/callback?next=/reset-password`,
    })

    if (error) {
        console.error("Forgot Password Error:", error.message)
        redirect(`/forgot-password?error=${encodeURIComponent(error.message)}`)
    }

    redirect('/forgot-password?message=Password reset link sent to your email')
}

export async function resetPassword(formData: FormData) {
    const supabase = await createClient()
    const password = formData.get('password') as string
    const confirmPassword = formData.get('confirmPassword') as string

    if (password !== confirmPassword) {
        redirect('/reset-password?error=Passwords do not match')
    }

    const { error } = await supabase.auth.updateUser({
        password: password,
    })

    if (error) {
        console.error("Reset Password Error:", error.message)
        redirect(`/reset-password?error=${encodeURIComponent(error.message)}`)
    }

    redirect('/login?message=Password updated successfully, you can now log in')
}
