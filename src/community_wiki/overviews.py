"""Validated, bounded document and community synthesis."""

from string import Template

from .models import Overview


def string_schema(maximum):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def validate_object(value, schema, *, length_overrides=None):
    if not isinstance(value, dict) or set(value) != set(schema["properties"]):
        raise ValueError(f"Expected exactly fields {list(schema['properties'])}")
    for key, rule in schema["properties"].items():
        item = value[key]
        if rule["type"] == "string":
            maximum = (length_overrides or {}).get(key, rule["maxLength"])
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{key}: nonblank text required")
            if len(item) > maximum:
                raise ValueError(
                    f"{key}: {len(item)} characters; at most {maximum} characters required"
                )
        else:
            if not isinstance(item, list) or not rule["minItems"] <= len(item) <= rule["maxItems"]:
                raise ValueError(f"{key}: incorrect number of items")
            for entry in item:
                validate_object({"item": entry}, object_schema({"item": rule["items"]}))
            if len({v.strip().casefold() for v in item}) != len(item):
                raise ValueError(f"{key}: duplicate items")


async def document_overview(content, config, text, client):
    c = config.overview
    fragments = text.split(content, c.fragment_tokens)
    previous = None
    prompt = Template(config.prompts.document.read_text(encoding="utf-8")).substitute(
        c.model_dump()
    )
    for index, fragment in enumerate(fragments, 1):
        final = index == len(fragments)
        schema = object_schema(
            {
                "title": string_schema(c.title_max_chars),
                "keywords": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": c.keyword_count,
                    "items": string_schema(c.keyword_max_chars),
                },
                "summary": string_schema(c.summary_max_chars),
            }
            if final
            else {"stage_summary": string_schema(c.stage_max_chars)}
        )
        payload = {
            "fragment_index": index,
            "fragment_count": len(fragments),
            "is_final": final,
            "previous_synthesis": previous,
            "content": fragment,
            "output_schema": schema,
        }
        result = await client.json_completion(
            prompt,
            payload,
            schema,
            c.validation_retries,
            lambda v: validate_object(
                v, schema, length_overrides={"summary": c.summary_validation_max_chars}
            ),
            "document_overview",
        )
        previous = result.get("stage_summary")
    return Overview.model_validate(result)


async def describe_community(documents, config, client):
    c = config.community
    schema = object_schema(
        {"name": string_schema(c.name_max_chars), "overview": string_schema(c.overview_max_chars)}
    )
    payload = {
        "document_overviews": [d.overview.model_dump() for d in documents],
        "output_schema": schema,
    }
    # Explicitly all covered document overviews, including for parent communities.
    return await client.json_completion(
        Template(config.prompts.community.read_text(encoding="utf-8")).substitute(c.model_dump()),
        payload,
        schema,
        c.validation_retries,
        lambda v: validate_object(v, schema),
        "community_overview",
    )
