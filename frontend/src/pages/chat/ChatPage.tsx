import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useModel } from "@/contexts/ModelContext";
import { useSession } from "@/contexts/SessionContext";
import { ChatSidebar } from "@/components/layout/ChatSidebar";
import { TranscribeRepository } from "@/repositories/transcribe";
import { SimpleChatHeader } from "@/components/chat/SimpleChatHeader";
import { WelcomeChatInput } from "@/components/chat/WelcomeChatInput";

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
    };

    const handleRemoveFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleSessionClick = (sessionId: string) => {
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
                <SimpleChatHeader
                    title="Nexus"
                    onMobileMenuClick={() => setMobileMenuOpen(true)}
                />
                <WelcomeChatInput
                    inputValue={inputValue}
                    files={files}
                    sending={sending}
                    transcribing={transcribing}
                    recording={recording}
                    selectedModel={selectedModel}
                    models={models}
                    userName={user?.name}
                    onInputChange={setInputValue}
                    onSend={handleSend}
                    onFileSelect={handleFileSelect}
                    onRemoveFile={handleRemoveFile}
                    onRecordAudio={handleRecordAudio}
                    onModelChange={setSelectedModel}
                />
            </div>
        </div>
    );
}