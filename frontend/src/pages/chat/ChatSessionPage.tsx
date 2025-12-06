import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Send, Copy, Volume2, VolumeX, Square, Mic } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Message, Session } from "@/lib/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useModel } from "@/contexts/ModelContext";
import { MessageRepository } from "@/repositories/message";
import { SessionRepository } from "@/repositories/session";
import { ChatSidebar } from "@/components/layout/ChatSidebar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TranscribeRepository } from "@/repositories/transcribe";

const PENDING_MESSAGE_KEY = 'nexus_pending_message';

export default function ChatSessionPage() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const navigate = useNavigate();
    const { models } = useModel();

    const [session, setSession] = useState<Session | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');

    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    const [sessionLoading, setSessionLoading] = useState(true);
    const [speakingMessageId, setSpeakingMessageId] = useState<number | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);

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
        if (!content) return;

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

            const response = await MessageRepository.sendChatMessage(session.id, content);
            if (response && response.status === 'SUCCESS') {
                setMessages((prev) => {
                    const filtered = prev.filter((msg) => msg.id !== userMessage.id);
                    return [...filtered, response.data];
                });
                await loadMessages(session.id);
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

    const handleSessionClick = (sessionId: number) => {
        navigate(`/${sessionId}`);
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
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-h-0 ">
                {/* Messages Area */}
                <div className="flex-1 overflow-hidden pt-16 lg:pt-0">
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
                                messages.map((message) => (
                                    <div
                                        key={message.id}
                                        className={`group flex flex-col p-3 ${message.role === 'user' ? 'items-end' : 'items-start'}`}
                                    >
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
                                                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
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
                                                                <code className={className} {...props}>
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
                                                                <pre className={`p-2 sm:p-3 rounded-lg border text-xs sm:text-sm ${preBorder} ${preBg} ${preText} overflow-x-auto mb-2 last:mb-0`}>
                                                                    <ScrollArea
                                                                        className="max-h-[350px] overflow-y-auto"
                                                                    >
                                                                        {children}
                                                                    </ScrollArea>
                                                                </pre>
                                                            );
                                                        },
                                                        h1: ({ children }) => <h1 className="text-2xl sm:text-3xl font-bold mb-2 mt-4 first:mt-0">{children}</h1>,
                                                        h2: ({ children }) => <h2 className="text-xl sm:text-2xl font-bold mb-2 mt-4 first:mt-0">{children}</h2>,
                                                        h3: ({ children }) => <h3 className="text-lg sm:text-xl font-bold mb-2 mt-4 first:mt-0">{children}</h3>,
                                                        blockquote: ({ children }) => {
                                                            const borderColor = message.role === 'user'
                                                                ? 'border-primary-foreground/30'
                                                                : 'border-muted-foreground/30';
                                                            return (
                                                                <blockquote className={`border-l-4 pl-4 italic my-2 ${borderColor}`}>
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
                                                    {message.content}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 mt-1">
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
                                        </div>
                                    </div>
                                ))
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </ScrollArea>
                </div>

                {/* Input Area */}
                <div className="p-3 sm:p-0 pb-3 sm:pb-0">
                    <div className="max-w-4xl mx-auto sm:mb-3">
                        <div className="flex flex-col gap-2 w-full border p-3 rounded-xl bg-background">
                            <Textarea
                                className="min-h-[80px] max-h-[200px] rounded-sm resize-none border-none shadow-none focus-visible:ring-0 p-0 text-sm sm:text-base"
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
                                        disabled={!inputValue.trim() || sending || transcribing}
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
        </div>
    );
}