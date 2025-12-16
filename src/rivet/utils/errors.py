import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categorize errors for targeted fixes"""

    SDK_SYNTAX = "sdk_syntax"  # SyntaxError, IndentationError
    SDK_IMPORT = "sdk_import"  # ImportError, ModuleNotFoundError
    SDK_STRUCTURE = "sdk_structure"  # NameError, AttributeError in SDK
    SDK_LOGIC = "sdk_logic"  # Wrong return types, logic errors
    TEST_MOCK = "test_mock"  # Mock setup issues
    TEST_DATA = "test_data"  # Wrong test data structure
    TEST_ASSERTION = "test_assertion"  # Failed assertions
    TEST_LOGIC = "test_logic"  # Test implementation bugs
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """Structured error information"""

    category: ErrorCategory
    error_type: str  # e.g., "SyntaxError", "AssertionError"
    error_message: str  # The actual error text
    file_path: Optional[str]  # Where error occurred
    line_number: Optional[int]
    traceback: str  # Full traceback for context
    is_sdk_error: bool  # True = fix SDK, False = fix tests
    severity: str  # "critical", "high", "medium", "low"
    suggested_action: str  # Human-readable fix suggestion


class ErrorAnalyzer:
    """Comprehensive error analysis for SDK generation"""

    # Critical errors that prevent code from parsing/loading
    SDK_FATAL_PATTERNS = {
        r"SyntaxError": ErrorCategory.SDK_SYNTAX,
        r"IndentationError": ErrorCategory.SDK_SYNTAX,
        r"TabError": ErrorCategory.SDK_SYNTAX,
        r"ModuleNotFoundError": ErrorCategory.SDK_IMPORT,
        r"ImportError": ErrorCategory.SDK_IMPORT,
    }

    # Runtime errors that indicate structural problems
    SDK_STRUCTURE_PATTERNS = {
        r"NameError": ErrorCategory.SDK_STRUCTURE,
        r"UnboundLocalError": ErrorCategory.SDK_STRUCTURE,
    }

    # Context-dependent errors (need file location to categorize)
    CONTEXT_PATTERNS = {
        r"AttributeError": None,  # Could be SDK or test
        r"TypeError": None,
        r"ValueError": None,
        r"KeyError": None,
    }

    # Test-specific patterns
    TEST_PATTERNS = {
        r"AssertionError": ErrorCategory.TEST_ASSERTION,
        r"MockError": ErrorCategory.TEST_MOCK,
        r"pytest\.fail": ErrorCategory.TEST_ASSERTION,
    }

    @staticmethod
    def analyze(logs: Optional[str]) -> Optional[ErrorAnalysis]:
        """
        Analyze error logs and return structured error information.
        Returns None if no errors found.
        """
        if not logs or not logs.strip():
            return None

        # Extract error type and message
        error_match = re.search(r"(\w+Error|AssertionError):\s*(.+?)(?:\n|$)", logs)
        if not error_match:
            return ErrorAnalyzer._handle_unknown_error(logs)

        error_type = error_match.group(1)
        error_message = error_match.group(2).strip()

        # Extract file and line info
        file_match = re.search(r'File "([^"]+)",\s*line\s*(\d+)', logs)
        file_path = file_match.group(1) if file_match else None
        line_number = int(file_match.group(2)) if file_match else None

        # Determine category
        category = ErrorAnalyzer._categorize_error(error_type, error_message, file_path, logs)

        # Determine if it's SDK or test error
        is_sdk_error = category.value.startswith("sdk_")

        # Determine severity
        severity = ErrorAnalyzer._determine_severity(category)

        # Generate action suggestion
        suggested_action = ErrorAnalyzer._suggest_action(
            category, error_type, error_message, file_path
        )

        return ErrorAnalysis(
            category=category,
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            traceback=logs,
            is_sdk_error=is_sdk_error,
            severity=severity,
            suggested_action=suggested_action,
        )

    @staticmethod
    def _categorize_error(
        error_type: str, error_message: str, file_path: Optional[str], full_logs: str
    ) -> ErrorCategory:
        """Determine error category using multiple signals"""

        # 1. Check fatal SDK errors first
        for pattern, category in ErrorAnalyzer.SDK_FATAL_PATTERNS.items():
            if re.search(pattern, error_type):
                return category

        # 2. Check test-specific patterns
        for pattern, category in ErrorAnalyzer.TEST_PATTERNS.items():
            if re.search(pattern, error_type) or re.search(pattern, error_message):
                return category

        # 3. Check SDK structure errors (must be in client.py)
        for pattern, category in ErrorAnalyzer.SDK_STRUCTURE_PATTERNS.items():
            if re.search(pattern, error_type):
                if file_path and "client.py" in file_path:
                    return category
                # If NameError in test, it's a test bug
                return ErrorCategory.TEST_LOGIC

        # 4. Handle context-dependent errors
        if error_type in ["AttributeError", "TypeError", "ValueError", "KeyError"]:
            return ErrorAnalyzer._categorize_context_error(
                error_type, error_message, file_path, full_logs
            )

        return ErrorCategory.UNKNOWN

    @staticmethod
    def _categorize_context_error(
        error_type: str, error_message: str, file_path: Optional[str], full_logs: str
    ) -> ErrorCategory:
        """Handle errors that need context to categorize"""

        # AttributeError patterns
        if error_type == "AttributeError":
            # "NoneType has no attribute 'json'" - likely SDK didn't return response
            if "NoneType" in error_message and any(
                attr in error_message for attr in ["json", "status_code", "text"]
            ):
                if file_path and "client.py" in file_path:
                    return ErrorCategory.SDK_LOGIC

            # Accessing wrong attribute on object - check file
            if file_path and "client.py" in file_path:
                return ErrorCategory.SDK_STRUCTURE
            return ErrorCategory.TEST_LOGIC

        # TypeError patterns
        if error_type == "TypeError":
            # "object async_generator can't be used in 'await' expression"
            if "coroutine" in error_message or "async" in error_message:
                if file_path and "test_client.py" in file_path:
                    return ErrorCategory.TEST_MOCK
                return ErrorCategory.SDK_LOGIC

            # Type mismatches in SDK
            if file_path and "client.py" in file_path:
                return ErrorCategory.SDK_LOGIC
            return ErrorCategory.TEST_DATA

        # ValueError patterns
        if error_type == "ValueError":
            # "invalid literal for int()" - bad test data
            if "invalid literal" in error_message:
                return ErrorCategory.TEST_DATA
            return ErrorCategory.TEST_LOGIC

        # KeyError patterns
        if error_type == "KeyError":
            # Missing key in response - could be SDK or test
            # If in client.py, SDK didn't handle missing keys
            if file_path and "client.py" in file_path:
                return ErrorCategory.SDK_LOGIC
            # If in test, wrong mock data structure
            return ErrorCategory.TEST_DATA

        return ErrorCategory.UNKNOWN

    @staticmethod
    def _determine_severity(category: ErrorCategory) -> str:
        """Determine how critical the error is"""
        critical = [ErrorCategory.SDK_SYNTAX, ErrorCategory.SDK_IMPORT]
        high = [ErrorCategory.SDK_STRUCTURE, ErrorCategory.SDK_LOGIC]
        medium = [ErrorCategory.TEST_MOCK, ErrorCategory.TEST_DATA]
        low = [ErrorCategory.TEST_ASSERTION, ErrorCategory.TEST_LOGIC]

        if category in critical:
            return "critical"
        elif category in high:
            return "high"
        elif category in medium:
            return "medium"
        elif category in low:
            return "low"
        return "unknown"

    @staticmethod
    def _suggest_action(
        category: ErrorCategory, error_type: str, error_message: str, file_path: Optional[str]
    ) -> str:
        """Generate human-readable fix suggestion"""
        suggestions = {
            ErrorCategory.SDK_SYNTAX: f"Fix syntax error in {file_path}: {error_message}",
            ErrorCategory.SDK_IMPORT: f"Fix import issue: {error_message}. Check dependencies.",
            ErrorCategory.SDK_STRUCTURE: f"Fix undefined variable/attribute in SDK: {error_message}",
            ErrorCategory.SDK_LOGIC: f"Fix SDK logic error in {file_path}: {error_message}",
            ErrorCategory.TEST_MOCK: f"Fix mock setup in test: {error_message}",
            ErrorCategory.TEST_DATA: f"Fix test data structure: {error_message}",
            ErrorCategory.TEST_ASSERTION: f"Fix test assertion: {error_message}",
            ErrorCategory.TEST_LOGIC: f"Fix test implementation: {error_message}",
        }
        return suggestions.get(category, f"Investigate {error_type}: {error_message}")

    @staticmethod
    def _handle_unknown_error(logs: str) -> ErrorAnalysis:
        """Handle logs that don't match expected patterns"""
        return ErrorAnalysis(
            category=ErrorCategory.UNKNOWN,
            error_type="Unknown",
            error_message="Could not parse error from logs",
            file_path=None,
            line_number=None,
            traceback=logs,
            is_sdk_error=True,  # Default to SDK to be safe
            severity="high",
            suggested_action="Manual investigation required. Check full logs.",
        )


def get_error_analysis(logs: Optional[str] = None) -> Optional[ErrorAnalysis]:
    """
    Recommended: Use this instead of filter_errors() for structured error info.
    """
    return ErrorAnalyzer.analyze(logs)
