"""Neo4j knowledge graph integration for JARVIS.
Phase 4: Maps relationships between projects, tools, people, agents, and concepts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import ServiceUnavailable

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "jarvis-neo4j")

ENTITY_TYPES = {
    "Project", "Agent", "Tool", "Person", "Concept",
    "Document", "Task", "Service", "Repository", "Skill",
}

RELATION_TYPES = {
    "DEPENDS_ON", "OWNS", "CONTRIBUTES_TO", "RELATES_TO",
    "IMPLEMENTS", "USES", "CREATED_BY", "PART_OF",
    "FOLLOWS_UP_ON", "BLOCKS", "REFERENCES", "MONITORS",
}


@dataclass
class GraphEntity:
    name: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.entity_type not in ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {self.entity_type}. Valid: {ENTITY_TYPES}")


@dataclass
class GraphRelation:
    from_entity: str
    to_entity: str
    relation_type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.relation_type not in RELATION_TYPES:
            raise ValueError(f"Unknown relation type: {self.relation_type}. Valid: {RELATION_TYPES}")


class KnowledgeGraph:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASS) -> None:
        self.uri = uri
        self._driver: Any = None
        try:
            self._driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
            self._driver.verify_connectivity()
        except (ServiceUnavailable, Exception):
            self._driver = None

    def _is_connected(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def __enter__(self) -> KnowledgeGraph:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def upsert_entity(self, entity: GraphEntity) -> bool:
        if not self._is_connected():
            return False
        with self._driver.session() as session:
            session.run(
                """
                MERGE (e:Entity {name: $name})
                SET e.entity_type = $entity_type,
                    e.properties = $properties,
                    e.updated_at = $updated_at
                """,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=json.dumps(entity.properties, sort_keys=True),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        return True

    def create_relation(self, relation: GraphRelation) -> bool:
        if not self._is_connected():
            return False
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (a:Entity {{name: $from_name}})
                MATCH (b:Entity {{name: $to_name}})
                MERGE (a)-[r:{relation.relation_type}]->(b)
                SET r.properties = $properties,
                    r.updated_at = $updated_at
                """,
                from_name=relation.from_entity,
                to_name=relation.to_entity,
                properties=json.dumps(relation.properties, sort_keys=True),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        return True

    def get_entity(self, name: str) -> dict[str, Any] | None:
        if not self._is_connected():
            return None
        with self._driver.session() as session:
            result = session.run(
                "MATCH (e:Entity {name: $name}) RETURN e.name AS name, e.entity_type AS entity_type, e.properties AS properties",
                name=name,
            )
            record = result.single()
            if record is None:
                return None
            return {
                "name": record["name"],
                "entity_type": record["entity_type"],
                "properties": json.loads(record["properties"]) if record["properties"] else {},
            }

    def search_entities(self, search_term: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._is_connected():
            return []
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $search_term OR e.entity_type CONTAINS $search_term
                RETURN e.name AS name, e.entity_type AS entity_type, e.properties AS properties
                LIMIT $limit
                """,
                search_term=search_term,
                limit=limit,
            )
            return [
                {
                    "name": r["name"],
                    "entity_type": r["entity_type"],
                    "properties": json.loads(r["properties"]) if r["properties"] else {},
                }
                for r in result
            ]

    def get_relations(self, entity_name: str, direction: str = "both", max_depth: int = 2) -> list[dict[str, Any]]:
        if not self._is_connected():
            return []
        with self._driver.session() as session:
            if direction == "outgoing":
                result = session.run(
                    """
                    MATCH (e:Entity {name: $name})-[r]->(target)
                    RETURN e.name AS source, type(r) AS relation, target.name AS target, r.properties AS properties
                    """,
                    name=entity_name,
                )
            elif direction == "incoming":
                result = session.run(
                    """
                    MATCH (source)-[r]->(e:Entity {name: $name})
                    RETURN source.name AS source, type(r) AS relation, e.name AS target, r.properties AS properties
                    """,
                    name=entity_name,
                )
            else:
                result = session.run(
                    f"""
                    MATCH path = (e:Entity {{name: $name}})-[*1..{max_depth}]-(connected)
                    WITH e, connected, relationships(path) AS rels
                    UNWIND rels AS r
                    RETURN DISTINCT
                        CASE WHEN startNode(r) = e THEN e.name ELSE startNode(r).name END AS source,
                        type(r) AS relation,
                        CASE WHEN endNode(r) = e THEN e.name ELSE endNode(r).name END AS target
                    """,
                    name=entity_name,
                )
            return [
                {
                    "source": r["source"],
                    "relation": r["relation"],
                    "target": r["target"],
                    "properties": json.loads(r["properties"]) if r.get("properties") else {},
                }
                for r in result
            ]

    def delete_entity(self, name: str) -> bool:
        if not self._is_connected():
            return False
        with self._driver.session() as session:
            session.run("MATCH (e:Entity {name: $name}) DETACH DELETE e", name=name)
        return True

    def health(self) -> dict[str, Any]:
        if self._driver is None:
            return {"connected": False, "error": "driver not initialized"}
        try:
            self._driver.verify_connectivity()
            return {"connected": True, "uri": self.uri}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def count_entities(self) -> int:
        if not self._is_connected():
            return 0
        with self._driver.session() as session:
            result = session.run("MATCH (e:Entity) RETURN count(e) AS count")
            record = result.single()
            return record["count"] if record else 0

    def count_relations(self) -> int:
        if not self._is_connected():
            return 0
        with self._driver.session() as session:
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            record = result.single()
            return record["count"] if record else 0


def seed_knowledge_graph() -> dict[str, Any]:
    kg = KnowledgeGraph()
    if not kg._is_connected():
        return {"status": "skipped", "reason": "Neo4j not reachable"}

    entities: list[GraphEntity] = [
        GraphEntity("JARVIS Ecosystem", "Project", {"description": "Autonomous AI engineering ecosystem", "phase": "4"}),
        GraphEntity("Coder Agent", "Agent", {"role": "Writes, reviews, tests, refactors code", "trust_tier": "high"}),
        GraphEntity("Researcher Agent", "Agent", {"role": "Searches web, reads docs, summarizes", "trust_tier": "standard"}),
        GraphEntity("Planner Agent", "Agent", {"role": "Breaks goals into step-by-step plans", "trust_tier": "standard"}),
        GraphEntity("Security Agent", "Agent", {"role": "Audits code, dependencies, policy", "trust_tier": "high"}),
        GraphEntity("QA Agent", "Agent", {"role": "Writes and runs tests, validates outputs", "trust_tier": "high"}),
        GraphEntity("Writer Agent", "Agent", {"role": "Drafts documentation and reports", "trust_tier": "standard"}),
        GraphEntity("Data Agent", "Agent", {"role": "Queries databases, generates reports", "trust_tier": "standard"}),
        GraphEntity("Claude", "Tool", {"type": "AI Model", "provider": "Anthropic"}),
        GraphEntity("Gemini", "Tool", {"type": "AI Model", "provider": "Google"}),
        GraphEntity("Ollama", "Tool", {"type": "Local LLM", "provider": "Open source"}),
        GraphEntity("Chroma DB", "Tool", {"type": "Vector Database", "purpose": "Semantic memory"}),
        GraphEntity("Neo4j", "Tool", {"type": "Graph Database", "purpose": "Knowledge graph"}),
        GraphEntity("SQLite", "Tool", {"type": "Relational Database", "purpose": "State tracking"}),
        GraphEntity("LangGraph", "Tool", {"type": "Orchestration Framework", "purpose": "Multi-agent pipelines"}),
        GraphEntity("Temporal", "Tool", {"type": "Workflow Engine", "purpose": "Durable execution"}),
        GraphEntity("Vault", "Tool", {"type": "Secrets Management", "purpose": "Security"}),
        GraphEntity("n8n", "Tool", {"type": "Automation", "purpose": "Visual workflow pipelines"}),
        GraphEntity("Grafana", "Tool", {"type": "Monitoring", "purpose": "Dashboards"}),
        GraphEntity("Prometheus", "Tool", {"type": "Monitoring", "purpose": "Metrics collection"}),
    ]

    relations: list[GraphRelation] = [
        GraphRelation("JARVIS Ecosystem", "LangGraph", "USES"),
        GraphRelation("JARVIS Ecosystem", "Temporal", "USES"),
        GraphRelation("JARVIS Ecosystem", "Chroma DB", "USES"),
        GraphRelation("JARVIS Ecosystem", "Neo4j", "USES"),
        GraphRelation("JARVIS Ecosystem", "SQLite", "USES"),
        GraphRelation("JARVIS Ecosystem", "Vault", "USES"),
        GraphRelation("JARVIS Ecosystem", "n8n", "USES"),
        GraphRelation("JARVIS Ecosystem", "Grafana", "USES"),
        GraphRelation("JARVIS Ecosystem", "Prometheus", "USES"),
        GraphRelation("Coder Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Researcher Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Planner Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Security Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("QA Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Writer Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Data Agent", "JARVIS Ecosystem", "PART_OF"),
        GraphRelation("Coder Agent", "Claude", "USES"),
        GraphRelation("Researcher Agent", "Gemini", "USES"),
        GraphRelation("Security Agent", "Vault", "USES"),
        GraphRelation("QA Agent", "LangGraph", "USES"),
    ]

    created = 0
    for entity in entities:
        if kg.upsert_entity(entity):
            created += 1

    linked = 0
    for relation in relations:
        if kg.create_relation(relation):
            linked += 1

    kg.close()
    return {
        "status": "ok",
        "entities_created": created,
        "relations_created": linked,
        "total_entities": kg.count_entities(),
        "total_relations": kg.count_relations(),
    }