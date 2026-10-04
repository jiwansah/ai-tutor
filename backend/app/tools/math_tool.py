import re
from sympy import Eq, solve, symbols, sympify


def try_symbolic_verify(question: str, student_answer: str) -> dict | None:
    """
    Best-effort: if question contains '=x' or solve-style, try SymPy.
    Returns None if not applicable.
    """
    try:
        # Very simple heuristic: question has 'solve' and '='
        if "=" not in question:
            return None

        x = symbols("x")
        # Extract the equation part
        eq_match = re.search(r"([0-9xX\+\-\*/=\(\)\. ]+)", question)
        if not eq_match:
            return None

        eq_str = eq_match.group(1).strip()
        left, right = eq_str.split("=")
        eq = Eq(sympify(left, locals={"x": x}), sympify(right, locals={"x": x}))
        solutions = solve(eq, x)
        if not solutions:
            return None

        correct = solutions[0]
        # Try to parse student's answer as "x = something"
        ans_match = re.search(r"(-?\d+(\.\d+)?)", student_answer)
        if not ans_match:
            return None

        student_val = float(ans_match.group(1))
        is_correct = abs(float(correct) - student_val) < 1e-6

        return {"is_correct": is_correct, "correct_answer": str(correct)}
    except Exception:
        return None