import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";

interface SimpleChatHeaderProps {
    title: string;
    onMobileMenuClick: () => void;
}

export function SimpleChatHeader({ title, onMobileMenuClick }: SimpleChatHeaderProps) {
    return (
        <div className="bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 sticky top-0 z-10 lg:static">
            <div className="max-w-4xl mx-auto px-3 sm:px-4 py-3 sm:py-4 lg:pl-3 lg:pr-4">
                <div className="flex items-center gap-2">
                    {/* Mobile Menu Button */}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onMobileMenuClick}
                        className="lg:hidden h-8 w-8 sm:h-9 sm:w-9 shrink-0"
                        title="Open menu"
                    >
                        <Menu className="h-4 w-4 sm:h-5 sm:w-5" />
                    </Button>
                    <h1 className="text-base sm:text-lg lg:text-xl font-semibold">
                        {title}
                    </h1>
                </div>
            </div>
        </div>
    );
}

