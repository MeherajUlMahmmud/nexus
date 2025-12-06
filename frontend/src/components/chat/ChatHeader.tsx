import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Menu, Edit2, Trash2, Check, X as XIcon } from "lucide-react";

interface ChatHeaderProps {
    title: string;
    isEditingTitle: boolean;
    editedTitle: string;
    updatingTitle: boolean;
    mobileMenuOpen: boolean;
    onMobileMenuClick: () => void;
    onStartEditTitle: () => void;
    onCancelEditTitle: () => void;
    onSaveTitle: () => void;
    onEditTitleChange: (value: string) => void;
    onDeleteClick: () => void;
    titleInputRef: React.RefObject<HTMLInputElement | null>;
}

export function ChatHeader({
    title,
    isEditingTitle,
    editedTitle,
    updatingTitle,
    mobileMenuOpen,
    onMobileMenuClick,
    onStartEditTitle,
    onCancelEditTitle,
    onSaveTitle,
    onEditTitleChange,
    onDeleteClick,
    titleInputRef,
}: ChatHeaderProps) {
    return (
        <div className="border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 sticky top-0 z-10 lg:static">
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
                    {isEditingTitle ? (
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                            <Input
                                ref={titleInputRef}
                                value={editedTitle}
                                onChange={(e) => onEditTitleChange(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        onSaveTitle();
                                    } else if (e.key === 'Escape') {
                                        onCancelEditTitle();
                                    }
                                }}
                                disabled={updatingTitle}
                                className="flex-1 text-sm sm:text-base"
                                maxLength={200}
                            />
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={onSaveTitle}
                                disabled={updatingTitle || !editedTitle.trim()}
                                className="shrink-0 h-8 w-8"
                            >
                                <Check className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={onCancelEditTitle}
                                disabled={updatingTitle}
                                className="shrink-0 h-8 w-8"
                            >
                                <XIcon className="h-4 w-4" />
                            </Button>
                        </div>
                    ) : (
                        <>
                            <h1 className="text-base sm:text-lg lg:text-xl font-semibold truncate flex-1 min-w-0">
                                {title}
                            </h1>
                            <div className="flex items-center gap-1 shrink-0">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={onStartEditTitle}
                                    className="h-8 w-8 sm:h-9 sm:w-9"
                                    title="Edit title"
                                >
                                    <Edit2 className="h-4 w-4" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={onDeleteClick}
                                    className="h-8 w-8 sm:h-9 sm:w-9 text-destructive hover:text-destructive"
                                    title="Delete session"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

