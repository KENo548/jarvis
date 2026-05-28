"""Tests for Phase 4 Neo4j knowledge graph integration."""

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import knowledge_graph
import pytest


def test_entity_dataclass() -> None:
    entity = knowledge_graph.GraphEntity("Test Project", "Project", {"phase": "4"})
    assert entity.name == "Test Project"
    assert entity.entity_type == "Project"
    assert entity.properties["phase"] == "4"


def test_entity_invalid_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown entity type"):
        knowledge_graph.GraphEntity("Bad", "InvalidType")


def test_relation_dataclass() -> None:
    rel = knowledge_graph.GraphRelation("A", "B", "DEPENDS_ON", {"weight": 1})
    assert rel.from_entity == "A"
    assert rel.to_entity == "B"
    assert rel.relation_type == "DEPENDS_ON"


def test_relation_invalid_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown relation type"):
        knowledge_graph.GraphRelation("A", "B", "INVALID")


def test_health_when_connected() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    health = kg.health()
    kg.close()
    assert health["connected"] is True


def test_upsert_and_get_entity() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    entity = knowledge_graph.GraphEntity("__test_entity__", "Concept", {"test": True})
    assert kg.upsert_entity(entity) is True
    retrieved = kg.get_entity("__test_entity__")
    assert retrieved is not None
    assert retrieved["name"] == "__test_entity__"
    assert retrieved["entity_type"] == "Concept"
    props = retrieved["properties"]
    assert isinstance(props, dict)
    kg.delete_entity("__test_entity__")
    kg.close()


def test_create_and_get_relation() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    a = knowledge_graph.GraphEntity("__test_rel_a__", "Concept")
    b = knowledge_graph.GraphEntity("__test_rel_b__", "Concept")
    kg.upsert_entity(a)
    kg.upsert_entity(b)
    rel = knowledge_graph.GraphRelation("__test_rel_a__", "__test_rel_b__", "RELATES_TO")
    assert kg.create_relation(rel) is True
    relations = kg.get_relations("__test_rel_a__", direction="outgoing")
    assert any(r["target"] == "__test_rel_b__" for r in relations)
    kg.delete_entity("__test_rel_a__")
    kg.delete_entity("__test_rel_b__")
    kg.close()


def test_search_entities() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    results = kg.search_entities("Agent", limit=10)
    assert len(results) >= 6
    names = [r["name"] for r in results]
    assert "Coder Agent" in names
    assert "Researcher Agent" in names
    kg.close()


def test_seed_populates_graph() -> None:
    result = knowledge_graph.seed_knowledge_graph()
    assert result["status"] == "ok"
    assert result["entities_created"] >= 20
    assert result["relations_created"] >= 20


def test_count_entities() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    count = kg.count_entities()
    kg.close()
    assert count >= 20


def test_count_relations() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    count = kg.count_relations()
    kg.close()
    assert count >= 20


def test_delete_entity_removes_it() -> None:
    kg = knowledge_graph.KnowledgeGraph()
    entity = knowledge_graph.GraphEntity("__test_delete__", "Concept")
    kg.upsert_entity(entity)
    assert kg.get_entity("__test_delete__") is not None
    assert kg.delete_entity("__test_delete__") is True
    assert kg.get_entity("__test_delete__") is None
    kg.close()