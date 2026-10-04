"""
Bayesian Knowledge Tracing (simplified, per concept).
p_init: prior mastery
p_learn: probability of learning after attempt
p_slip: P(correct | not mastered)
p_guess: P(correct | mastered)
"""

P_INIT = 0.2
P_LEARN = 0.15
P_SLIP = 0.1
P_GUESS = 0.2


def update_mastery(prior: float, correct: bool) -> float:
    if correct:
        # P(mastered | correct)
        num = prior * (1 - P_SLIP)
        den = prior * (1 - P_SLIP) + (1 - prior) * P_GUESS
        posterior = num / den if den else prior
    else:
        num = prior * P_SLIP
        den = prior * P_SLIP + (1 - prior) * (1 - P_GUESS)
        posterior = num / den if den else prior

    # Apply learning transition
    return posterior + (1 - posterior) * P_LEARN