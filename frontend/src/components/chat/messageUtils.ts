import { Message } from "@/lib/types";

export function parseMessageContent(content: string) {
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
}

