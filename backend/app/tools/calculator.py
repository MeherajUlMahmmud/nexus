import logging
import math
import re
from typing import Any, Dict

from app.tools import BaseTool

logger = logging.getLogger(__name__)


class CalculatorTool(BaseTool):
    """Performs mathematical calculations and evaluates expressions."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates mathematical expressions safely. Supports basic arithmetic (+, -, *, /, ^ for exponentiation), trigonometry (sin, cos, tan), logarithms (log, ln), square root (sqrt), and constants (pi, e). Use ^ for exponentiation (e.g., 2^3 = 8)."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '2^3', 'sqrt(16)', 'sin(pi/2)')"
                }
            },
            "required": ["expression"]
        }

    async def execute(self, expression: str) -> str:
        import time
        start_time = time.time()
        logger.info(f"[CALCULATOR_TOOL] Execution started - expression: {expression}")

        try:
            # Safe math namespace
            safe_dict = {
                'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'sqrt': math.sqrt, 'log': math.log10, 'ln': math.log,
                'pi': math.pi, 'e': math.e, 'abs': abs,
                'pow': pow, 'round': round
            }

            # Clean and validate expression
            expr = expression.strip()
            logger.debug(f"[CALCULATOR_TOOL] Original expression: {expr}")

            # Validate expression before conversion (allow ^ in original)
            # Allow: numbers, +, -, *, /, ^, (, ), ., space, letters (for functions)
            if not re.match(r'^[0-9+\-*/^()., a-z]+$', expr, re.IGNORECASE):
                logger.warning(f"[CALCULATOR_TOOL] Invalid characters in expression: {expression}")
                return f"Error: Invalid characters in expression. Only numbers, operators (+, -, *, /, ^), parentheses, and math functions are allowed."

            # Convert ^ to ** (Python's exponentiation operator)
            # Replace ^ with **, handling cases like 2^3, (-2)^3, etc.
            expr = re.sub(r'\^', '**', expr)
            logger.debug(f"[CALCULATOR_TOOL] Converted expression: {expr}")

            # Evaluate the expression
            result = eval(expr, {"__builtins__": {}}, safe_dict)

            execution_time = time.time() - start_time
            logger.info(f"[CALCULATOR_TOOL] Execution completed successfully in {execution_time:.2f}s - "
                        f"expression: {expression}, result: {result}")

            return f"Result: {result}"
        except ZeroDivisionError:
            execution_time = time.time() - start_time
            logger.warning(
                f"[CALCULATOR_TOOL] Division by zero - expression: {expression}, time: {execution_time:.2f}s")
            return "Error: Division by zero is not allowed"
        except SyntaxError as e:
            execution_time = time.time() - start_time
            logger.warning(
                f"[CALCULATOR_TOOL] Syntax error - expression: {expression}, error: {str(e)}, time: {execution_time:.2f}s")
            return f"Error: Invalid expression syntax. {str(e)}"
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[CALCULATOR_TOOL] Error calculating expression: {expression}, error: {str(e)}, time: {execution_time:.2f}s",
                exc_info=True)
            return f"Error calculating expression: {str(e)}"
