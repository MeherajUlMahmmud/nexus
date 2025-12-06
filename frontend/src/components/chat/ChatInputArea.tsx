import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Send, Square, Mic, Paperclip, X } from "lucide-react";
import { useRef } from "react";
import { Model } from "@/lib/types";

interface ChatInputAreaProps {
    inputValue: string;
    files: File[];
    sending: boolean;
    transcribing: boolean;
    recording: boolean;
    sessionModelName?: string;
    models: Model[];
    onInputChange: (value: string) => void;
    onSend: () => void;
    onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onRemoveFile: (index: number) => void;
    onRecordAudio: () => void;
    formatFileSize: (bytes: number) => string;
}

export function ChatInputArea({
    inputValue,
    files,
    sending,
    transcribing,
    recording,
    sessionModelName,
    models,
    onInputChange,
    onSend,
    onFileSelect,
    onRemoveFile,
    onRecordAudio,
    formatFileSize,
}: ChatInputAreaProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    return (
        <div className="m-3">
            <div className="max-w-4xl mx-auto">
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
                                        onClick={() => onRemoveFile(index)}
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
                        onChange={(e) => onInputChange(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                onSend();
                            }
                        }}
                        disabled={sending || transcribing}
                        rows={3}
                    />
                    <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2">
                        <Select
                            value={sessionModelName || ''}
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
                                onChange={onFileSelect}
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
                                onClick={onRecordAudio}
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
                                onClick={onSend}
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
    );
}

