import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Message } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface MessageMetadataModalProps {
    message: Message | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function MessageMetadataModal({
    message,
    open,
    onOpenChange,
}: MessageMetadataModalProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-lg md:max-w-2xl max-h-[90vh] sm:max-h-[80vh] p-0 flex flex-col">
                <DialogHeader className="px-4 sm:px-6 pt-4 sm:pt-6 pb-3 sm:pb-4 border-b shrink-0">
                    <DialogTitle>Message Metadata</DialogTitle>
                    <DialogDescription>
                        Detailed information about this message
                    </DialogDescription>
                </DialogHeader>
                <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6">
                    {message && (
                        <div className="space-y-4">
                            {/* Basic Info */}
                            <div className="space-y-2">
                                <h3 className="text-sm font-semibold">Basic Information</h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-sm">
                                    <div>
                                        <span className="text-muted-foreground">Role:</span>
                                        <span className="ml-2 capitalize">{message.role}</span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Message ID:</span>
                                        <span className="ml-2">{message.id}</span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Created:</span>
                                        <span className="ml-2">
                                            {formatDate(message.created_at)}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">Updated:</span>
                                        <span className="ml-2">
                                            {formatDate(message.updated_at)}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Token Usage */}
                            {message.extra_metadata?.usage && (
                                <div className="space-y-2">
                                    <h3 className="text-sm font-semibold">Token Usage</h3>
                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 text-sm">
                                        <div className="p-3 rounded-lg bg-muted">
                                            <div className="text-muted-foreground text-xs">Prompt Tokens</div>
                                            <div className="text-base sm:text-lg font-semibold mt-1">
                                                {message.extra_metadata.usage.prompt_tokens?.toLocaleString() || 'N/A'}
                                            </div>
                                        </div>
                                        <div className="p-3 rounded-lg bg-muted">
                                            <div className="text-muted-foreground text-xs">Completion Tokens</div>
                                            <div className="text-base sm:text-lg font-semibold mt-1">
                                                {message.extra_metadata.usage.completion_tokens?.toLocaleString() || 'N/A'}
                                            </div>
                                        </div>
                                        <div className="p-3 rounded-lg bg-muted">
                                            <div className="text-muted-foreground text-xs">Total Tokens</div>
                                            <div className="text-base sm:text-lg font-semibold mt-1">
                                                {message.extra_metadata.usage.total_tokens?.toLocaleString() || 'N/A'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Model Info */}
                            {message.extra_metadata?.model && (
                                <div className="space-y-2">
                                    <h3 className="text-sm font-semibold">Model Information</h3>
                                    <div className="text-sm">
                                        <span className="text-muted-foreground">Model:</span>
                                        <span className="ml-2 font-mono break-all">{message.extra_metadata.model}</span>
                                    </div>
                                    {message.extra_metadata.finish_reason && (
                                        <div className="text-sm">
                                            <span className="text-muted-foreground">Finish Reason:</span>
                                            <span className="ml-2 capitalize">{message.extra_metadata.finish_reason}</span>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Raw Metadata */}
                            {message.extra_metadata && (
                                <div className="space-y-2">
                                    <h3 className="text-sm font-semibold">Raw Metadata</h3>
                                    <pre className="p-3 rounded-lg bg-muted text-xs overflow-x-auto max-w-full">
                                        {JSON.stringify(message.extra_metadata, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* No Metadata Message */}
                            {!message.extra_metadata && (
                                <div className="text-sm text-muted-foreground text-center py-4">
                                    No additional metadata available for this message
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

