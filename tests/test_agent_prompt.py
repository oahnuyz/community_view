from community_wiki.agent import Agent


async def test_agent_prompt_limits_follow_configuration(config, store, client, tmp_path):
    config.prompts.agent = tmp_path / "agent.txt"
    config.prompts.agent.write_text(
        "Read at most ${read_chunk_limit} entries. At most ${max_identical_tool_calls} identical calls."
    )
    config.retrieval.read_chunk_limit = 7
    config.agent.max_identical_tool_calls = 3

    class Retriever:
        mode = "naive"

    async def chat(messages, **kwargs):
        system = messages[0]["content"]
        assert "at most 7 entries" in system
        assert "At most 3 identical calls" in system
        assert "${" not in system
        return {"role": "assistant", "content": "test answer"}

    client.chat = chat
    await Agent(config, store, client, Retriever()).ask("test")
