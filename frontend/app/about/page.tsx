import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowRight, Bot, BookOpen, Code, Lightbulb, Settings, Zap } from "lucide-react"

export default function AboutPage() {
    return (
        <div className="flex flex-col min-h-screen">
            {/* Header */}
            <section className="py-20 md:py-28 text-center bg-muted/20 flex flex-col items-center justify-center">
                <div className="container px-4 flex flex-col items-center">
                    <h1 className="text-4xl font-bold tracking-tight md:text-5xl mb-6 max-w-3xl">Mastering Kiwin</h1>
                    <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
                        Your comprehensive guide to building, training, and deploying intelligent AI agents.
                    </p>
                    <div className="flex justify-center gap-4">
                        <Link href="/login?mode=signup">
                            <Button size="lg">Start Building Now</Button>
                        </Link>
                    </div>
                </div>
            </section>

            <div className="container px-4 py-16 max-w-4xl mx-auto space-y-16">

                {/* Mission Section */}
                <section className="space-y-6">
                    <div className="flex items-center gap-2 text-primary">
                        <Lightbulb className="w-6 h-6" />
                        <h2 className="text-2xl font-bold">What is Kiwin?</h2>
                    </div>
                    <p className="text-lg leading-relaxed text-muted-foreground">
                        Kiwin is a no-code platform designed to democratize AI. We believe everyone should be able to create custom AI assistants without needing to write complex code. Whether you need a customer support bot, an internal research assistant, or a creative writing aide, Kiwin provides the infrastructure to bring your agent to life in minutes.
                    </p>
                </section>

                {/* How It Works (Detailed) */}
                <section className="space-y-8">
                    <div className="flex items-center gap-2 text-primary">
                        <Settings className="w-6 h-6" />
                        <h2 className="text-2xl font-bold">Getting Started Guide</h2>
                    </div>

                    <div className="grid gap-8 md:grid-cols-1">
                        <div className="flex gap-6 p-6 border rounded-xl bg-card">
                            <div className="p-3 bg-primary/10 rounded-lg h-fit">
                                <Bot className="w-6 h-6 text-primary" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-xl font-bold">1. Create Your Agent</h3>
                                <p className="text-muted-foreground">
                                    Upon logging in, go to the Dashboard and click <strong>"Create Agent"</strong>. Give your agent a name and a persona. The "System Prompt" is crucial—it defines how your agent behaves. Be specific!
                                    <br /><em className="text-sm">Example: "You are a helpful travel assistant who loves suggesting hidden gems."</em>
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-6 p-6 border rounded-xl bg-card">
                            <div className="p-3 bg-primary/10 rounded-lg h-fit">
                                <BookOpen className="w-6 h-6 text-primary" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-xl font-bold">2. Train with Knowledge (RAG)</h3>
                                <p className="text-muted-foreground">
                                    Standard AI models know a lot, but they don't know <em>your</em> business. In the agent details page, locate the <strong>"Knowledge"</strong> tab. Upload PDF documents here. Your agent will automatically read and reference these files when answering questions.
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-6 p-6 border rounded-xl bg-card">
                            <div className="p-3 bg-primary/10 rounded-lg h-fit">
                                <Code className="w-6 h-6 text-primary" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-xl font-bold">3. Embed Anywhere</h3>
                                <p className="text-muted-foreground">
                                    Once tested, go to the <strong>"Integration"</strong> tab. Copy the provided Javascript snippet. You can paste this code into the <code>&lt;body&gt;</code> of any website (WordPress, React, plain HTML) to instantly add your chat widget.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Advanced Features */}
                <section className="space-y-6">
                    <div className="flex items-center gap-2 text-primary">
                        <Zap className="w-6 h-6" />
                        <h2 className="text-2xl font-bold">Advanced Features</h2>
                    </div>
                    <ul className="grid gap-4 md:grid-cols-2">
                        <li className="p-4 border rounded-lg">
                            <strong className="block mb-1">Model Selection</strong>
                            <span className="text-muted-foreground text-sm">Switch between Gemini 1.5 Flash (faster, cheaper) and Pro (smarter, detailed) based on your needs.</span>
                        </li>
                        <li className="p-4 border rounded-lg">
                            <strong className="block mb-1">Custom Tools</strong>
                            <span className="text-muted-foreground text-sm">Enable "Web Search" or "Calculator" to give your agent super-powers beyond just text generation.</span>
                        </li>
                        <li className="p-4 border rounded-lg">
                            <strong className="block mb-1">Widget Customization</strong>
                            <span className="text-muted-foreground text-sm">Change the color, icon size, and position of the chat bubble to match your brand identity.</span>
                        </li>
                        <li className="p-4 border rounded-lg">
                            <strong className="block mb-1">Secure API</strong>
                            <span className="text-muted-foreground text-sm">Your agents communicate securely via encrypted API tokens.</span>
                        </li>
                    </ul>
                </section>

            </div>
        </div>
    )
}
