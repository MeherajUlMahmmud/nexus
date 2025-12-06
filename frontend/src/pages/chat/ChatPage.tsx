import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Mic, Send, Square } from "lucide-react";
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
    const [sending, setSending] = useState(false);
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

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

    const handleSessionClick = (sessionId: number) => {
        navigate(`/${sessionId}`);
    };

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <ChatSidebar onSessionClick={handleSessionClick} />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <div className="flex-1 flex items-center justify-center p-4">
                    <div className="text-center text-muted-foreground w-full max-w-xl">
                        <p className="text-lg font-medium mb-4">
                            Hi, {user?.name}!
                        </p>
                        <div className="flex flex-col gap-2 w-full border p-3 rounded-xl">
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