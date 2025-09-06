"""
Placeholder for job matching logic.

The recruitment automation system now delegates candidate‑to‑job matching to
an external n8n workflow.  This file no longer contains any functional
code, but is retained as a stub to avoid import errors from any legacy
modules or third‑party scripts that might reference ``job_matcher``.

If you are integrating this repository into a system that still expects
matching to occur locally, please implement the required functions here.
"""


def match_candidate_to_job(candidate_id: int, job_id: int) -> None:
    """Deprecated stub for backwards compatibility.

    Previously, this function would perform local AI‑based matching of a
    candidate to a job and create a CandidateJobMatch entry.  Matching is
    now handled externally in n8n.  Calling this function will do
    nothing.  It is provided solely to satisfy legacy imports.

    Args:
        candidate_id (int): The ID of the candidate.
        job_id (int): The ID of the job.

    Returns:
        None
    """
    return None