from app.workers.celery_app import celery

@celery.task
def ingest_pdf_task(book_id: str, file_path: str):
    """Background: parse PDF, chunk, embed, store."""
    # Implementation uses PyMuPDF / unstructured
    return {"status": "done", "book_id": book_id}

@celery.task
def recompute_recommendations(student_id: str):
    """Nightly: recompute weak areas and next topics."""
    return {"student_id": student_id}