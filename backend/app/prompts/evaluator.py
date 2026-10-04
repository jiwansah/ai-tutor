EVALUATOR_PROMPT = """You are an evaluator for a school tutor.

Question: {question}
Student's answer: {student_answer}

Return JSON:
{{
  "is_correct": true/false,
  "correct_answer": "...",
  "method_valid": true/false,
  "confidence": 0.0-1.0,
  "feedback": "brief feedback for the student"
}}
"""

MISCONCEPTION_PROMPT = """Analyze the student's error and identify a possible misconception.

Concept: {concept}
Question: {question}
Student answer: {student_answer}
Correct answer: {correct_answer}

Return JSON:
{{
  "misconception": "short label or null",
  "explanation": "brief explanation"
}}
"""