"""
Math Agent — Detect, convert to LaTeX, and solve mathematical expressions.
Uses SymPy for algebraic solving and latex2sympy2 for LaTeX parsing.
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger


class MathAgent:
    """
    Handles mathematical content:
    1. Detect if text contains math
    2. Convert to LaTeX notation
    3. Solve equations using SymPy
    4. Format step-by-step solutions
    """

    MATH_PATTERNS = [
        r"\d+\s*[\+\-\*\/\^]\s*\d+",     # Basic arithmetic
        r"[a-zA-Z]\s*=\s*[-\d]",           # Variable assignment
        r"(?:sin|cos|tan|log|ln|sqrt)\s*\(", # Functions
        r"\d+x\^?\d*",                     # Polynomials
        r"∫|∂|∑|∏|√|∞|≠|≤|≥",            # Math symbols
        r"\b(?:solve|equation|integral|derivative|matrix)\b",  # Keywords
    ]

    def is_math_content(self, text: str) -> bool:
        """Check if text contains mathematical expressions."""
        for pattern in self.MATH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def text_to_latex(self, text: str) -> str | None:
        """Convert plain text math expression to LaTeX notation."""
        try:
            # Simple rule-based conversions
            latex = text
            latex = re.sub(r"\bsqrt\((.+?)\)", r"\\sqrt{\1}", latex)
            latex = re.sub(r"\bsin\((.+?)\)", r"\\sin(\1)", latex)
            latex = re.sub(r"\bcos\((.+?)\)", r"\\cos(\1)", latex)
            latex = re.sub(r"\btan\((.+?)\)", r"\\tan(\1)", latex)
            latex = re.sub(r"\blog\((.+?)\)", r"\\log(\1)", latex)
            latex = re.sub(r"\bln\((.+?)\)", r"\\ln(\1)", latex)
            latex = re.sub(r"\^(\d+)", r"^{\1}", latex)
            latex = re.sub(r"(\d+)/(\d+)", r"\\frac{\1}{\2}", latex)
            latex = re.sub(r"<=", r"\\leq", latex)
            latex = re.sub(r">=", r"\\geq", latex)
            latex = re.sub(r"!=", r"\\neq", latex)
            latex = re.sub(r"\*", r"\\cdot", latex)
            latex = re.sub(r"infinity|inf", r"\\infty", latex, flags=re.IGNORECASE)
            return f"$${latex}$$"
        except Exception as e:
            logger.warning(f"[MathAgent] text_to_latex failed: {e}")
            return None

    def solve_equation(self, expression: str) -> dict[str, Any]:
        """
        Solve a mathematical expression using SymPy.
        Returns solution, steps, and formatted LaTeX.
        """
        try:
            import sympy as sp
            from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

            transformations = standard_transformations + (implicit_multiplication_application,)

            result: dict[str, Any] = {
                "expression": expression,
                "solution": None,
                "steps": [],
                "latex": None,
                "error": None,
            }

            # Try to solve as an equation (contains =)
            if "=" in expression:
                parts = expression.split("=", 1)
                lhs = parse_expr(parts[0].strip(), transformations=transformations)
                rhs = parse_expr(parts[1].strip(), transformations=transformations)
                equation = sp.Eq(lhs, rhs)

                symbols_found = list(equation.free_symbols)
                if symbols_found:
                    var = symbols_found[0]
                    solutions = sp.solve(equation, var)
                    result["solution"] = str(solutions)
                    result["latex"] = f"$${sp.latex(equation)}$$"
                    result["steps"] = self._generate_solve_steps(equation, var, solutions)
            else:
                # Evaluate/simplify expression
                expr = parse_expr(expression, transformations=transformations)
                simplified = sp.simplify(expr)
                result["solution"] = str(simplified)
                result["latex"] = f"$${sp.latex(simplified)}$$"
                result["steps"] = [
                    f"Original expression: {expression}",
                    f"Simplified: {sp.latex(simplified)}",
                ]

            logger.info(f"[MathAgent] Solved: {expression} → {result['solution']}")
            return result

        except Exception as e:
            logger.error(f"[MathAgent] solve_equation failed: {e}")
            return {
                "expression": expression,
                "solution": None,
                "steps": [],
                "latex": None,
                "error": str(e),
            }

    def _generate_solve_steps(self, equation, variable, solutions) -> list[str]:
        """Generate human-readable solution steps."""
        import sympy as sp
        steps = [
            f"Given equation: {sp.latex(equation)}",
            f"Solving for: {variable}",
        ]
        for i, sol in enumerate(solutions):
            steps.append(f"Solution {i+1}: {variable} = {sol} = {sp.latex(sol)}")
        return steps

    def classify_question_type(self, text: str) -> str:
        """Classify question domain from text content."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["integral", "derivative", "differentiate", "dx", "dy"]):
            return "calculus"
        if any(w in text_lower for w in ["matrix", "vector", "determinant", "eigenvalue"]):
            return "linear_algebra"
        if any(w in text_lower for w in ["sin", "cos", "tan", "angle", "triangle", "hypotenuse"]):
            return "trigonometry"
        if any(w in text_lower for w in ["probability", "combination", "permutation", "binomial"]):
            return "statistics"
        if any(w in text_lower for w in ["velocity", "acceleration", "force", "newton", "momentum"]):
            return "physics"
        if any(w in text_lower for w in ["element", "compound", "reaction", "mole", "valence"]):
            return "chemistry"
        if any(w in text_lower for w in ["=", "+", "-", "*", "/", "solve", "equation", "factor"]):
            return "math"
        return "general"
