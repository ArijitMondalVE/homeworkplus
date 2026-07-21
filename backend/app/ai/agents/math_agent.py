"""
Math Agent — Advanced symbolic math solver.
Handles: arithmetic, algebra, calculus, logs, integrals, derivatives,
         probability, matrices, linear algebra, series, and more.
Uses SymPy for exact symbolic computation.
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger


class MathAgent:
    """
    Advanced math solver covering:
    - Arithmetic & algebra
    - Calculus: derivatives, integrals, limits
    - Logarithms & exponentials
    - Trigonometry
    - Probability & statistics
    - Matrices & linear algebra
    - Series & sequences
    - Number theory
    - Differential equations
    """

    MATH_PATTERNS = [
        r"\d+\s*[\+\-\*\/\^]\s*\d+",                         # Basic arithmetic
        r"\d+\s*[÷×]\s*\d+",                                  # ÷ × symbols
        r"\d+\s*/\s*\d+",                                     # Fractions
        r"[a-zA-Z]\s*=\s*[-\d]",                              # Variable assignment
        r"(?:sin|cos|tan|sec|csc|cot|log|ln|exp|sqrt)\s*\(", # Functions
        r"\d+[a-zA-Z]\^?\d*",                                 # Polynomials
        r"∫|∂|∑|∏|√|∞|≠|≤|≥|÷|×|→|∈|∉|⊂|∩|∪",             # Unicode math
        r"\b(?:solve|equation|integral|derivative|differentiat|matrix|determinant|"
        r"eigenvalue|probability|factorial|permutation|combination|limit|series|"
        r"sequence|vector|gradient|divergence|curl|laplace|fourier)\b",
        r"d[yf]/d[xt]",                                       # Derivative notation
        r"lim\s*[_\(]",                                       # Limit notation
        r"P\s*\(\s*[A-Z]",                                    # Probability P(A)
        r"\bC\s*\(\s*\d",                                     # Combination C(n,r)
        r"\bP\s*\(\s*\d",                                     # Permutation P(n,r)
        r"\bnCr\b|\bnPr\b|\bbinom\b",                         # nCr, nPr
    ]

    # ── Detection ─────────────────────────────────────────────────────────────

    def is_math_content(self, text: str) -> bool:
        """Check if text contains mathematical expressions."""
        for pattern in self.MATH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def classify_question_type(self, text: str) -> str:
        """Classify question domain from text content."""
        t = text.lower()
        if any(w in t for w in ["∫", "integral", "integrate", "antiderivative", "∫dx"]):
            return "calculus_integration"
        if any(w in t for w in ["d/dx", "derivative", "differentiat", "dy/dx", "f'", "df/dx", "∂"]):
            return "calculus_differentiation"
        if any(w in t for w in ["lim", "limit", "→", "approaches"]):
            return "calculus_limits"
        if any(w in t for w in ["log", "ln", "logarithm", "log₂", "log₁₀"]):
            return "logarithms"
        if any(w in t for w in ["sin", "cos", "tan", "sec", "csc", "cot", "angle", "triangle", "hypotenuse", "radian", "degree"]):
            return "trigonometry"
        if any(w in t for w in ["probability", "p(", "combination", "permutation", "binomial", "bayes", "ncr", "npr", "factorial", "!"]):
            return "probability"
        if any(w in t for w in ["matrix", "matrices", "determinant", "eigenvalue", "eigenvector", "transpose", "inverse matrix"]):
            return "linear_algebra"
        if any(w in t for w in ["vector", "dot product", "cross product", "magnitude", "gradient"]):
            return "vectors"
        if any(w in t for w in ["series", "sequence", "sigma", "∑", "geometric", "arithmetic progression", "ap ", "gp "]):
            return "series"
        if any(w in t for w in ["differential equation", "ode", "pde", "d²y", "d2y/dx2"]):
            return "differential_equations"
        if any(w in t for w in ["prime", "factor", "gcd", "lcm", "modulo", "mod ", "divisib"]):
            return "number_theory"
        if any(w in t for w in ["velocity", "acceleration", "force", "newton", "momentum", "energy"]):
            return "physics_math"
        if any(w in t for w in ["=", "+", "-", "*", "/", "÷", "×", "solve", "equation", "simplify", "expand", "factor"]):
            return "math"
        return "general"

    # ── LaTeX Conversion ──────────────────────────────────────────────────────

    def text_to_latex(self, text: str) -> str | None:
        """Convert plain text math expression to LaTeX notation."""
        try:
            latex = text
            # Trig functions
            for fn in ["sin", "cos", "tan", "sec", "csc", "cot", "arcsin", "arccos", "arctan"]:
                latex = re.sub(rf"\b{fn}\((.+?)\)", rf"\\{fn}(\\1)", latex)
            # Calculus functions
            latex = re.sub(r"\bsqrt\((.+?)\)", r"\\sqrt{\1}", latex)
            latex = re.sub(r"\bln\((.+?)\)", r"\\ln(\1)", latex)
            latex = re.sub(r"\blog\((.+?)\)", r"\\log(\1)", latex)
            latex = re.sub(r"\blog_(\d+)\((.+?)\)", r"\\log_{\1}(\2)", latex)
            latex = re.sub(r"\bexp\((.+?)\)", r"e^{\1}", latex)
            # Exponents
            latex = re.sub(r"\^(\d+)", r"^{\1}", latex)
            latex = re.sub(r"\^(\([^)]+\))", r"^{\1}", latex)
            # Fractions
            latex = re.sub(r"(\d+)/(\d+)", r"\\frac{\1}{\2}", latex)
            # Integrals
            latex = re.sub(r"\bint\b", r"\\int", latex)
            latex = re.sub(r"∫", r"\\int ", latex)
            # Derivatives
            latex = re.sub(r"\bd/dx\b", r"\\frac{d}{dx}", latex)
            latex = re.sub(r"\bdy/dx\b", r"\\frac{dy}{dx}", latex)
            # Symbols
            latex = re.sub(r"\*", r"\\cdot ", latex)
            latex = re.sub(r"÷", r"\\div ", latex)
            latex = re.sub(r"×", r"\\times ", latex)
            latex = re.sub(r"<=", r"\\leq ", latex)
            latex = re.sub(r">=", r"\\geq ", latex)
            latex = re.sub(r"!=", r"\\neq ", latex)
            latex = re.sub(r"\binfinity\b|\binf\b", r"\\infty", latex, flags=re.IGNORECASE)
            latex = re.sub(r"∞", r"\\infty", latex)
            latex = re.sub(r"∑", r"\\sum", latex)
            latex = re.sub(r"∏", r"\\prod", latex)
            latex = re.sub(r"∂", r"\\partial", latex)
            # Limits
            latex = re.sub(r"\blim\b", r"\\lim", latex)
            latex = re.sub(r"->", r"\\to", latex)
            return f"$${latex}$$"
        except Exception as e:
            logger.warning(f"[MathAgent] text_to_latex failed: {e}")
            return None

    # ── Main Solver ───────────────────────────────────────────────────────────

    def solve_equation(self, expression: str) -> dict[str, Any]:
        """
        Route expression to the appropriate solver.
        Handles: equations, integrals, derivatives, limits, matrices,
                 probability, series, and general arithmetic.
        """
        expr_clean = expression.strip()
        q_type = self.classify_question_type(expr_clean)
        logger.info(f"[MathAgent] Solving ({q_type}): {expr_clean[:80]}")

        try:
            if q_type == "calculus_integration":
                return self._solve_integral(expr_clean)
            elif q_type == "calculus_differentiation":
                return self._solve_derivative(expr_clean)
            elif q_type == "calculus_limits":
                return self._solve_limit(expr_clean)
            elif q_type == "logarithms":
                return self._solve_logarithm(expr_clean)
            elif q_type == "probability":
                return self._solve_probability(expr_clean)
            elif q_type == "linear_algebra":
                return self._solve_linear_algebra(expr_clean)
            elif q_type == "series":
                return self._solve_series(expr_clean)
            else:
                return self._solve_general(expr_clean)
        except Exception as e:
            logger.error(f"[MathAgent] Solver failed: {e}")
            return self._error_result(expr_clean, str(e))

    # ── Specialised Solvers ───────────────────────────────────────────────────

    def _solve_general(self, expression: str) -> dict[str, Any]:
        """Solve arithmetic, algebra, polynomials, equations."""
        import sympy as sp
        from sympy.parsing.sympy_parser import (
            parse_expr, standard_transformations,
            implicit_multiplication_application, convert_xor
        )
        transformations = standard_transformations + (
            implicit_multiplication_application, convert_xor,
        )

        result = self._base_result(expression)

        # Normalise: ÷→/, ×→*
        expr_norm = expression.replace("÷", "/").replace("×", "*").replace("^", "**")
        # Replace standalone 'x' multiply between digits
        expr_norm = re.sub(r"(\d)\s+[xX]\s+(\d)", r"\1*\2", expr_norm)

        if "=" in expr_norm:
            lhs_str, rhs_str = expr_norm.split("=", 1)
            lhs = parse_expr(lhs_str.strip(), transformations=transformations)
            rhs = parse_expr(rhs_str.strip(), transformations=transformations)
            eq = sp.Eq(lhs, rhs)
            symbols_found = sorted(eq.free_symbols, key=str)
            if symbols_found:
                var = symbols_found[0]
                solutions = sp.solve(eq, var)
                result["solution"] = str(solutions)
                result["latex"] = f"$${sp.latex(eq)}$$"
                result["steps"] = [
                    f"**Given:** $${sp.latex(eq)}$$",
                    f"**Solving for** ${var}$:",
                    *[f"**Solution {i+1}:** ${var} = {sp.latex(s)}$" for i, s in enumerate(solutions)],
                ]
            else:
                # Numerical check
                val = sp.simplify(lhs - rhs)
                result["solution"] = f"True: {val == 0}"
                result["latex"] = f"$${sp.latex(eq)}$$"
                result["steps"] = [f"Both sides evaluate: LHS - RHS = {val}"]
        else:
            expr = parse_expr(expr_norm, transformations=transformations)
            simplified = sp.simplify(expr)
            numeric_val = None
            try:
                numeric_val = float(simplified.evalf())
            except Exception:
                pass
            result["solution"] = f"{sp.latex(simplified)}" + (f" = {numeric_val:.6g}" if numeric_val is not None else "")
            result["latex"] = f"$${sp.latex(expr)} = {sp.latex(simplified)}$$"
            result["steps"] = [
                f"**Expression:** $${sp.latex(expr)}$$",
                f"**Simplified:** $${sp.latex(simplified)}$$",
                *([ f"**Numeric value:** ${numeric_val:.6g}$"] if numeric_val is not None else []),
            ]

        logger.info(f"[MathAgent] Result: {result['solution']}")
        return result

    def _solve_integral(self, expression: str) -> dict[str, Any]:
        """Compute definite or indefinite integrals."""
        import sympy as sp
        x = sp.Symbol('x')
        result = self._base_result(expression)

        # Try to extract integrand: "integrate x^2" or "∫x^2 dx"
        integrand_str = re.sub(r"(?i)(integrate|integral of|∫)", "", expression)
        integrand_str = re.sub(r"\s*d[xyt]\s*$", "", integrand_str).strip()
        integrand_str = integrand_str.replace("^", "**")

        # Detect limits: "from 0 to 1" or "[0,1]"
        limits = re.search(r"from\s*(-?[\d\w]+)\s*to\s*(-?[\d\w]+)", expression, re.IGNORECASE)
        bracket_limits = re.search(r"\[(-?[\d\w]+)\s*,\s*(-?[\d\w]+)\]", expression)

        integrand = sp.sympify(integrand_str, locals={"x": x, "e": sp.E, "pi": sp.pi})

        if limits or bracket_limits:
            m = limits or bracket_limits
            a, b = sp.sympify(m.group(1)), sp.sympify(m.group(2))
            integral_result = sp.integrate(integrand, (x, a, b))
            simplified = sp.simplify(integral_result)
            result["solution"] = sp.latex(simplified)
            result["latex"] = f"$$\\int_{{{sp.latex(a)}}}^{{{sp.latex(b)}}} {sp.latex(integrand)} \\, dx = {sp.latex(simplified)}$$"
            result["steps"] = [
                f"**Definite integral:** $\\int_{{{sp.latex(a)}}}^{{{sp.latex(b)}}} {sp.latex(integrand)} \\, dx$",
                f"**Antiderivative:** $F(x) = {sp.latex(sp.integrate(integrand, x))}$",
                f"**Evaluate** $F({sp.latex(b)}) - F({sp.latex(a)})$",
                f"**Result:** ${sp.latex(simplified)}$",
            ]
        else:
            antideriv = sp.integrate(integrand, x)
            result["solution"] = sp.latex(antideriv)
            result["latex"] = f"$$\\int {sp.latex(integrand)} \\, dx = {sp.latex(antideriv)} + C$$"
            result["steps"] = [
                f"**Indefinite integral:** $\\int {sp.latex(integrand)} \\, dx$",
                f"**Apply integration rules**",
                f"**Result:** ${sp.latex(antideriv)} + C$  (C = constant of integration)",
            ]

        return result

    def _solve_derivative(self, expression: str) -> dict[str, Any]:
        """Compute derivatives (including higher-order)."""
        import sympy as sp
        x = sp.Symbol('x')
        result = self._base_result(expression)

        # Extract function: "derivative of x^3" or "d/dx x^3"
        fn_str = re.sub(r"(?i)(derivative of|differentiate|d/dx|dy/dx|d²y/dx²)", "", expression)
        fn_str = fn_str.strip().replace("^", "**")

        # Detect order: "second derivative" or "d²/dx²"
        order = 1
        if re.search(r"second|2nd|d²|d2", expression, re.IGNORECASE):
            order = 2
        elif re.search(r"third|3rd|d³|d3", expression, re.IGNORECASE):
            order = 3

        f = sp.sympify(fn_str, locals={"x": x, "e": sp.E, "pi": sp.pi})
        deriv = sp.diff(f, x, order)
        simplified = sp.simplify(deriv)

        order_str = {1: "first", 2: "second", 3: "third"}.get(order, f"{order}th")
        prime = "'" * min(order, 3) + ("" if order <= 3 else f"^({order})")

        result["solution"] = sp.latex(simplified)
        result["latex"] = f"$$\\frac{{d^{{{order}}}}}{{dx^{{{order}}}}} \\left( {sp.latex(f)} \\right) = {sp.latex(simplified)}$$"
        result["steps"] = [
            f"**Find the {order_str} derivative of** $f(x) = {sp.latex(f)}$",
            f"**Apply differentiation rules** (power rule, chain rule, etc.)",
            f"**f{prime}(x) = {sp.latex(simplified)}**",
        ]
        return result

    def _solve_limit(self, expression: str) -> dict[str, Any]:
        """Evaluate limits."""
        import sympy as sp
        x = sp.Symbol('x')
        result = self._base_result(expression)

        # Extract: "lim x->0 sin(x)/x"
        m = re.search(r"(?:lim\s*)?[xX]\s*[-→>]+\s*(-?[\w\+\-\.]+)\s*(.*)", expression, re.IGNORECASE)
        if not m:
            return self._solve_general(expression)

        point_str = m.group(1).strip()
        fn_str = m.group(2).strip().replace("^", "**")

        point = sp.sympify(point_str)
        f = sp.sympify(fn_str, locals={"x": x, "e": sp.E, "pi": sp.pi})
        lim_result = sp.limit(f, x, point)

        result["solution"] = sp.latex(lim_result)
        result["latex"] = f"$$\\lim_{{x \\to {sp.latex(point)}}} {sp.latex(f)} = {sp.latex(lim_result)}$$"
        result["steps"] = [
            f"**Evaluate:** $\\lim_{{x \\to {sp.latex(point)}}} {sp.latex(f)}$",
            f"**Substitute** $x = {sp.latex(point)}$ (check direct substitution)",
            f"**Apply L'Hôpital / limit laws if needed**",
            f"**Result:** ${sp.latex(lim_result)}$",
        ]
        return result

    def _solve_logarithm(self, expression: str) -> dict[str, Any]:
        """Solve logarithmic expressions and equations."""
        import sympy as sp
        x = sp.Symbol('x')
        result = self._base_result(expression)

        expr_norm = expression.replace("^", "**")

        if "=" in expr_norm:
            lhs_str, rhs_str = expr_norm.split("=", 1)
            lhs = sp.sympify(lhs_str.strip(), locals={"x": x, "log": sp.log, "ln": sp.log, "e": sp.E})
            rhs = sp.sympify(rhs_str.strip(), locals={"x": x, "log": sp.log, "ln": sp.log, "e": sp.E})
            eq = sp.Eq(lhs, rhs)
            solutions = sp.solve(eq, x)
            result["solution"] = str(solutions)
            result["latex"] = f"$${sp.latex(eq)}$$"
            result["steps"] = [
                f"**Given:** $${sp.latex(eq)}$$",
                f"**Apply logarithm properties** (power rule, product rule, quotient rule)",
                f"**Solve for x:** ${sp.latex(solutions)}$",
            ]
        else:
            expr = sp.sympify(expr_norm, locals={"x": x, "log": sp.log, "ln": sp.log, "e": sp.E})
            val = sp.simplify(expr)
            result["solution"] = sp.latex(val)
            result["latex"] = f"$${sp.latex(expr)} = {sp.latex(val)}$$"
            result["steps"] = [
                f"**Expression:** $${sp.latex(expr)}$$",
                f"**Simplify using log laws**",
                f"**Result:** ${sp.latex(val)}$",
            ]
        return result

    def _solve_probability(self, expression: str) -> dict[str, Any]:
        """Handle combinations, permutations, factorials, and basic probability."""
        import sympy as sp
        import math
        result = self._base_result(expression)
        steps = []

        # nCr / nPr
        m_comb = re.search(r"C\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)|(\d+)\s*C\s*(\d+)|(\d+)Cr(\d+)", expression, re.IGNORECASE)
        m_perm = re.search(r"P\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)|(\d+)\s*P\s*(\d+)|(\d+)Pr(\d+)", expression, re.IGNORECASE)
        m_fact = re.search(r"(\d+)\s*!", expression)

        if m_comb:
            grps = [g for g in m_comb.groups() if g is not None]
            n, r = int(grps[0]), int(grps[1])
            val = math.comb(n, r)
            steps = [
                f"**Combination:** $C({n},{r}) = \\binom{{{n}}}{{{r}}}$",
                f"$$\\binom{{{n}}}{{{r}}} = \\frac{{{n}!}}{{{r}! \\cdot ({n}-{r})!}} = \\frac{{{n}!}}{{{r}! \\cdot {n-r}!}}$$",
                f"**Result:** ${val}$",
            ]
            result["solution"] = str(val)
            result["latex"] = f"$$\\binom{{{n}}}{{{r}}} = {val}$$"
        elif m_perm:
            grps = [g for g in m_perm.groups() if g is not None]
            n, r = int(grps[0]), int(grps[1])
            val = math.perm(n, r)
            steps = [
                f"**Permutation:** $P({n},{r})$",
                f"$$P({n},{r}) = \\frac{{{n}!}}{{({n}-{r})!}} = \\frac{{{n}!}}{{{n-r}!}}$$",
                f"**Result:** ${val}$",
            ]
            result["solution"] = str(val)
            result["latex"] = f"$$P({n},{r}) = {val}$$"
        elif m_fact:
            n = int(m_fact.group(1))
            val = math.factorial(n)
            steps = [
                f"**Factorial:** ${n}!$",
                f"$${n}! = {' \\times '.join(str(i) for i in range(n, 0, -1))} = {val}$$" if n <= 12
                else f"$${n}! = {val}$$",
            ]
            result["solution"] = str(val)
            result["latex"] = f"$${n}! = {val}$$"
        else:
            # Fall back to general solver
            return self._solve_general(expression)

        result["steps"] = steps
        return result

    def _solve_linear_algebra(self, expression: str) -> dict[str, Any]:
        """Handle matrix determinants, inverses, eigenvalues."""
        import sympy as sp
        result = self._base_result(expression)

        # Parse matrix from [[a,b],[c,d]] notation
        m = re.search(r"\[\s*\[(.+?)\]\s*,\s*\[(.+?)\]\s*\]", expression)
        if not m:
            # Try to extract 2x2 from free numbers
            nums = re.findall(r"-?\d+\.?\d*", expression)
            if len(nums) == 4:
                a, b, c, d = [sp.Rational(n) for n in nums]
                M = sp.Matrix([[a, b], [c, d]])
            else:
                return self._solve_general(expression)
        else:
            row1 = [sp.Rational(x.strip()) for x in m.group(1).split(",")]
            row2 = [sp.Rational(x.strip()) for x in m.group(2).split(",")]
            M = sp.Matrix([row1, row2])

        det = M.det()
        inv = M.inv() if det != 0 else None
        eigenvals = M.eigenvals()

        result["solution"] = f"det = {det}"
        result["latex"] = f"$$M = {sp.latex(M)}$$"
        result["steps"] = [
            f"**Matrix:** $${sp.latex(M)}$$",
            f"**Determinant:** $\\det(M) = {sp.latex(det)}$",
            f"**Trace:** $\\text{{tr}}(M) = {sp.latex(M.trace())}$",
            *([ f"**Inverse:** $M^{{-1}} = {sp.latex(inv)}$"] if inv is not None else ["**Matrix is singular (no inverse)**"]),
            f"**Eigenvalues:** ${', '.join(f'{sp.latex(k)} (mult. {v})' for k,v in eigenvals.items())}$",
        ]
        return result

    def _solve_series(self, expression: str) -> dict[str, Any]:
        """Evaluate sums of series."""
        import sympy as sp
        n, k = sp.Symbol('n'), sp.Symbol('k')
        result = self._base_result(expression)

        # Detect arithmetic sequence: "sum of first N natural numbers"
        m_nat = re.search(r"sum of first (\d+)", expression, re.IGNORECASE)
        m_sigma = re.search(r"∑|sigma|sum", expression, re.IGNORECASE)

        if m_nat:
            N = int(m_nat.group(1))
            total = N * (N + 1) // 2
            result["solution"] = str(total)
            result["latex"] = f"$$\\sum_{{k=1}}^{{{N}}} k = \\frac{{{N}({N}+1)}}{{2}} = {total}$$"
            result["steps"] = [
                f"**Sum of first {N} natural numbers**",
                f"$$\\sum_{{k=1}}^{{{N}}} k = \\frac{{n(n+1)}}{{2}}$$",
                f"$$= \\frac{{{N} \\times {N+1}}}{{2}} = {total}$$",
            ]
        else:
            return self._solve_general(expression)

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_result(self, expression: str) -> dict[str, Any]:
        return {
            "expression": expression,
            "solution": None,
            "steps": [],
            "latex": None,
            "error": None,
        }

    def _error_result(self, expression: str, error: str) -> dict[str, Any]:
        return {
            "expression": expression,
            "solution": None,
            "steps": [f"Could not solve: {error}"],
            "latex": None,
            "error": error,
        }

    def _generate_solve_steps(self, equation, variable, solutions) -> list[str]:
        import sympy as sp
        steps = [
            f"**Given equation:** $${sp.latex(equation)}$$",
            f"**Solving for:** ${variable}$",
        ]
        for i, sol in enumerate(solutions):
            steps.append(f"**Solution {i+1}:** ${variable} = {sp.latex(sol)}$")
        return steps
