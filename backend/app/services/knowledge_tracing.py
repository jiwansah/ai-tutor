P_INIT = 0.2
P_LEARN = 0.15
P_SLIP = 0.1
P_GUESS = 0.2


def update_mastery(prior: float, correct: bool) -> float:
    if correct:
        num = prior * (1 - P_SLIP)
        den = prior * (1 - P_SLIP) + (1 - prior) * P_GUESS
        posterior = num / den if den else prior
    else:
        num = prior * P_SLIP
        den = prior * P_SLIP + (1 - prior) * (1 - P_GUESS)
        posterior = num / den if den else prior
    return posterior + (1 - posterior) * P_LEARN
