import { Button } from "@/components/ui/button";
import { Copy, Volume2, VolumeX, Info, Eye, EyeOff, FileText, Paperclip, Download } from "lucide-react";
import { Message } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { formatFileSize } from "@/lib/utils";
import { toast } from "sonner";
import { parseMessageContent } from "./messageUtils";

interface MessageItemProps {
    message: Message;
    isThinkingVisible: boolean;
    isSpeaking: boolean;
    onToggleThinking: () => void;
    onReadAloud: () => void;
    onShowMetadata: () => void;
}

const getFileIcon = (fileType: string) => {
    if (fileType.startsWith('text/')) {
        return FileText;
    }
    return Paperclip;
};

const getMarkdownComponents = (isUser: boolean) => ({
    p: ({ children }: any) => <p className="mb-2 last:mb-0 whitespace-break-spaces">{children}</p>,
    ul: ({ children }: any) => <ul className="mb-2 last:mb-0 ml-4 list-disc">{children}</ul>,
    ol: ({ children }: any) => <ol className="mb-2 last:mb-0 ml-4 list-decimal">{children}</ol>,
    li: ({ children }: any) => <li className="mb-1">{children}</li>,
    code: ({ className, children, ...props }: any) => {
        const isInline = !className;
        const codeBg = isUser ? 'bg-primary-foreground/20' : 'bg-muted';
        const codeText = isUser ? 'text-primary-foreground' : 'text-foreground';
        return isInline ? (
            <code className={`px-1.5 py-0.5 rounded ${codeBg} ${codeText} text-xs sm:text-sm font-mono`} {...props}>
                {children}
            </code>
        ) : (
            <code className={`${className} block whitespace-pre`} {...props}>
                {children}
            </code>
        );
    },
    pre: ({ children }: any) => {
        const preBg = isUser ? 'bg-primary-foreground/10' : 'bg-muted';
        const preText = isUser ? 'text-primary-foreground' : 'text-foreground';
        const preBorder = isUser ? 'border-primary-foreground/20' : 'border-border';
        return (
            <pre className={`p-2 sm:p-3 rounded-lg border text-xs sm:text-sm ${preBorder} ${preBg} ${preText} overflow-auto max-h-[350px] mb-2 last:mb-0 w-full min-w-0`}>
                {children}
            </pre>
        );
    },
    h1: ({ children }: any) => <h1 className="text-2xl sm:text-3xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-xl sm:text-2xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-lg sm:text-xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h3>,
    blockquote: ({ children }: any) => {
        const borderColor = isUser ? 'border-primary-foreground/30' : 'border-muted-foreground/30';
        return (
            <blockquote className={`border-l-4 pl-4 italic my-2 whitespace-break-spaces ${borderColor}`}>
                {children}
            </blockquote>
        );
    },
    a: ({ href, children }: any) => {
        const linkColor = isUser
            ? 'text-primary-foreground underline decoration-primary-foreground/50'
            : 'text-primary underline';
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className={`${linkColor} hover:opacity-80`}>
                {children}
            </a>
        );
    },
    table: ({ children }: any) => {
        const borderColor = isUser ? 'border-primary-foreground/20' : 'border-border';
        return (
            <div className="overflow-auto my-2 max-h-[400px] w-full">
                <table className={`border-collapse border ${borderColor} text-xs sm:text-sm w-full min-w-full`}>
                    {children}
                </table>
            </div>
        );
    },
    th: ({ children }: any) => {
        const borderColor = isUser ? 'border-primary-foreground/20' : 'border-border';
        return (
            <th className={`border ${borderColor} px-2 sm:px-3 py-1 sm:py-2 font-semibold`}>
                {children}
            </th>
        );
    },
    td: ({ children }: any) => {
        const borderColor = isUser ? 'border-primary-foreground/20' : 'border-border';
        return (
            <td className={`border ${borderColor} px-2 sm:px-3 py-1 sm:py-2`}>
                {children}
            </td>
        );
    },
});

const getThinkingMarkdownComponents = (isUser: boolean) => ({
    p: ({ children }: any) => <p className="mb-2 last:mb-0 whitespace-break-spaces text-xs opacity-80">{children}</p>,
    code: ({ className, children, ...props }: any) => {
        const isInline = !className;
        const codeBg = isUser ? 'bg-primary-foreground/20' : 'bg-muted';
        const codeText = isUser ? 'text-primary-foreground' : 'text-foreground';
        return isInline ? (
            <code className={`px-1.5 py-0.5 rounded ${codeBg} ${codeText} text-xs font-mono`} {...props}>
                {children}
            </code>
        ) : (
            <code className={`${className} block whitespace-pre text-xs`} {...props}>
                {children}
            </code>
        );
    },
    pre: ({ children }: any) => {
        const preBg = isUser ? 'bg-primary-foreground/10' : 'bg-muted';
        const preText = isUser ? 'text-primary-foreground' : 'text-foreground';
        const preBorder = isUser ? 'border-primary-foreground/20' : 'border-border';
        return (
            <pre className={`p-2 rounded-lg border text-xs ${preBorder} ${preBg} ${preText} overflow-auto max-h-[200px] mb-2 last:mb-0 w-full min-w-0`}>
                {children}
            </pre>
        );
    },
});

export function MessageItem({
    message,
    isThinkingVisible,
    isSpeaking,
    onToggleThinking,
    onReadAloud,
    onShowMetadata,
}: MessageItemProps) {
    const isUser = message.role === 'user';
    const { hasThinking, visibleContent, thinkingContent } = parseMessageContent(message.content);

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(message.content);
        toast.success('Copied to clipboard');
    };

    return (
        <div className={`group flex flex-col p-3 ${isUser ? 'items-end' : 'items-start'}`}>
            {/* File Attachments */}
            {message.files && message.files.length > 0 && (
                <div className={`flex flex-wrap gap-2 mb-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {message.files.map((file) => {
                        const FileIcon = getFileIcon(file.file_type);
                        return (
                            <a
                                key={file.id}
                                href={"http://localhost:8000" + file.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:opacity-80 transition-opacity group/file max-w-[280px] sm:max-w-[320px]"
                            >
                                <FileIcon className="h-4 w-4 shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium truncate">
                                        {file.filename}
                                    </div>
                                    <div className="text-xs opacity-70">
                                        {formatFileSize(file.file_size)}
                                    </div>
                                </div>
                                <Download className="h-3.5 w-3.5 shrink-0 opacity-0 group-hover/file:opacity-100 transition-opacity" />
                            </a>
                        );
                    })}
                </div>
            )}

            <div
                className={`rounded-xl ${isUser
                    ? 'bg-primary text-primary-foreground max-w-[85%] sm:max-w-[80%] px-3 sm:px-4 py-2'
                    : 'w-full'
                    }`}
            >
                <div className={`text-sm sm:text-base markdown-content ${isUser
                    ? 'text-primary-foreground'
                    : 'text-foreground'
                    }`}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={getMarkdownComponents(isUser)}
                    >
                        {visibleContent}
                    </ReactMarkdown>

                    {/* Thinking Section */}
                    {hasThinking && isThinkingVisible && (
                        <div className={`mt-3 pt-3 border-t ${isUser ? 'border-primary-foreground/20' : 'border-border'}`}>
                            <div className="text-xs font-semibold mb-2 opacity-70">
                                Thinking:
                            </div>
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={getThinkingMarkdownComponents(isUser)}
                            >
                                {thinkingContent}
                            </ReactMarkdown>
                        </div>
                    )}
                </div>
            </div>
            <div className="flex gap-1 mt-1">
                {hasThinking && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                            e.stopPropagation();
                            onToggleThinking();
                        }}
                        title={isThinkingVisible ? "Hide thinking" : "Show thinking"}
                    >
                        {isThinkingVisible ? (
                            <EyeOff className="size-3" />
                        ) : (
                            <Eye className="size-3" />
                        )}
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={handleCopy}
                    title="Copy to clipboard"
                >
                    <Copy className="size-3" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => {
                        e.stopPropagation();
                        onReadAloud();
                    }}
                    title={isSpeaking ? "Stop reading" : "Read aloud"}
                >
                    {isSpeaking ? (
                        <VolumeX className="size-3" />
                    ) : (
                        <Volume2 className="size-3" />
                    )}
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => {
                        e.stopPropagation();
                        onShowMetadata();
                    }}
                    title="Message info"
                >
                    <Info className="size-3" />
                </Button>
            </div>
        </div>
    );
}

