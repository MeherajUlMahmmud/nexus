import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Mic, Paperclip, Send, Square, X, Menu } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useModel } from "@/contexts/ModelContext";
import { useSession } from "@/contexts/SessionContext";
import { ChatSidebar } from "@/components/layout/ChatSidebar";
import { TranscribeRepository } from "@/repositories/transcribe";

const PENDING_MESSAGE_KEY = 'nexus_pending_message';

export default function ChatPage() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const { models, selectedModel, setSelectedModel } = useModel();
    const { createSession, refreshSessions } = useSession();

    const [inputValue, setInputValue] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const [sending, setSending] = useState(false);
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        refreshSessions();

        return () => {
            stopRecording();
        };
    }, []);

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
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

    const handleSend = async () => {
        const messageContent = inputValue.trim();
        if (!messageContent) return;

        try {
            setSending(true);
            const newSession = await createSession(selectedModel, messageContent);
            if (newSession) {
                sessionStorage.setItem(PENDING_MESSAGE_KEY, messageContent);
                setInputValue('');
                await refreshSessions();
                navigate(`/${newSession.id}`);
            } else {
                toast.error('Failed to create session');
            }
        } catch (error) {
            console.error('Failed to create session and send message:', error);
            toast.error('Failed to create session. Please try again.');
        } finally {
            setSending(false);
        }
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

    const handleSessionClick = (sessionId: number) => {
        navigate(`/${sessionId}`);
    };

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <ChatSidebar 
                onSessionClick={handleSessionClick}
                mobileMenuOpen={mobileMenuOpen}
                onMobileMenuOpenChange={setMobileMenuOpen}
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <div className="bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 sticky top-0 z-10 lg:static">
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
                            <h1 className="text-base sm:text-lg lg:text-xl font-semibold">
                                Nexus
                            </h1>
                        </div>
                    </div>
                </div>
                <div className="flex-1 flex items-center justify-center p-4">
                    <div className="text-center text-muted-foreground w-full max-w-xl">
                        <p className="text-lg font-medium mb-4">
                            Hi, {user?.name}!
                        </p>
                        <div className="flex flex-col gap-2 w-full border p-3 rounded-xl">
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
                            {/* Text Input Field */}
                            <Textarea
                                className="min-h-[80px] max-h-[200px] rounded-sm resize-none border-none shadow-none focus-visible:ring-0 p-0"
                                placeholder="How can I help you today?"
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
                                {/* Model Selection Dropdown */}
                                <Select value={selectedModel} onValueChange={setSelectedModel}>
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
                                    {/* Record Audio Button */}
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
                                    {/* Send Button */}
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