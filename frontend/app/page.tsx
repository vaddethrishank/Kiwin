import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { FeatureCard } from '@/components/landing/feature-card'
import { Bot, Brain, MessageSquare, Zap, Layers, Globe, ArrowRight, ShieldCheck, Code2 } from 'lucide-react'

export default async function Home() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (user) {
    redirect('/dashboard')
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative py-24 md:py-32 overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />
        <div className="container px-4 md:px-6 mx-auto flex flex-col items-center justify-center text-center space-y-8">
          <div className="space-y-4 max-w-3xl">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/70">
              Build Intelligent <span className="text-primary">AI Agents</span> in Minutes
            </h1>
            <p className="mx-auto max-w-[700px] text-muted-foreground text-lg md:text-xl leading-relaxed">
              Kiwin empowers you to create, train, and deploy custom AI agents.
              Upload your knowledge base, customize instructions, and embed anywhere.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
            <Link href="/login?mode=signup">
              <Button size="lg" className="h-12 px-8 text-lg gap-2">
                Get Started Free <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="h-12 px-8 text-lg">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-muted/30">
        <div className="container px-4 md:px-6 mx-auto">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Everything you need</h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              A complete toolkit for building production-ready AI assistants without valid coding experience.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Bot}
              title="Custom Agents"
              description="Create specialized agents with unique names, roles, and instructions tailored to your specific needs."
            />
            <FeatureCard
              icon={Brain}
              title="Knowledge Base (RAG)"
              description="Upload PDF documents to train your agents. Our RAG engine allows them to answer questions based on your data."
            />
            <FeatureCard
              icon={Code2}
              title="Embeddable Widget"
              description="Copy-paste a simple code snippet to add your trained agent to any website or application instantly."
            />
            <FeatureCard
              icon={Globe}
              title="Multi-Model Support"
              description="Switch between powerful free Groq models like Llama 3.3 70B or Gemma 2 to balance performance and speed."
            />
            <FeatureCard
              icon={ShieldCheck}
              title="Secure & Scalable"
              description="Built with enterprise-grade security. Your data is isolated, and API access is protected via secure tokens."
            />
            <FeatureCard
              icon={Zap}
              title="Real-time Tools"
              description="Equip agents with tools like web search and calculators to perform actions, not just answer questions."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24">
        <div className="container px-4 md:px-6 mx-auto">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl text-center mb-16">How It Works</h2>
          <div className="grid gap-8 md:grid-cols-3">
            {[
              { step: "01", title: "Create Agent", desc: "Define your agent's persona and select a model." },
              { step: "02", title: "Add Knowledge", desc: "Upload PDFs and documents for your agent to learn from." },
              { step: "03", title: "Deploy", desc: "Get your unique embed code and launch your agent." }
            ].map((item, i) => (
              <div key={i} className="relative flex flex-col items-center text-center p-6 space-y-4">
                <div className="text-6xl font-black text-muted/20 absolute -top-4 select-none">{item.step}</div>
                <h3 className="text-xl font-bold relative z-10">{item.title}</h3>
                <p className="text-muted-foreground relative z-10">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t bg-background/50 backdrop-blur-sm">
        <div className="container px-4 md:px-6 mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5" />
            <span className="font-bold text-lg">Kiwin</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} Kiwin. All rights reserved.
          </p>
          <div className="flex gap-4 text-sm text-muted-foreground">
            <Link href="#" className="hover:text-foreground transition-colors">Privacy</Link>
            <Link href="#" className="hover:text-foreground transition-colors">Terms</Link>
            <Link href="#" className="hover:text-foreground transition-colors">Twitter</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
