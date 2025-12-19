import { LucideIcon } from 'lucide-react';

interface FeatureCardProps {
    icon: LucideIcon;
    title: string;
    description: string;
}

export function FeatureCard({ icon: Icon, title, description }: FeatureCardProps) {
    return (
        <div className="flex flex-col p-6 space-y-4 bg-background/50 border rounded-xl backdrop-blur-sm hover:shadow-lg transition-all duration-300 hover:border-primary/20 group">
            <div className="p-3 w-fit rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Icon className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold">{title}</h3>
            <p className="text-muted-foreground leading-relaxed">
                {description}
            </p>
        </div>
    );
}
