"""
Symbolic math verification for the tutor.

Two responsibilities:
  1. verify_question(question)  -> solve a natural-language math question with SymPy
  2. verify_answer(question, llm_text) -> check the LLM's final answer against SymPy
"""
import re
from typing import Any
import sympy as sp


# ---------------------------------------------------------------
# Stopwords
# ---------------------------------------------------------------

_STOPWORDS = [
    "how do i solve", "how can i solve", "how to solve",
    "solve for", "solve the equation", "solve this equation",
    "find the value of", "find the solution of",
    "what is the value of", "what is", "what's", "whats",
    "how do i", "how do you", "how can i", "how to", "how",
    "can you", "could you", "please", "tell me", "show me",
    "the value of", "value of",
    "solve", "find", "calculate", "compute", "evaluate",
]

_VARIABLE_PREFERENCE = ["x", "y", "z", "n", "t"]


def _clean_question(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[?!,;:\"']+$", "", t)
    for w in _STOPWORDS:
        t = re.sub(rf"\b{re.escape(w)}\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _is_math_token(tok: str, allowed_vars: set[str]) -> bool:
    """Does this token look like part of a math expression?"""
    if not tok:
        return False
    if re.search(r"\d", tok):                                   # contains digit
        return True
    if re.fullmatch(r"[+\-*/^()]+", tok):                       # operator
        return True
    if len(tok) == 1 and tok in allowed_vars:                   # single-letter var
        return True
    if re.fullmatch(r"\d+[a-zA-Z]+|[a-zA-Z]+\d+", tok):         # 2x, x2
        return True
    if re.fullmatch(r"[a-zA-Z]+\^\d+", tok):                    # x^2
        return True
    return False


def _detect_allowed_vars(cleaned: str) -> set[str]:
    letters = set(c for c in cleaned if c.isalpha())
    preferred = [v for v in _VARIABLE_PREFERENCE if v in letters]
    return set(preferred) if preferred else letters


def _take_math_right_to_left(tokens: list[str], allowed: set[str]) -> list[str]:
    """From the end, take math-like tokens until a non-math token stops us."""
    out: list[str] = []
    for tok in reversed(tokens):
        if _is_math_token(tok, allowed):
            out.insert(0, tok)
        else:
            break
    return out


def _take_math_left_to_right(tokens: list[str], allowed: set[str]) -> list[str]:
    """From the start, take math-like tokens until a non-math token stops us."""
    out: list[str] = []
    for tok in tokens:
        if _is_math_token(tok, allowed):
            out.append(tok)
        else:
            break
    return out


def extract_equation(text: str) -> tuple[str, str, str] | None:
    """
    Return (lhs, rhs, variable) if text contains a solvable equation.

    Strategy: anchor on the equals sign.
      - Walk LEFT from '=' collecting math tokens until we hit a non-math token.
      - Walk RIGHT from '=' collecting math tokens until we hit a non-math token.
    This ignores leading English like "What is the value of x in ...".
    """
    cleaned = _clean_question(text)
    if "=" not in cleaned:
        return None

    idx = cleaned.rindex("=")
    lhs_tokens = cleaned[:idx].split()
    rhs_tokens = cleaned[idx + 1:].split()
    if not lhs_tokens or not rhs_tokens:
        return None

    allowed = _detect_allowed_vars(cleaned)

    lhs_parts = _take_math_right_to_left(lhs_tokens, allowed)
    rhs_parts = _take_math_left_to_right(rhs_tokens, allowed)

    if not lhs_parts or not rhs_parts:
        return None

    lhs = " ".join(lhs_parts)
    rhs = " ".join(rhs_parts)

    var = None
    for v in _VARIABLE_PREFERENCE:
        if v in lhs or v in rhs:
            var = v
            break
    if var is None:
        return None

    return lhs, rhs, var


# ---------------------------------------------------------------
# SymPy solve
# ---------------------------------------------------------------

def _to_sympy(expr_str: str, var_symbol: sp.Symbol) -> sp.Expr:
    s = expr_str.strip()
    # Strip punctuation that LLMs add mid-expression (commas, periods, etc.)
    s = re.sub(r"[,;:?!]+", "", s)
    s = s.replace("^", "**")
    s = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", s)
    s = re.sub(r"([a-zA-Z])\(", r"\1*(", s)
    s = re.sub(r"\)([a-zA-Z0-9])", r")*\1", s)
    return sp.sympify(s, locals={str(var_symbol): var_symbol})


def solve_equation(lhs: str, rhs: str, var: str) -> list[str] | None:
    try:
        x = sp.symbols(var)
        eq = sp.Eq(_to_sympy(lhs, x), _to_sympy(rhs, x))
        if x not in eq.free_symbols:
            return None
        solutions = sp.solve(eq, x)
        if not solutions:
            return None
        return [str(sp.simplify(s)) for s in solutions]
    except Exception:
        return None


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def verify_question(question: str) -> dict[str, Any]:
    parsed = extract_equation(question)
    if not parsed:
        return {"is_math": False}

    lhs, rhs, var = parsed
    solutions = solve_equation(lhs, rhs, var)
    if solutions is None:
        return {"is_math": False}

    return {
        "is_math": True,
        "equation": f"{lhs} = {rhs}",
        "variable": var,
        "solutions": solutions,
    }


def _extract_llm_answer(llm_text: str, variable: str) -> str | None:
    pattern = rf"{re.escape(variable)}\s*=\s*(-?\d+(?:\.\d+)?(?:/\d+)?)"
    matches = re.findall(pattern, llm_text)
    if not matches:
        return None
    return matches[-1]


def verify_answer(question: str, llm_text: str) -> dict[str, Any]:
    qv = verify_question(question)
    if not qv["is_math"]:
        return {"verified": None, "reason": "not a solvable math question"}

    var = qv["variable"]
    sols = qv["solutions"]
    llm_ans = _extract_llm_answer(llm_text, var)

    if llm_ans is None:
        return {
            "verified": False,
            "reason": f"could not find '{var} = ...' in the answer",
            "sympy_solutions": sols,
            "llm_answer": None,
        }

    try:
        llm_val = float(sp.sympify(llm_ans))
    except Exception:
        return {
            "verified": False,
            "reason": "could not parse LLM answer",
            "sympy_solutions": sols,
            "llm_answer": llm_ans,
        }

    sympy_vals: list[float] = []
    for s in sols:
        try:
            sympy_vals.append(float(sp.sympify(s)))
        except Exception:
            pass

    if not sympy_vals:
        return {
            "verified": False,
            "reason": "SymPy solutions could not be compared numerically",
            "sympy_solutions": sols,
            "llm_answer": llm_ans,
        }

    matches = any(abs(llm_val - v) < 1e-6 for v in sympy_vals)
    return {
        "verified": matches,
        "sympy_solutions": sols,
        "llm_answer": llm_ans,
        "reason": "match" if matches else "answer does not match SymPy",
    }
