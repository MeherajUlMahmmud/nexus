import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Send, Copy, Volume2, VolumeX, Square, Mic, Info, Paperclip, X, Edit2, Trash2, Check, X as XIcon, FileText, Download, Menu, Eye, EyeOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Message, Session } from "@/lib/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useModel } from "@/contexts/ModelContext";
import { MessageRepository } from "@/repositories/message";
import { SessionRepository } from "@/repositories/session";
import { ChatSidebar } from "@/components/layout/ChatSidebar";
import { useSession } from "@/contexts/SessionContext";
import { Input } from "@/components/ui/input";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TranscribeRepository } from "@/repositories/transcribe";
import { formatDate } from "@/lib/utils";

const PENDING_MESSAGE_KEY = 'nexus_pending_message';

export default function ChatSessionPage() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const navigate = useNavigate();
    const { models } = useModel();

    const [session, setSession] = useState<Session | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [files, setFiles] = useState<File[]>([]);

    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    const [sessionLoading, setSessionLoading] = useState(true);
    const [speakingMessageId, setSpeakingMessageId] = useState<number | null>(null);
    const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    const [editedTitle, setEditedTitle] = useState('');
    const [updatingTitle, setUpdatingTitle] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [deletingSession, setDeletingSession] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [visibleThinking, setVisibleThinking] = useState<Set<number>>(new Set());

    const { refreshSessions } = useSession();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const titleInputRef = useRef<HTMLInputElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        if (sessionId) {
            loadSession(parseInt(sessionId));
        }
    }, [sessionId]);

    useEffect(() => {
        if (session) {
            loadMessages(session.id);
        }
    }, [session]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (session && !loading && !sending) {
            const pendingMessage = sessionStorage.getItem(PENDING_MESSAGE_KEY);
            if (pendingMessage) {
                sessionStorage.removeItem(PENDING_MESSAGE_KEY);
                sendMessage(pendingMessage);
            }
        }
    }, [session, loading, sending]);

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
    };

    const loadSession = async (id: number) => {
        try {
            setSessionLoading(true);
            const response = await SessionRepository.getSessionDetails(id);
            if (response && response.status === 'SUCCESS') {
                setSession(response.data);
            } else {
                toast.error('Failed to load session');
                navigate('/');
            }
        } catch (error) {
            console.error('Failed to load session:', error);
            toast.error('Failed to load session. Please try again.');
            navigate('/');
        } finally {
            setSessionLoading(false);
        }
    };

    const loadMessages = async (sessionId: number) => {
        try {
            setLoading(true);
            const response = await MessageRepository.getMessages(sessionId);
            if (response && response.status === 'SUCCESS') {
                setMessages(Array.isArray(response.data) ? response.data : []);
            } else {
                toast.error('Failed to load messages');
            }
        } catch (error) {
            console.error('Failed to load messages:', error);
            toast.error('Failed to load messages. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleRecordAudio = async () => {
        if (recording) {
            stopRecording();
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            audioChunksRef.current = [];

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                setRecording(false);

                if (audioChunksRef.current.length > 0) {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                    await transcribeAudio(audioBlob);
                }

                audioChunksRef.current = [];
            };

            mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event);
                toast.error('Recording failed. Please try again.');
                setRecording(false);
                stopRecording();
            };

            mediaRecorder.start();
            setRecording(true);
        } catch (error) {
            console.error('Failed to access microphone:', error);
            toast.error('Failed to access microphone. Please check permissions.');
            setRecording(false);
        }
    };

    const transcribeAudio = async (audioBlob: Blob) => {
        try {
            setTranscribing(true);
            const formData = new FormData();

            const audioFile = new File(
                [audioBlob],
                `recording-${Date.now()}.webm`,
                { type: 'audio/webm' }
            );
            formData.append('audio_file', audioFile);

            const response = await TranscribeRepository.transcribeAudio(formData);

            if (response && response.status === 'SUCCESS') {
                setInputValue(response.data.text);
            } else {
                toast.error('Failed to transcribe audio. Please try again.');
            }
        } catch (error) {
            console.error('Transcription error:', error);
            toast.error('Failed to transcribe audio. Please try again.');
        } finally {
            setTranscribing(false);
        }
    };

    const sendMessage = async (messageContent?: string) => {
        if (!session) return;

        const content = messageContent || inputValue.trim();
        // Allow sending if there's content OR files
        if (!content && files.length === 0) return;

        const userMessage: Message = {
            id: Date.now(),
            session_id: session.id,
            role: 'user',
            content: content,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        try {
            setSending(true);
            if (!messageContent) {
                setInputValue('');
            }

            setMessages((prev) => [...prev, userMessage]);

            const formData = new FormData();
            formData.append('content', content);
            for (const file of files) {
                formData.append('files', file);
            }

            const response = await MessageRepository.sendChatMessage(session.id, formData);
            if (response && response.status === 'SUCCESS') {
                setMessages((prev) => {
                    const filtered = prev.filter((msg) => msg.id !== userMessage.id);
                    return [...filtered, response.data];
                });
                await loadMessages(session.id);
                // Clear files after successful send
                setFiles([]);
            } else {
                setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id));
                toast.error(response?.message || 'Failed to send message');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id));
            toast.error('Failed to send message. Please try again.');
        } finally {
            setSending(false);
        }
    };

    const handleSend = () => {
        sendMessage();
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files || []);

        if (selectedFiles.length === 0) return;

        // Check total file count (max 2)
        if (files.length + selectedFiles.length > 2) {
            toast.error('Maximum 2 files are allowed');
            return;
        }

        // Validate file types (only text/plain)
        const invalidFiles = selectedFiles.filter(file => file.type !== 'text/plain');
        if (invalidFiles.length > 0) {
            toast.error('Only text files (.txt) are supported');
            return;
        }

        // Add valid files
        setFiles(prev => [...prev, ...selectedFiles]);

        // Reset input
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleRemoveFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const getFileIcon = (fileType: string) => {
        if (fileType.startsWith('text/')) {
            return FileText;
        }
        return Paperclip;
    };

    const handleSessionClick = (sessionId: number) => {
        navigate(`/${sessionId}`);
    };

    const handleStartEditTitle = () => {
        if (session) {
            setEditedTitle(session.title);
            setIsEditingTitle(true);
            setTimeout(() => {
                titleInputRef.current?.focus();
                titleInputRef.current?.select();
            }, 0);
        }
    };

    const handleCancelEditTitle = () => {
        setIsEditingTitle(false);
        setEditedTitle('');
    };

    const handleSaveTitle = async () => {
        if (!session || !editedTitle.trim()) {
            handleCancelEditTitle();
            return;
        }

        if (editedTitle.trim() === session.title) {
            handleCancelEditTitle();
            return;
        }

        setUpdatingTitle(true);
        try {
            const response = await SessionRepository.updateSession(session.id, {
                title: editedTitle.trim(),
            });
            if (response && response.status === 'SUCCESS') {
                setSession(response.data);
                await refreshSessions();
                toast.success('Session title updated');
                setIsEditingTitle(false);
            } else {
                toast.error(response?.message || 'Failed to update title');
            }
        } catch (error: any) {
            console.error('Failed to update title:', error);
            toast.error(error?.response?.data?.message || 'Failed to update title');
        } finally {
            setUpdatingTitle(false);
        }
    };

    const handleDeleteSession = async () => {
        if (!session) return;

        setDeletingSession(true);
        try {
            await SessionRepository.deleteSession(session.id);
            await refreshSessions();
            toast.success('Session deleted');
            navigate('/');
        } catch (error: any) {
            console.error('Failed to delete session:', error);
            toast.error(error?.response?.data?.message || 'Failed to delete session');
        } finally {
            setDeletingSession(false);
            setShowDeleteDialog(false);
        }
    };

    const parseMessageContent = (content: string) => {
        // Match <think>...</think> or <think>...</think> tags
        const redactedReasoningRegex = /<think>(.*?)<\/redacted_reasoning>/gs;
        const thinkTagRegex = /<think>(.*?)<\/think>/gs;
        
        // Check for both patterns
        const redactedMatches = [...content.matchAll(redactedReasoningRegex)];
        const thinkMatches = [...content.matchAll(thinkTagRegex)];
        
        if (redactedMatches.length === 0 && thinkMatches.length === 0) {
            return { hasThinking: false, visibleContent: content, thinkingContent: '' };
        }
        
        // Extract thinking content (prefer redacted_reasoning if present)
        const matches = redactedMatches.length > 0 ? redactedMatches : thinkMatches;
        const thinkingContent = matches.map(m => m[1]).join('\n\n');
        
        // Remove thinking tags from visible content
        let visibleContent = content;
        visibleContent = visibleContent.replace(redactedReasoningRegex, '');
        visibleContent = visibleContent.replace(thinkTagRegex, '');
        visibleContent = visibleContent.trim();
        
        return { hasThinking: true, visibleContent, thinkingContent };
    };

    const toggleThinking = (messageId: number) => {
        setVisibleThinking(prev => {
            const newSet = new Set(prev);
            if (newSet.has(messageId)) {
                newSet.delete(messageId);
            } else {
                newSet.add(messageId);
            }
            return newSet;
        });
    };

    const handleReadAloud = (message: Message) => {
        if (speakingMessageId === message.id) {
            if (window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
            }
            setSpeakingMessageId(null);
            speechSynthesisRef.current = null;
            return;
        }

        if (window.speechSynthesis.speaking && speechSynthesisRef.current) {
            window.speechSynthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(message.content);

        utterance.onend = () => {
            setSpeakingMessageId(null);
            speechSynthesisRef.current = null;
        };

        utterance.onerror = (event) => {
            setSpeakingMessageId(null);
            speechSynthesisRef.current = null;
            if (event.error !== 'interrupted') {
                toast.error('Failed to read message aloud');
            }
        };

        speechSynthesisRef.current = utterance;
        setSpeakingMessageId(message.id);
        window.speechSynthesis.speak(utterance);
    };

    useEffect(() => {
        return () => {
            if (speechSynthesisRef.current) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    if (sessionLoading) {
        return (
            <div className="flex h-screen bg-background items-center justify-center">
                <div className="text-muted-foreground">Loading session...</div>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <ChatSidebar
                currentSessionId={session?.id}
                onSessionClick={handleSessionClick}
                mobileMenuOpen={mobileMenuOpen}
                onMobileMenuOpenChange={setMobileMenuOpen}
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-h-0 ">
                {/* Header */}
                <div className="border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 sticky top-0 z-10 lg:static">
                    <div className="max-w-4xl mx-auto px-3 sm:px-4 py-3 sm:py-4 lg:pl-3 lg:pr-4">
                        <div className="flex items-center gap-2">
                            {/* Mobile Menu Button */}
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setMobileMenuOpen(true)}
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
                                        onChange={(e) => setEditedTitle(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                handleSaveTitle();
                                            } else if (e.key === 'Escape') {
                                                handleCancelEditTitle();
                                            }
                                        }}
                                        disabled={updatingTitle}
                                        className="flex-1 text-sm sm:text-base"
                                        maxLength={200}
                                    />
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={handleSaveTitle}
                                        disabled={updatingTitle || !editedTitle.trim()}
                                        className="shrink-0 h-8 w-8"
                                    >
                                        <Check className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={handleCancelEditTitle}
                                        disabled={updatingTitle}
                                        className="shrink-0 h-8 w-8"
                                    >
                                        <XIcon className="h-4 w-4" />
                                    </Button>
                                </div>
                            ) : (
                                <>
                                    <h1 className="text-base sm:text-lg lg:text-xl font-semibold truncate flex-1 min-w-0">
                                        {session?.title || 'Chat Session'}
                                    </h1>
                                    <div className="flex items-center gap-1 shrink-0">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={handleStartEditTitle}
                                            className="h-8 w-8 sm:h-9 sm:w-9"
                                            title="Edit title"
                                        >
                                            <Edit2 className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => setShowDeleteDialog(true)}
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
                {/* Messages Area */}
                <div className="flex-1 overflow-hidden">
                    <ScrollArea className="h-full">
                        <div className="max-w-4xl mx-auto space-y-4 p-3 sm:p-4">
                            {loading && messages.length === 0 ? (
                                <div className="text-center text-muted-foreground">Loading messages...</div>
                            ) : messages.length === 0 ? (
                                <div className="text-center text-muted-foreground mt-8">
                                    <p className="text-lg font-medium mb-2">Start a conversation</p>
                                    <p className="text-sm">Send a message to begin chatting</p>
                                </div>
                            ) : (
                                messages.map((message) => {
                                    const { hasThinking, visibleContent, thinkingContent } = parseMessageContent(message.content);
                                    const isThinkingVisible = visibleThinking.has(message.id);
                                    
                                    return (
                                        <div
                                            key={message.id}
                                            className={`group flex flex-col p-3 ${message.role === 'user' ? 'items-end' : 'items-start'}`}
                                        >
                                            {/* File Attachments */}
                                            {message.files && message.files.length > 0 && (
                                                <div className={`flex flex-wrap gap-2 mb-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                                    {message.files.map((file) => {
                                                        const FileIcon = getFileIcon(file.file_type);
                                                        return (
                                                            <a
                                                                key={file.id}
                                                                href={"http://localhost:8000" + file.file_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className={`
                                                                    flex items-center gap-2 px-3 py-2 rounded-lg border
                                                                    hover:opacity-80 transition-opacity group/file max-w-[280px] sm:max-w-[320px]`}
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
                                                className={`rounded-xl ${message.role === 'user'
                                                    ? 'bg-primary text-primary-foreground max-w-[85%] sm:max-w-[80%] px-3 sm:px-4 py-2'
                                                    : 'w-full'
                                                    }`}
                                            >
                                                <div className={`text-sm sm:text-base markdown-content ${message.role === 'user'
                                                    ? 'text-primary-foreground'
                                                    : 'text-foreground'
                                                    }`}>
                                                    <ReactMarkdown
                                                        remarkPlugins={[remarkGfm]}
                                                        components={{
                                                            p: ({ children }) => <p className="mb-2 last:mb-0 whitespace-break-spaces">{children}</p>,
                                                            ul: ({ children }) => <ul className="mb-2 last:mb-0 ml-4 list-disc">{children}</ul>,
                                                            ol: ({ children }) => <ol className="mb-2 last:mb-0 ml-4 list-decimal">{children}</ol>,
                                                            li: ({ children }) => <li className="mb-1">{children}</li>,
                                                            code: ({ className, children, ...props }) => {
                                                                const isInline = !className;
                                                                const codeBg = message.role === 'user'
                                                                    ? 'bg-primary-foreground/20'
                                                                    : 'bg-muted';
                                                                const codeText = message.role === 'user'
                                                                    ? 'text-primary-foreground'
                                                                    : 'text-foreground';
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
                                                            pre: ({ children }) => {
                                                                const preBg = message.role === 'user'
                                                                    ? 'bg-primary-foreground/10'
                                                                    : 'bg-muted';
                                                                const preText = message.role === 'user'
                                                                    ? 'text-primary-foreground'
                                                                    : 'text-foreground';
                                                                const preBorder = message.role === 'user'
                                                                    ? 'border-primary-foreground/20'
                                                                    : 'border-border';
                                                                return (
                                                                    <pre className={`p-2 sm:p-3 rounded-lg border text-xs sm:text-sm ${preBorder} ${preBg} ${preText} overflow-auto max-h-[350px] mb-2 last:mb-0 w-full min-w-0`}>
                                                                        {children}
                                                                    </pre>
                                                                );
                                                            },
                                                            h1: ({ children }) => <h1 className="text-2xl sm:text-3xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h1>,
                                                            h2: ({ children }) => <h2 className="text-xl sm:text-2xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h2>,
                                                            h3: ({ children }) => <h3 className="text-lg sm:text-xl font-bold whitespace-break-spaces mb-2 mt-4 first:mt-0">{children}</h3>,
                                                            blockquote: ({ children }) => {
                                                                const borderColor = message.role === 'user'
                                                                    ? 'border-primary-foreground/30'
                                                                    : 'border-muted-foreground/30';
                                                                return (
                                                                    <blockquote className={`border-l-4 pl-4 italic my-2 whitespace-break-spaces ${borderColor}`}>
                                                                        {children}
                                                                    </blockquote>
                                                                );
                                                            },
                                                            a: ({ href, children }) => {
                                                                const linkColor = message.role === 'user'
                                                                    ? 'text-primary-foreground underline decoration-primary-foreground/50'
                                                                    : 'text-primary underline';
                                                                return (
                                                                    <a href={href} target="_blank" rel="noopener noreferrer" className={`${linkColor} hover:opacity-80`}>
                                                                        {children}
                                                                    </a>
                                                                );
                                                            },
                                                            table: ({ children }) => {
                                                                const borderColor = message.role === 'user'
                                                                    ? 'border-primary-foreground/20'
                                                                    : 'border-border';
                                                                return (
                                                                    <div className="overflow-x-auto my-2">
                                                                        <table className={`border-collapse border ${borderColor} text-xs sm:text-sm`}>
                                                                            {children}
                                                                        </table>
                                                                    </div>
                                                                );
                                                            },
                                                            th: ({ children }) => {
                                                                const borderColor = message.role === 'user'
                                                                    ? 'border-primary-foreground/20'
                                                                    : 'border-border';
                                                                return (
                                                                    <th className={`border ${borderColor} px-2 sm:px-3 py-1 sm:py-2 font-semibold`}>
                                                                        {children}
                                                                    </th>
                                                                );
                                                            },
                                                            td: ({ children }) => {
                                                                const borderColor = message.role === 'user'
                                                                    ? 'border-primary-foreground/20'
                                                                    : 'border-border';
                                                                return (
                                                                    <td className={`border ${borderColor} px-2 sm:px-3 py-1 sm:py-2`}>
                                                                        {children}
                                                                    </td>
                                                                );
                                                            },
                                                        }}
                                                    >
                                                        {visibleContent}
                                                    </ReactMarkdown>
                                                    
                                                    {/* Thinking Section */}
                                                    {hasThinking && isThinkingVisible && (
                                                        <div className={`mt-3 pt-3 border-t ${message.role === 'user' ? 'border-primary-foreground/20' : 'border-border'}`}>
                                                            <div className="text-xs font-semibold mb-2 opacity-70">
                                                                Thinking:
                                                            </div>
                                                            <ReactMarkdown
                                                                remarkPlugins={[remarkGfm]}
                                                                components={{
                                                                    p: ({ children }) => <p className="mb-2 last:mb-0 whitespace-break-spaces text-xs opacity-80">{children}</p>,
                                                                    code: ({ className, children, ...props }) => {
                                                                        const isInline = !className;
                                                                        const codeBg = message.role === 'user'
                                                                            ? 'bg-primary-foreground/20'
                                                                            : 'bg-muted';
                                                                        const codeText = message.role === 'user'
                                                                            ? 'text-primary-foreground'
                                                                            : 'text-foreground';
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
                                                                    pre: ({ children }) => {
                                                                        const preBg = message.role === 'user'
                                                                            ? 'bg-primary-foreground/10'
                                                                            : 'bg-muted';
                                                                        const preText = message.role === 'user'
                                                                            ? 'text-primary-foreground'
                                                                            : 'text-foreground';
                                                                        const preBorder = message.role === 'user'
                                                                            ? 'border-primary-foreground/20'
                                                                            : 'border-border';
                                                                        return (
                                                                            <pre className={`p-2 rounded-lg border text-xs ${preBorder} ${preBg} ${preText} overflow-auto max-h-[200px] mb-2 last:mb-0 w-full min-w-0`}>
                                                                                {children}
                                                                            </pre>
                                                                        );
                                                                    },
                                                                }}
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
                                                            toggleThinking(message.id);
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
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        navigator.clipboard.writeText(message.content);
                                                        toast.success('Copied to clipboard');
                                                    }}
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
                                                        handleReadAloud(message);
                                                    }}
                                                    title={speakingMessageId === message.id ? "Stop reading" : "Read aloud"}
                                                >
                                                    {speakingMessageId === message.id ? (
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
                                                        setSelectedMessage(message);
                                                    }}
                                                    title="Message info"
                                                >
                                                    <Info className="size-3" />
                                                </Button>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </ScrollArea>
                </div>

                {/* Input Area */}
                <div className="p-3 sm:p-0 pb-3 sm:pb-0">
                    <div className="max-w-4xl mx-auto sm:mb-3">
                        <div className="flex flex-col gap-2 w-full border p-3 rounded-xl bg-background">
                            {/* Selected Files Display */}
                            {files.length > 0 && (
                                <div className="flex flex-wrap gap-2 pb-2 border-b">
                                    {files.map((file, index) => (
                                        <div
                                            key={index}
                                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted text-sm"
                                        >
                                            <Paperclip className="size-3.5 text-muted-foreground" />
                                            <span className="max-w-[200px] truncate">{file.name}</span>
                                            <span className="text-xs text-muted-foreground">
                                                ({formatFileSize(file.size)})
                                            </span>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-5 w-5 ml-1"
                                                onClick={() => handleRemoveFile(index)}
                                                disabled={sending || transcribing}
                                            >
                                                <X className="size-3" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}
                            <Textarea
                                className="min-h-[80px] max-h-[200px] rounded-sm resize-none border-none shadow-none focus-visible:ring-0 p-0 text-sm sm:text-base flex-1"
                                placeholder="Type your message..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                disabled={sending || transcribing}
                                rows={3}
                            />
                            <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2">
                                <Select
                                    value={session?.model_name || ''}
                                    disabled
                                >
                                    <SelectTrigger className="w-full sm:w-[180px]">
                                        <SelectValue placeholder="Select a model" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {models.map((model) => (
                                            <SelectItem key={model.id} value={model.id}>
                                                {model.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <div className="flex items-center gap-2">
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept=".txt,text/plain"
                                        multiple
                                        onChange={handleFileSelect}
                                        disabled={sending || transcribing || files.length >= 2}
                                        className="hidden"
                                    />
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => fileInputRef.current?.click()}
                                        disabled={sending || transcribing || files.length >= 2}
                                        title={files.length >= 2 ? "Maximum 2 files allowed" : "Attach file"}
                                        className="shrink-0"
                                    >
                                        <Paperclip className="size-4" />
                                    </Button>
                                    <Button
                                        onClick={handleRecordAudio}
                                        disabled={sending || transcribing}
                                        variant={recording ? "destructive" : "outline"}
                                        size="icon"
                                        className="flex-1 sm:flex-none"
                                    >
                                        {recording ? (
                                            <Square className="size-4" />
                                        ) : (
                                            <Mic className="size-4" />
                                        )}
                                    </Button>
                                    <Button
                                        onClick={handleSend}
                                        disabled={(!inputValue.trim() && files.length === 0) || sending || transcribing}
                                        size="icon"
                                        className="flex-1 sm:flex-none"
                                    >
                                        <Send className="size-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Message Metadata Modal */}
            <Dialog open={!!selectedMessage} onOpenChange={(open) => !open && setSelectedMessage(null)}>
                <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-lg md:max-w-2xl max-h-[90vh] sm:max-h-[80vh] p-0 flex flex-col">
                    <DialogHeader className="px-4 sm:px-6 pt-4 sm:pt-6 pb-3 sm:pb-4 border-b shrink-0">
                        <DialogTitle>Message Metadata</DialogTitle>
                        <DialogDescription>
                            Detailed information about this message
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6">
                        {selectedMessage && (
                            <div className="space-y-4">
                                {/* Basic Info */}
                                <div className="space-y-2">
                                    <h3 className="text-sm font-semibold">Basic Information</h3>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-sm">
                                        <div>
                                            <span className="text-muted-foreground">Role:</span>
                                            <span className="ml-2 capitalize">{selectedMessage.role}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Message ID:</span>
                                            <span className="ml-2">{selectedMessage.id}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Created:</span>
                                            <span className="ml-2">
                                                {formatDate(selectedMessage.created_at)}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Updated:</span>
                                            <span className="ml-2">
                                                {formatDate(selectedMessage.updated_at)}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Token Usage */}
                                {selectedMessage.extra_metadata?.usage && (
                                    <div className="space-y-2">
                                        <h3 className="text-sm font-semibold">Token Usage</h3>
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 text-sm">
                                            <div className="p-3 rounded-lg bg-muted">
                                                <div className="text-muted-foreground text-xs">Prompt Tokens</div>
                                                <div className="text-base sm:text-lg font-semibold mt-1">
                                                    {selectedMessage.extra_metadata.usage.prompt_tokens?.toLocaleString() || 'N/A'}
                                                </div>
                                            </div>
                                            <div className="p-3 rounded-lg bg-muted">
                                                <div className="text-muted-foreground text-xs">Completion Tokens</div>
                                                <div className="text-base sm:text-lg font-semibold mt-1">
                                                    {selectedMessage.extra_metadata.usage.completion_tokens?.toLocaleString() || 'N/A'}
                                                </div>
                                            </div>
                                            <div className="p-3 rounded-lg bg-muted">
                                                <div className="text-muted-foreground text-xs">Total Tokens</div>
                                                <div className="text-base sm:text-lg font-semibold mt-1">
                                                    {selectedMessage.extra_metadata.usage.total_tokens?.toLocaleString() || 'N/A'}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Model Info */}
                                {selectedMessage.extra_metadata?.model && (
                                    <div className="space-y-2">
                                        <h3 className="text-sm font-semibold">Model Information</h3>
                                        <div className="text-sm">
                                            <span className="text-muted-foreground">Model:</span>
                                            <span className="ml-2 font-mono break-all">{selectedMessage.extra_metadata.model}</span>
                                        </div>
                                        {selectedMessage.extra_metadata.finish_reason && (
                                            <div className="text-sm">
                                                <span className="text-muted-foreground">Finish Reason:</span>
                                                <span className="ml-2 capitalize">{selectedMessage.extra_metadata.finish_reason}</span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Raw Metadata */}
                                {selectedMessage.extra_metadata && (
                                    <div className="space-y-2">
                                        <h3 className="text-sm font-semibold">Raw Metadata</h3>
                                        <pre className="p-3 rounded-lg bg-muted text-xs overflow-x-auto max-w-full">
                                            {JSON.stringify(selectedMessage.extra_metadata, null, 2)}
                                        </pre>
                                    </div>
                                )}

                                {/* No Metadata Message */}
                                {!selectedMessage.extra_metadata && (
                                    <div className="text-sm text-muted-foreground text-center py-4">
                                        No additional metadata available for this message
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Delete Session Confirmation Dialog */}
            <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Session</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete this session? This action cannot be undone and all messages in this session will be permanently deleted.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deletingSession}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteSession}
                            disabled={deletingSession}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deletingSession ? 'Deleting...' : 'Delete'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}