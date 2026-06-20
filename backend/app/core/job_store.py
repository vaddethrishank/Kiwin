"""
job_store.py
─────────────
Lightweight in-memory store for background-job status and SSE event queues.

Each file upload spawns a background RAG-processing job.  The job writes
progress events into an asyncio.Queue that is consumed by the SSE endpoint
and streamed to the browser in real-time.

No external broker (Kafka, Redis, etc.) is required — FastAPI's own event-loop
handles everything within a single process.
"""

import asyncio
from typing import Dict, Literal, Optional

# ── Status type ────────────────────────────────────────────────────────────────
JobStatus = Literal["pending", "processing", "ready", "error"]

# ── Singleton store ────────────────────────────────────────────────────────────

class JobStore:
    """
    Stores per-file:
      • status   — current lifecycle stage
      • queue    — asyncio.Queue of SSE event strings consumed by the SSE endpoint
      • error    — error message if status == "error"
    """

    def __init__(self) -> None:
        self._status: Dict[str, JobStatus] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._errors: Dict[str, str] = {}

    # ── Lifecycle helpers ──────────────────────────────────────────────────────

    def register(self, file_id: str) -> asyncio.Queue:
        """Register a new job and return its event queue."""
        self._status[file_id] = "pending"
        q: asyncio.Queue = asyncio.Queue()
        self._queues[file_id] = q
        self._errors.pop(file_id, None)
        return q

    def set_status(self, file_id: str, status: JobStatus, error: Optional[str] = None) -> None:
        self._status[file_id] = status
        if error:
            self._errors[file_id] = error

    def get_status(self, file_id: str) -> Optional[JobStatus]:
        return self._status.get(file_id)

    def get_error(self, file_id: str) -> Optional[str]:
        return self._errors.get(file_id)

    def get_queue(self, file_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(file_id)

    async def emit(self, file_id: str, event: str, data: str = "") -> None:
        """Push an SSE-formatted event string onto the file's queue."""
        q = self._queues.get(file_id)
        if q:
            await q.put(f"event: {event}\ndata: {data}\n\n")

    def cleanup(self, file_id: str) -> None:
        """Remove job state after the SSE connection closes."""
        self._status.pop(file_id, None)
        self._queues.pop(file_id, None)
        self._errors.pop(file_id, None)


# Global singleton — imported by rag.py and files.py
job_store = JobStore()
