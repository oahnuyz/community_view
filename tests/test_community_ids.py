from community_wiki.community_ids import remap_community_links, shorten_community_ids
from community_wiki.models import Community


def test_ids_deterministic_persistent_and_preserve_hierarchy(store):
    original = [
        Community(
            "root-hash", 0, None, ["a", "b"], ["left-hash", "right-hash"], "Root", "Overview"
        ),
        Community("left-hash", 1, "root-hash", ["a"]),
        Community("right-hash", 1, "root-hash", ["b"]),
    ]
    result, mapping = shorten_community_ids(store, list(reversed(original)))
    assert mapping == {"root-hash": "C0001", "left-hash": "C0002", "right-hash": "C0003"}
    assert result[0].child_ids == ["C0002", "C0003"]
    assert result[1].parent_id == "C0001"
    assert result[0].overview == "Overview" and result[0].doc_ids == ["a", "b"]
    assert shorten_community_ids(store, result)[0] == result
    assert shorten_community_ids(store, original)[0] == result
    links = [
        {
            "source": "left-hash",
            "target": "right-hash",
            "weight_max": 0.7,
            "edges": [{"source": "a", "target": "b"}],
        }
    ]
    updated = remap_community_links(links, mapping)
    assert updated[0]["source"] == "C0002" and updated[0]["target"] == "C0003"
    assert updated[0]["edges"] == links[0]["edges"]
