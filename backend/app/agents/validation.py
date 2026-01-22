"""
Validation agents for query and response validation.
Validates user queries and AI responses for security threats, prompt injection,
and quality issues.
"""
import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation result status."""
    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    status: ValidationStatus
    message: str
    issues: List[str]
    severity_score: float  # 0.0 (safe) to 1.0 (critical)
    details: Dict[str, Any]


class BaseValidator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    async def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate the given text.

        Args:
            text: Text to validate
            context: Optional context information

        Returns:
            ValidationResult with status and details
        """
        pass


class QueryValidator(BaseValidator):
    """
    Validates user queries for suspicious prompts, prompt injection attempts,
    jailbreak attempts, and malicious content.
    """

    def __init__(self):
        # Patterns for detecting suspicious content
        self.jailbreak_patterns = [
            r'ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)',
            r'disregard\s+(previous|above|all)\s+(instructions?|prompts?)',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now\s+(a|an)\s+\w+',
            r'act\s+as\s+(if\s+)?(you\s+are|a|an)\s+\w+',
            r'pretend\s+(you\s+are|to\s+be)',
            r'roleplay\s+as',
            r'new\s+instructions?:',
            r'system\s+prompt\s*:',
            r'ignore\s+your\s+programming',
            r'bypass\s+(safety|security|filters?)',
            r'sudo\s+mode',
            r'developer\s+mode',
            r'god\s+mode',
        ]

        self.prompt_injection_patterns = [
            r'\[SYSTEM\]|\[INST\]|\[/INST\]',
            r'<\|im_start\|>|<\|im_end\|>',
            r'###\s*Instruction:',
            r'###\s*System:',
            r'</s>|<s>',
            r'\*\*\*ADMIN\*\*\*',
            r'<prompt>|</prompt>',
        ]

        self.malicious_intent_keywords = [
            'hack', 'exploit', 'vulnerability', 'bypass', 'crack',
            'phishing', 'malware', 'ransomware', 'ddos',
            'sql injection', 'xss', 'csrf',
        ]

        self.sensitive_info_requests = [
            r'api\s+key',
            r'secret\s+key',
            r'password',
            r'private\s+key',
            r'access\s+token',
            r'credentials?',
            r'connection\s+string',
            r'database\s+password',
        ]

    async def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate user query for suspicious content.

        Args:
            text: User query to validate
            context: Optional context (user_id, session_id, etc.)

        Returns:
            ValidationResult
        """
        issues = []
        severity_score = 0.0
        details = {
            "jailbreak_detected": False,
            "prompt_injection_detected": False,
            "malicious_intent_detected": False,
            "sensitive_info_requested": False,
            "excessive_length": False,
        }

        # Check 1: Jailbreak attempts
        jailbreak_matches = self._check_patterns(
            text.lower(), self.jailbreak_patterns)
        if jailbreak_matches:
            issues.append(
                f"Potential jailbreak attempt detected: {', '.join(jailbreak_matches[:3])}")
            details["jailbreak_detected"] = True
            severity_score = max(severity_score, 0.9)

        # Check 2: Prompt injection
        injection_matches = self._check_patterns(
            text, self.prompt_injection_patterns)
        if injection_matches:
            issues.append(
                f"Potential prompt injection detected: {', '.join(injection_matches[:3])}")
            details["prompt_injection_detected"] = True
            severity_score = max(severity_score, 0.95)

        # Check 3: Malicious intent
        malicious_found = [
            kw for kw in self.malicious_intent_keywords if kw in text.lower()]
        if malicious_found:
            # Context matters - not all mentions are malicious
            if self._is_likely_malicious(text, malicious_found):
                issues.append(
                    f"Potential malicious intent: {', '.join(malicious_found[:3])}")
                details["malicious_intent_detected"] = True
                severity_score = max(severity_score, 0.7)

        # Check 4: Requesting sensitive information
        sensitive_matches = self._check_patterns(
            text.lower(), self.sensitive_info_requests)
        if sensitive_matches:
            issues.append(
                f"Request for sensitive information: {', '.join(sensitive_matches[:3])}")
            details["sensitive_info_requested"] = True
            severity_score = max(severity_score, 0.8)

        # Check 5: Excessive length (possible DoS attempt)
        if len(text) > 10000:
            issues.append(f"Excessive query length: {len(text)} characters")
            details["excessive_length"] = True
            severity_score = max(severity_score, 0.6)

        # Check 6: Repeated patterns (possible attack)
        if self._has_suspicious_repetition(text):
            issues.append("Suspicious repetitive patterns detected")
            severity_score = max(severity_score, 0.5)

        # Determine status based on severity
        if severity_score >= 0.8:
            status = ValidationStatus.BLOCKED
            message = "Query blocked due to security concerns"
        elif severity_score >= 0.4:
            status = ValidationStatus.WARNING
            message = "Query contains potentially suspicious content"
        else:
            status = ValidationStatus.SAFE
            message = "Query passed validation"

        return ValidationResult(
            status=status,
            message=message,
            issues=issues,
            severity_score=severity_score,
            details=details
        )

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check text against a list of regex patterns."""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _is_likely_malicious(self, text: str, keywords: List[str]) -> bool:
        """Determine if malicious keywords are used in a harmful context."""
        # Educational or informational queries are generally safe
        educational_indicators = [
            'what is', 'how does', 'explain', 'learn', 'understand',
            'protect against', 'prevent', 'defend', 'secure'
        ]

        text_lower = text.lower()

        # If educational context, likely safe
        if any(ind in text_lower for ind in educational_indicators):
            return False

        # If asking how to perform attack, likely malicious
        malicious_indicators = [
            'how to', 'teach me', 'show me', 'help me',
            'can you', 'write code to', 'create a'
        ]

        if any(ind in text_lower for ind in malicious_indicators):
            return True

        # Multiple malicious keywords = likely malicious
        return len(keywords) >= 2

    def _has_suspicious_repetition(self, text: str) -> bool:
        """Check for suspicious repetitive patterns."""
        # Check for same phrase repeated many times
        words = text.split()
        if len(words) < 10:
            return False

        # Count repeated sequences
        sequences = {}
        for i in range(len(words) - 3):
            seq = ' '.join(words[i:i+4])
            sequences[seq] = sequences.get(seq, 0) + 1

        # If any sequence appears more than 5 times, suspicious
        return any(count > 5 for count in sequences.values())


class ResponseValidator(BaseValidator):
    """
    Validates AI-generated responses for quality, accuracy, private information leakage,
    and potential harmful content.
    """

    def __init__(self):
        # Patterns for detecting private/sensitive information
        self.private_info_patterns = [
            r'api[_-]?key[:\s]+[\w\-]{20,}',
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI API key pattern
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub token
            r'AWS[A-Z0-9]{16,}',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'password[:\s]+\S+',
            r'token[:\s]+[\w\-]{20,}',
            r'/home/[\w/]+',  # File paths
            r'C:\\[\w\\]+',
            r'mongodb://[\w:@/]+',  # Connection strings
            r'postgresql://[\w:@/]+',
        ]

        self.system_info_patterns = [
            r'model\s+architecture',
            r'training\s+data',
            r'system\s+prompt',
            r'internal\s+configuration',
            r'server\s+details',
            r'backend\s+implementation',
        ]

        self.harmful_content_keywords = [
            'illegal', 'violence', 'harm', 'kill', 'suicide',
            'terrorist', 'bomb', 'weapon', 'drug',
        ]

    async def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate AI response for quality and safety.

        Args:
            text: AI-generated response to validate
            context: Optional context (query, user_id, etc.)

        Returns:
            ValidationResult
        """
        issues = []
        severity_score = 0.0
        details = {
            "private_info_leaked": False,
            "system_info_leaked": False,
            "low_quality": False,
            "potentially_harmful": False,
            "incomplete_response": False,
            "hallucination_risk": False,
        }

        # Check 1: Private information leakage
        private_matches = self._check_patterns(
            text, self.private_info_patterns)
        if private_matches:
            issues.append(
                f"Potential private information leak detected: {len(private_matches)} matches")
            details["private_info_leaked"] = True
            severity_score = max(severity_score, 0.95)

        # Check 2: System information disclosure
        system_matches = self._check_patterns(
            text.lower(), self.system_info_patterns)
        if system_matches:
            issues.append(
                f"Potential system information disclosure: {', '.join(system_matches[:2])}")
            details["system_info_leaked"] = True
            severity_score = max(severity_score, 0.7)

        # Check 3: Response quality
        quality_issues = self._check_quality(text)
        if quality_issues:
            issues.extend(quality_issues)
            details["low_quality"] = True
            severity_score = max(severity_score, 0.5)

        # Check 4: Potentially harmful content
        harmful_found = [
            kw for kw in self.harmful_content_keywords if kw in text.lower()]
        if harmful_found:
            # Check context - educational content is okay
            if not self._is_educational_context(text):
                issues.append(
                    f"Potentially harmful content: {', '.join(harmful_found[:3])}")
                details["potentially_harmful"] = True
                severity_score = max(severity_score, 0.8)

        # Check 5: Hallucination indicators
        if self._has_hallucination_indicators(text):
            issues.append("Response may contain unsupported claims")
            details["hallucination_risk"] = True
            severity_score = max(severity_score, 0.4)

        # Check 6: Incomplete response
        if self._is_incomplete(text):
            issues.append("Response appears incomplete or cut off")
            details["incomplete_response"] = True
            severity_score = max(severity_score, 0.3)

        # Determine status
        if severity_score >= 0.8:
            status = ValidationStatus.BLOCKED
            message = "Response blocked due to safety/privacy concerns"
        elif severity_score >= 0.4:
            status = ValidationStatus.WARNING
            message = "Response has quality or safety concerns"
        else:
            status = ValidationStatus.SAFE
            message = "Response passed validation"

        return ValidationResult(
            status=status,
            message=message,
            issues=issues,
            severity_score=severity_score,
            details=details
        )

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check text against a list of regex patterns."""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _check_quality(self, text: str) -> List[str]:
        """Check response quality."""
        issues = []

        # Too short
        if len(text.strip()) < 10:
            issues.append("Response too short")

        # Excessive repetition
        words = text.split()
        if len(words) > 20:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                issues.append("Excessive repetition detected")

        # No punctuation (might indicate truncation or poor quality)
        if len(text) > 100 and not any(p in text for p in '.!?'):
            issues.append("Missing punctuation - possible quality issue")

        return issues

    def _is_educational_context(self, text: str) -> bool:
        """Check if harmful keywords are used in educational context."""
        educational_phrases = [
            'for educational purposes',
            'to understand',
            'to learn',
            'it is important to note',
            'however',
            'instead',
            'do not',
            "don't",
            'avoid',
            'prevent',
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in educational_phrases)

    def _has_hallucination_indicators(self, text: str) -> bool:
        """Check for indicators of potential hallucination."""
        # Overly confident claims without qualification
        absolute_claims = [
            'definitely', 'absolutely', 'certainly', 'guaranteed',
            'always works', 'never fails', '100% accurate'
        ]

        text_lower = text.lower()

        # Count absolute claims
        claim_count = sum(
            1 for claim in absolute_claims if claim in text_lower)

        # High confidence with no hedging is risky
        hedging_phrases = [
            'may', 'might', 'could', 'possibly', 'likely',
            'in some cases', 'generally', 'typically'
        ]

        has_hedging = any(hedge in text_lower for hedge in hedging_phrases)

        # Multiple absolute claims without hedging = hallucination risk
        return claim_count >= 2 and not has_hedging

    def _is_incomplete(self, text: str) -> bool:
        """Check if response appears incomplete."""
        text = text.strip()

        # Ends with incomplete sentence indicators
        incomplete_endings = ['...', 'and', 'but', 'or', 'because', ',']

        for ending in incomplete_endings:
            if text.endswith(ending):
                return True

        # Very short response
        if len(text) < 20:
            return True

        return False


class ValidationAgent:
    """
    Main agent that coordinates query and response validation.
    """

    def __init__(self):
        self.query_validator = QueryValidator()
        self.response_validator = ResponseValidator()
        self.validation_log: List[Dict[str, Any]] = []

    async def validate_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate user query before processing.

        Args:
            query: User's input query
            context: Optional context information

        Returns:
            ValidationResult
        """
        result = await self.query_validator.validate(query, context)

        # Log validation
        self._log_validation("query", query, result, context)

        return result

    async def validate_response(
        self,
        response: str,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate AI-generated response before sending to user.

        Args:
            response: AI-generated response
            query: Original user query (for context)
            context: Optional context information

        Returns:
            ValidationResult
        """
        validation_context = context or {}
        if query:
            validation_context["original_query"] = query

        result = await self.response_validator.validate(response, validation_context)

        # Log validation
        self._log_validation("response", response, result, validation_context)

        return result

    async def validate_full_interaction(
        self,
        query: str,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ValidationResult, ValidationResult]:
        """
        Validate both query and response.

        Args:
            query: User query
            response: AI response
            context: Optional context

        Returns:
            Tuple of (query_result, response_result)
        """
        query_result = await self.validate_query(query, context)
        response_result = await self.validate_response(response, query, context)

        return query_result, response_result

    def _log_validation(
        self,
        validation_type: str,
        text: str,
        result: ValidationResult,
        context: Optional[Dict[str, Any]]
    ):
        """Log validation for auditing."""
        try:
            loop = asyncio.get_event_loop()
            timestamp = loop.time()
        except RuntimeError:
            import time
            timestamp = time.time()

        log_entry = {
            "type": validation_type,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "status": result.status.value,
            "severity": result.severity_score,
            "issues": result.issues,
            "context": context,
            "timestamp": timestamp
        }

        self.validation_log.append(log_entry)

        # Also log to application logger
        if result.status == ValidationStatus.BLOCKED:
            logger.warning(
                f"[VALIDATION_BLOCKED] {validation_type} - "
                f"status: {result.status.value}, severity: {result.severity_score:.2f}, "
                f"issues: {result.issues}, context: {context}"
            )
        elif result.status == ValidationStatus.WARNING:
            logger.info(
                f"[VALIDATION_WARNING] {validation_type} - "
                f"severity: {result.severity_score:.2f}, issues: {result.issues}"
            )

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = len(self.validation_log)
        if total == 0:
            return {"total_validations": 0}

        blocked = sum(
            1 for log in self.validation_log if log["status"] == "blocked")
        warnings = sum(
            1 for log in self.validation_log if log["status"] == "warning")
        safe = sum(1 for log in self.validation_log if log["status"] == "safe")

        query_validations = sum(
            1 for log in self.validation_log if log["type"] == "query")
        response_validations = sum(
            1 for log in self.validation_log if log["type"] == "response")

        return {
            "total_validations": total,
            "blocked": blocked,
            "warnings": warnings,
            "safe": safe,
            "query_validations": query_validations,
            "response_validations": response_validations,
            "block_rate": f"{(blocked/total)*100:.2f}%" if total > 0 else "0.00%",
            "warning_rate": f"{(warnings/total)*100:.2f}%" if total > 0 else "0.00%"
        }
