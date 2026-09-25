"""Native tool-call loop; retrieval enrichment belongs to the program, not the agent."""

import asyncio
import json
import uuid
from collections import Counter
from dataclasses import dataclass
from string import Template
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .metrics import count_round
from .models import QuestionState
from .store import dumps


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchArguments(Arguments):
    query: str = Field(min_length=1)
    search_mode: Literal["vector", "keyword", "hybrid"] | None
    doc_ids: list[str] | None


TOOL_ARGUMENTS = {
    "search_chunks": SearchArguments,
}
TOOL_DESCRIPTIONS = {
    "search_chunks": "Search chunks by vector, keyword or hybrid. Use null for default search_mode. doc_ids limits chunk search to exact document IDs: null searches all documents, [] searches none. Community expansion is unrestricted. Document overviews include both doc_id and title.",
}


def tool_definitions():
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
        for name, schema in TOOL_ARGUMENTS.items()
    ]


@dataclass
class Answer:
    run_id: str
    answer: str
    rounds: int


class Agent:
    def __init__(self, config, store, client, retriever):
        self.config, self.store, self.client, self.retriever = config, store, client, retriever

    def _prepare_tool(self, call, counts, scope):
        name = call["function"]["name"]
        if name not in TOOL_ARGUMENTS:
            raise ValueError("Unknown tool")
        raw = json.loads(call["function"]["arguments"])
        args = TOOL_ARGUMENTS[name].model_validate(raw).model_dump()
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

        async def retrieve(args):
            try:
                async with slots:
                    return await self.retriever.search_hits(**args)
            except (ValueError, TypeError, KeyError) as exc:
                return {"error": str(exc)}

        pending = []
        # Validate/count in call order. Fatal failures cancel and drain sibling tasks.
        async with asyncio.TaskGroup() as group:
            for call in calls:
                try:
                    _, args = self._prepare_tool(call, counts, scope)
                except (ValueError, TypeError, KeyError) as exc:
                    pending.append({"error": str(exc)})
                else:
                    pending.append(group.create_task(retrieve(args)))
        messages = []
        # Only this ordered, synchronous pass modifies the shared deduplication state.
        for call, item in zip(calls, pending, strict=True):
            result = item.result() if isinstance(item, asyncio.Task) else item
            if isinstance(result, list):
                result = self.retriever.context(result, state)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": dumps(result)})
        return messages

    async def ask(self, question: str, *, doc_ids=None, run_id=None):
        if not question.strip():
            raise ValueError("Question cannot be blank")
        scope = None if doc_ids is None else set(doc_ids)
        if scope is not None and scope - self.retriever.documents.keys():
            raise ValueError("Unknown doc_ids in question scope")
        # Every question owns its messages, tool context and deduplication state.
        messages = [
            {
                "role": "system",
                "content": Template(
                    self.config.prompts.agent.read_text(encoding="utf-8")
                ).substitute(
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
        self.store.save_run(run_id, self.retriever.mode, "running", messages)
        try:
            if self.retriever.mode == "community_guide":
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
            for round_index in range(self.config.agent.max_rounds):
                count_round()
                last = round_index == self.config.agent.max_rounds - 1
                message = await self.client.chat(
                    messages,
                    tools=tool_definitions(),
                    force_final=last,
                )
                messages.append(message)
                calls = message.get("tool_calls") or []
                if not calls:
                    answer = message.get("content")
                    if not answer or not answer.strip():
                        raise ValueError("Agent returned an empty final answer")
                    self.store.save_run(run_id, self.retriever.mode, "complete", messages)
                    return Answer(run_id, answer, round_index + 1)
                if last:
                    raise ValueError("Model ignored final-round tool_choice=none")
                messages.extend(await self._run_tools(calls, state, counts, scope))
                self.store.save_run(run_id, self.retriever.mode, "running", messages)
        except BaseException:
            self.store.save_run(run_id, self.retriever.mode, "failed", messages)
            raise
        raise AssertionError("unreachable")
