"""Explicit no-browsing document learning within the shared research lifecycle."""
import asyncio
from contextlib import aclosing

from backend.app.contracts import RuntimeEvent, uid
from backend.app.db import Job
from backend.app.import_learning import ImportExplanation, ImportLearningResult, learning_key, learning_prompt, validate_learning
from backend.app.import_storage import RetainedImportView, summary
from backend.app.retained_imports import RetainedImport
from backend.app.runtime_base import RuntimeFailure


class ImportLearning:
    def __init__(self, research, storage):
        self.research, self.storage, self.db = research, storage, research.db
        self.pending = {}

    async def view(self, scope):
        view = await self.storage.view(scope.document_id)
        if view.document.content_hash != scope.content_hash:
            raise ValueError("Open the original retained document before requesting an explanation")
        return view

    async def lookup(self, scope):
        view = await self.view(scope)
        value = self.db.get("import_explanation:" + learning_key(scope))
        if value:
            validate_learning(ImportExplanation.model_validate(value), view)
        elif learning_key(scope) in self.pending:
            return self.db.job(self.pending[learning_key(scope)])
        return {"status": "cached" if value else "unavailable", "result": value}

    async def submit(self, request):
        cached = await self.lookup(request)
        if cached["result"]:
            return cached
        if not self.research.settings().cloud_enabled:
            raise ValueError("Cloud research is off. Previously generated explanations remain available.")
        request = self.research.selected_request(request)
        key = learning_key(request)
        if key in self.pending:
            return self.db.job(self.pending[key])
        if len(self.research.tasks) >= 20:
            raise ValueError("The research queue is full. Try again when another operation finishes.")
        job_id = uid()
        with self.db.session.begin() as session:
            session.add(Job(id=job_id, request=request.model_dump(mode="json"), status="queued"))
        self.pending[key] = job_id
        task = asyncio.create_task(self.run(job_id, request))
        self.research.tasks[job_id] = task
        def finished(_):
            self.pending.pop(key, None)
            self.research.tasks.pop(job_id, None)
        task.add_done_callback(finished)
        return self.db.job(job_id)

    async def run(self, job_id, request):
        try:
            async with self.research.inference, asyncio.timeout(180):
                if not self.research.settings().cloud_enabled:
                    raise RuntimeFailure("Cloud permission was revoked")
                self.research.selected_request(request)
                self.db.transition(job_id, "running")
                view = await self.view(request)
                prompt = learning_prompt(request, view)
                if not self.research.settings().cloud_enabled:
                    raise RuntimeFailure("Cloud permission was revoked")
                self.research.emit(RuntimeEvent(run_id=job_id, kind="run.started", text="Explaining the retained document without browsing"))
                workspace = self.research.workspace / job_id
                workspace.mkdir(parents=True, exist_ok=True)
                output = ""
                async with aclosing(self.research.adapters[request.provider].stream(prompt, job_id, workspace, request.model, allow_browsing=False)) as events:
                    async for event in events:
                        if event.kind == "message.delta":
                            output += event.text
                            if len(output) > 12000:
                                raise ValueError("Explanation response limit")
                        elif event.kind not in ("run.started", "run.completed"):
                            raise RuntimeFailure("Unexpected provider activity")
                if not self.research.settings().cloud_enabled:
                    raise RuntimeFailure("Cloud permission was revoked")
                output = output.strip()
                if output.startswith("```json") and output.endswith("```"):
                    output = output[7:-3].strip()
                result = ImportLearningResult.model_validate_json(output)
                value = ImportExplanation(**result.model_dump(exclude={"schema_version"}), id=learning_key(request),
                    **request.model_dump(include={"document_id", "content_hash", "language", "level", "provider", "model"}))
                # Recheck current rights before publication; the original record is immutable.
                retained = RetainedImport.model_validate(self.db.get("import:" + request.document_id))
                validate_learning(value, RetainedImportView(item=summary(retained), document=retained.document))
                self.db.complete_import_explanation(job_id, value.model_dump(mode="json"))
        except asyncio.CancelledError:
            self.db.transition(job_id, "cancelled")
            self.research.emit(RuntimeEvent(run_id=job_id, kind="run.cancelled"))
            raise
        except (RuntimeFailure, TimeoutError):
            self.db.transition(job_id, "failed", error="The selected provider could not complete this explanation with browsing disabled. Check Connections and subscription availability before retrying; no fallback was attempted.")
        except Exception:
            self.db.transition(job_id, "failed", error="The document or explanation could not be validated. Try a smaller permitted document. No facts or saved research were changed.")
        finally:
            self.research.approvals.cancel(job_id)
            job = self.db.job(job_id)
            if job and job["status"] != "cancelled":
                self.research.emit(RuntimeEvent(run_id=job_id, kind="run.failed" if job["status"] == "failed" else "run.completed", text=job["error"] or "", data={"status": job["status"]}))
