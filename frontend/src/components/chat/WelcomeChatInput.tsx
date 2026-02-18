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
import { formatFileSize } from "@/lib/utils";

interface WelcomeChatInputProps {
    inputValue: string;
    files: File[];
    sending: boolean;
    transcribing: boolean;
    recording: boolean;
    selectedModel: string;
    models: Model[];
    userName?: string;
    onInputChange: (value: string) => void;
    onSend: () => void;
    onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onRemoveFile: (index: number) => void;
    onRecordAudio: () => void;
    onModelChange: (modelId: string) => void;
}

export function WelcomeChatInput({
    inputValue,
    files,
    sending,
    transcribing,
    recording,
    selectedModel,
    models,
    userName,
    onInputChange,
    onSend,
    onFileSelect,
    onRemoveFile,
    onRecordAudio,
    onModelChange,
}: WelcomeChatInputProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    return (
        <div className="flex-1 flex items-center justify-center p-4">
            <div className="text-center text-muted-foreground w-full max-w-xl">
                {userName && (
                    <p className="text-lg font-medium mb-4">
                        Hi, {userName}!
                    </p>
                )}
                <div className="flex flex-col gap-2 w-full border p-3 rounded-3xl">
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
                    {/* Text Input Field */}
                    <Textarea
                        className="min-h-[80px] max-h-[200px] rounded-sm resize-none border-none shadow-none focus-visible:ring-0 p-0"
                        placeholder="How can I help you today?"
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
                        {/* Model Selection Dropdown */}
                        <Select value={selectedModel} onValueChange={onModelChange}>
                            <SelectTrigger className="w-full sm:w-[180px] rounded-full">
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
                                onChange={(e) => {
                                    onFileSelect(e);
                                    // Reset input after selection
                                    if (fileInputRef.current) {
                                        fileInputRef.current.value = '';
                                    }
                                }}
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
                            {/* Send Button */}
                            <Button
                                onClick={onSend}
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
    );
}

