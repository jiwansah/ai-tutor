from app.agents.orchestrator import TutorContext


def plan(ctx: TutorContext, diagnosis: dict) -> dict:
    readiness = diagnosis["readiness"]
    mode = ctx.mode

    if mode == "socratic":
        strategy = "socratic"
    elif readiness == "low":
        strategy = "scaffold"
    elif readiness == "medium":
        strategy = "explain_with_example"
    else:
        strategy = "challenge"

    return {"strategy": strategy, "readiness": readiness}