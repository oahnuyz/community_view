"""Native tool-call loop; retrieval enrichment belongs to the program, not the agent."""

import asyncio
import json
import uuid
from collections import Counter
from dataclasses import dataclass
from string import Template
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .knowledge_store import record_question
from .knowledge_views import ViewReader
from .metrics import count_round
from .models import QuestionState
from .store import dumps


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchArguments(Arguments):
    query: str = Field(min_length=1)
    search_mode: Literal["vector", "keyword", "hybrid"] | None
    doc_ids: list[str] | None


class ReadViewArguments(Arguments):
    question_ids: list[str] = Field(min_length=1)


TOOL_ARGUMENTS = {
    "search_chunks": SearchArguments,
}
TOOL_DESCRIPTIONS = {
    "search_chunks": "Search chunks by vector, keyword or hybrid. Use null for default search_mode. doc_ids limits chunk search to exact document IDs: null searches all documents, [] searches none. Community expansion is unrestricted. Document overviews include both doc_id and title.",
    "read_view_answers": "Read selected answers by question_ids from the supplied view_catalog.",
}


def tool_definitions(include_views=False):
    arguments = dict(TOOL_ARGUMENTS)
    if include_views:
        arguments["read_view_answers"] = ReadViewArguments
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "strict": True,
                "parameters": schema.model_json_schema(),
            },
        }
        for name, schema in arguments.items()
    ]


@dataclass
class Answer:
    run_id: str
    answer: str
    rounds: int


class Agent:
    def __init__(self, config, store, client, retriever):
        self.config, self.store, self.client, self.retriever = config, store, client, retriever
        self.views = (
            ViewReader(config, store, client, retriever) if config.knowledge.use_compiled else None
        )

    def _prepare_tool(self, call, counts, scope):
        name = call["function"]["name"]
        arguments = dict(TOOL_ARGUMENTS)
        if self.views is not None:
            arguments["read_view_answers"] = ReadViewArguments
        if name not in arguments:
            raise ValueError("Unknown tool")
        raw = json.loads(call["function"]["arguments"])
        args = arguments[name].model_validate(raw).model_dump()
        if name == "search_chunks" and scope is not None:
            requested = args["doc_ids"]
            if requested is not None and set(requested) - self.retriever.documents.keys():
                raise ValueError("Unknown doc_ids; use IDs from retrieved document overviews")
            args["doc_ids"] = sorted(scope if requested is None else scope.intersection(requested))
        key = dumps({"tool": name, "arguments": args})
        counts[key] += 1
        if counts[key] > self.config.agent.max_identical_tool_calls:
            raise ValueError(
                "Repeated identical tool call; refine query or answer with available evidence"
            )
        return name, args

    async def _run_tools(self, calls, state, counts, scope):
        slots = asyncio.Semaphore(self.config.agent.tool_concurrency)

        async def retrieve(name, args):
            try:
                async with slots:
                    if name == "read_view_answers":
                        return (name, args)
                    return await self.retriever.search_hits(**args)
            except (ValueError, TypeError, KeyError) as exc:
                return {"error": str(exc)}

        pending = []
        # Validate/count in call order. Fatal failures cancel and drain sibling tasks.
        async with asyncio.TaskGroup() as group:
            for call in calls:
                try:
                    name, args = self._prepare_tool(call, counts, scope)
                except (ValueError, TypeError, KeyError) as exc:
                    pending.append({"error": str(exc)})
                else:
                    pending.append(group.create_task(retrieve(name, args)))
        messages = []
        # Only this ordered, synchronous pass modifies the shared deduplication state.
        for call, item in zip(calls, pending, strict=True):
            result = item.result() if isinstance(item, asyncio.Task) else item
            if isinstance(result, tuple):
                try:
                    result = self.views.read(**result[1], state=state)
                except (ValueError, TypeError, KeyError) as exc:
                    result = {"error": str(exc)}
            if isinstance(result, list):
                result = self.retriever.context(result, state)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": dumps(result)})
        return messages

    async def ask(
        self,
        question: str,
        *,
        doc_ids=None,
        run_id=None,
        initial_context=None,
        track_question=True,
        external_question_id=None,
    ):
        if not question.strip():
            raise ValueError("Question cannot be blank")
        scope = None if doc_ids is None else set(doc_ids)
        if scope is not None and scope - self.retriever.documents.keys():
            raise ValueError("Unknown doc_ids in question scope")
        # Every question owns its messages, tool context and deduplication state.
        messages = [
            {
                "role": "system",
                "content": Template(self.config.prompts.agent.read_text(encoding="utf-8")).substitute(
                    read_chunk_limit=self.config.retrieval.read_chunk_limit,
                    max_identical_tool_calls=self.config.agent.max_identical_tool_calls,
                ),
            }
        ]
        messages.append(
            {
                "role": "user",
                "content": self.config.prompts.question.read_text(encoding="utf-8").replace(
                    "{question}", question
                ),
            }
        )
        if scope is not None:
            messages.append(
                {
                    "role": "system",
                    "content": f"All chunk searches are restricted to doc_ids: {dumps(sorted(scope))}. Community expansion is unrestricted.",
                }
            )
        state, counts = QuestionState(), Counter()
        run_id = run_id or uuid.uuid4().hex
        if self.config.knowledge.use_compiled:
            messages.append(
                {
                    "role": "system",
                    "content": self.config.knowledge.context_prompt.read_text(encoding="utf-8"),
                }
            )
        if initial_context is not None:
            messages.append(
                {"role": "user", "content": dumps({"initial_context": initial_context})}
            )
            state.seen_communities.update(
                c["community_id"] for c in initial_context.get("communities", [])
            )
            state.seen_overviews.update(
                d["doc_id"] for d in initial_context.get("document_overviews", [])
            )

        def record(status):
            if (
                self.config.knowledge.record_questions
                and track_question
                and (self.retriever.mode != "naive" or self.views is not None)
            ):
                record_question(
                    self.store,
                    run_id,
                    self.retriever.graph_key,
                    question,
                    state.seen_communities | {cid for cid, _ in state.offered_answers},
                    status,
                    external_question_id,
                )

        record("running")
        self.store.save_run(run_id, self.retriever.mode, "running", messages)
        try:
            if self.views is not None:
                catalog = await self.views.catalog(question, state)
                messages.append({"role": "user", "content": dumps(catalog)})
                self.store.save_run(run_id, self.retriever.mode, "running", messages)
                record("running")
            elif self.retriever.mode == "community_guide":
                context = await self.retriever.search(
                    question, state, doc_ids=None if scope is None else sorted(scope)
                )
                context.pop("chunks", None)
                messages.append(
                    {
                        "role": "system",
                        "content": self.config.prompts.community_guide.read_text(encoding="utf-8"),
                    }
                )
                messages.append({"role": "user", "content": dumps({"initial_context": context})})
                self.store.save_run(run_id, self.retriever.mode, "running", messages)
                record("running")
            for round_index in range(self.config.agent.max_rounds):
                count_round()
                last = round_index == self.config.agent.max_rounds - 1
                message = await self.client.chat(
                    messages,
                    tools=tool_definitions(self.views is not None),
                    force_final=last,
                )
                messages.append(message)
                calls = message.get("tool_calls") or []
                if not calls:
                    answer = message.get("content")
                    if not answer or not answer.strip():
                        raise ValueError("Agent returned an empty final answer")
                    self.store.save_run(run_id, self.retriever.mode, "complete", messages)
                    record("complete")
                    return Answer(run_id, answer, round_index + 1)
                if last:
                    raise ValueError("Model ignored final-round tool_choice=none")
                messages.extend(await self._run_tools(calls, state, counts, scope))
                self.store.save_run(run_id, self.retriever.mode, "running", messages)
                record("running")
        except BaseException:
            self.store.save_run(run_id, self.retriever.mode, "failed", messages)
            record("failed")
            raise
        raise AssertionError("unreachable")
