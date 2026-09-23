"""Optional semantic partitioning with exact, exclusive document coverage."""

from collections import Counter

from .overviews import object_schema


def validate_partition(value, doc_ids):
    if not isinstance(value, dict) or set(value) != {"split", "groups"}:
        raise ValueError("Expected exactly fields split and groups")
    if type(value["split"]) is not bool or not isinstance(value["groups"], list):
        raise ValueError("split must be a boolean and groups must be an array")
    groups = value["groups"]
    if not value["split"]:
        if groups:
            raise ValueError("When split is false, groups must be []")
        return
    if len(groups) < 2:
        raise ValueError("When split is true, provide at least two nonempty groups")
    if any(
        not isinstance(group, list)
        or not group
        or any(not isinstance(doc_id, str) for doc_id in group)
        for group in groups
    ):
        raise ValueError("Each group must be a nonempty array of document ID strings")
    counts = Counter(doc_id for group in groups for doc_id in group)
    missing = sorted(set(doc_ids) - counts.keys())
    unknown = sorted(counts.keys() - set(doc_ids))
    repeated = sorted(doc_id for doc_id, count in counts.items() if count != 1)
    if missing or unknown or repeated:
        raise ValueError(
            "Every member document must occur exactly once: "
            f"missing={missing}; unknown={unknown}; repeated={repeated}"
        )


async def split_community(community, documents, config, client):
    doc_ids = [doc.doc_id for doc in documents]
    schema = object_schema(
        {
            "split": {"type": "boolean"},
            "groups": {
                "type": "array",
                "maxItems": len(doc_ids),
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "enum": sorted(doc_ids)},
                },
            },
        }
    )
    value = await client.json_completion(
        config.prompts.community_split.read_text(encoding="utf-8"),
        {
            "name": community.name,
            "overview": community.overview,
            "max_documents": config.community.max_documents,
            "document_overviews": [
                {"doc_id": doc.doc_id, **doc.overview.model_dump()} for doc in documents
            ],
        },
        schema,
        config.community.validation_retries,
        lambda result: validate_partition(result, doc_ids),
        "community_split",
    )
    return sorted([sorted(group) for group in value["groups"]], key=lambda group: group[0])
