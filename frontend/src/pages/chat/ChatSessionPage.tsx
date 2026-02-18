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
import { TranscribeRepository } from "@/repositories/transcribe";
import { formatFileSize } from "@/lib/utils";
import { MessageItem } from "@/components/chat/MessageItem";
import { MessageMetadataModal } from "@/components/chat/MessageMetadataModal";
import { ChatInputArea } from "@/components/chat/ChatInputArea";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { v4 as uuidv4 } from 'uuid';

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
    const [micDisabled, setMicDisabled] = useState(false);
    const [micDisabledReason, setMicDisabledReason] = useState<string | undefined>(undefined);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    const [sessionLoading, setSessionLoading] = useState(true);
    const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
    const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    const [editedTitle, setEditedTitle] = useState('');
    const [updatingTitle, setUpdatingTitle] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [deletingSession, setDeletingSession] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [visibleThinking, setVisibleThinking] = useState<Set<string>>(new Set());

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
            loadSession(sessionId);
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

    const updateMicAvailability = async () => {
        const mediaDevices = navigator.mediaDevices;

        if (!mediaDevices?.getUserMedia || !mediaDevices?.enumerateDevices) {
            setMicDisabled(true);
            setMicDisabledReason('Microphone is not supported in this browser');
            return;
        }

        // If permission API is available and explicitly denied, we can disable proactively
        try {
            if ((navigator as any).permissions?.query) {
                const status = await (navigator as any).permissions.query({ name: 'microphone' });
                if (status?.state === 'denied') {
                    setMicDisabled(true);
                    setMicDisabledReason('Microphone permission is blocked');
                    return;
                }
            }
        } catch {
            // ignore; permission API not supported everywhere
        }

        try {
            const devices = await mediaDevices.enumerateDevices();
            const hasAudioInput = devices.some((d) => d.kind === 'audioinput');
            if (!hasAudioInput) {
                setMicDisabled(true);
                setMicDisabledReason('No microphone device detected');
                return;
            }
        } catch {
            // If device enumeration fails (rare), don't hard-disable; let getUserMedia decide.
        }

        setMicDisabled(false);
        setMicDisabledReason(undefined);
    };

    useEffect(() => {
        updateMicAvailability();

        // Keep state updated if devices/permissions change
        const mediaDevices = navigator.mediaDevices as any;
        const onDeviceChange = () => updateMicAvailability();
        if (mediaDevices?.addEventListener) {
            mediaDevices.addEventListener('devicechange', onDeviceChange);
        } else if (mediaDevices) {
            mediaDevices.ondevicechange = onDeviceChange;
        }

        let permissionStatus: any;
        (async () => {
            try {
                if ((navigator as any).permissions?.query) {
                    permissionStatus = await (navigator as any).permissions.query({ name: 'microphone' });
                    if (permissionStatus) {
                        permissionStatus.onchange = () => updateMicAvailability();
                    }
                }
            } catch {
                // ignore
            }
        })();

        return () => {
            stopRecording();
            try {
                if (mediaDevices?.removeEventListener) {
                    mediaDevices.removeEventListener('devicechange', onDeviceChange);
                } else if (mediaDevices) {
                    mediaDevices.ondevicechange = null;
                }
                if (permissionStatus) {
                    permissionStatus.onchange = null;
                }
            } catch {
                // ignore
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const loadSession = async (id: string) => {
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

    const loadMessages = async (sessionId: string) => {
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

        if (micDisabled) {
            toast.error(micDisabledReason || 'Microphone unavailable');
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
            // Update UI state so the mic button can reflect blocked permission
            await updateMicAvailability();
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
            id: uuidv4(),
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


    const handleSessionClick = (sessionId: string) => {
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

    const toggleThinking = (messageId: string) => {
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
                <ChatHeader
                    title={session?.title || 'Chat Session'}
                    isEditingTitle={isEditingTitle}
                    editedTitle={editedTitle}
                    updatingTitle={updatingTitle}
                    mobileMenuOpen={mobileMenuOpen}
                    onMobileMenuClick={() => setMobileMenuOpen(true)}
                    onStartEditTitle={handleStartEditTitle}
                    onCancelEditTitle={handleCancelEditTitle}
                    onSaveTitle={handleSaveTitle}
                    onEditTitleChange={setEditedTitle}
                    onDeleteClick={() => setShowDeleteDialog(true)}
                    titleInputRef={titleInputRef}
                />
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
                                messages.map((message) => (
                                    <MessageItem
                                        key={message.id}
                                        message={message}
                                        isThinkingVisible={visibleThinking.has(message.id)}
                                        isSpeaking={speakingMessageId === message.id}
                                        onToggleThinking={() => toggleThinking(message.id)}
                                        onReadAloud={() => handleReadAloud(message)}
                                        onShowMetadata={() => setSelectedMessage(message)}
                                    />
                                ))
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </ScrollArea>
                </div>

                <ChatInputArea
                    inputValue={inputValue}
                    files={files}
                    sending={sending}
                    transcribing={transcribing}
                    recording={recording}
                    micDisabled={micDisabled}
                    micDisabledReason={micDisabledReason}
                    sessionModelName={session?.model_name}
                    models={models}
                    onInputChange={setInputValue}
                    onSend={handleSend}
                    onFileSelect={handleFileSelect}
                    onRemoveFile={handleRemoveFile}
                    onRecordAudio={handleRecordAudio}
                    formatFileSize={formatFileSize}
                />
            </div>

            <MessageMetadataModal
                message={selectedMessage}
                open={!!selectedMessage}
                onOpenChange={(open) => !open && setSelectedMessage(null)}
            />

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