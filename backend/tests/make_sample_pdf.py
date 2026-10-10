"""
Generate a small fake textbook PDF for testing the parser.
Run inside the backend container:
    docker compose exec backend python /app/tests/make_sample_pdf.py
Creates /app/uploads/sample_math_grade7.pdf
"""
import fitz  # PyMuPDF
from pathlib import Path


PAGES = [
    # (title, body lines, font size)
    ("Simple Equations", [
        "An equation is like a balance.",
        "Whatever you do to one side, you must do to the other.",
    ], 16),

    ("4.1 What is an Equation?", [
        "An equation is a mathematical statement that two expressions are equal.",
        "The equals sign (=) shows that the left side equals the right side.",
        "For example, x + 3 = 7 is an equation.",
    ], 12),

    ("4.2 Solving an Equation", [
        "To solve an equation, we need to isolate the variable.",
        "For x + a = b, subtract a from both sides.",
        "Example: solve x + 3 = 7. Subtract 3 from both sides: x = 4.",
        "Check: 4 + 3 = 7. Correct.",
    ], 12),

    ("4.3 More Equations", [
        "Sometimes an equation has a coefficient in front of the variable.",
        "For 2x = 8, divide both sides by 2 to get x = 4.",
        "Practice: solve 3x = 12.",
    ], 12),

    ("Chapter 5", [
        "Lines and Angles",
        "An angle is formed when two rays meet at a common point.",
    ], 16),

    ("5.1 Types of Angles", [
        "Acute angle: less than 90 degrees.",
        "Right angle: exactly 90 degrees.",
        "Obtuse angle: more than 90 but less than 180 degrees.",
    ], 12),

    ("5.2 Complementary Angles", [
        "Two angles are complementary if their sum is 90 degrees.",
        "Example: 30 and 60 are complementary.",
    ], 12),
]


def make_pdf(out_path: str = "/app/uploads/sample_math_grade7.pdf"):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # Title page
    page = doc.new_page()
    page.insert_text((72, 120), "Mathematics", fontsize=28)
    page.insert_text((72, 160), "Grade 7", fontsize=20)

    for title, lines, size in PAGES:
        page = doc.new_page()
        y = 90
        page.insert_text((72, y), title, fontsize=size)
        y += size + 15
        for ln in lines:
            page.insert_text((72, y), ln, fontsize=11)
            y += 18

    doc.save(out_path)
    doc.close()
    print(f"✓ Wrote {out_path}")


if __name__ == "__main__":
    make_pdf()
