#!/usr/bin/env python3
"""Seed Neo4j from a local SQLite graph.db if present.

Requires: `neo4j` Python driver. Configure NEO4J_URI env or defaults to bolt://localhost:7687
Auth: reads `security/neo4j-auth.txt` if present (format username:password).
"""
import os
import pathlib
import sqlite3

try:
    from neo4j import GraphDatabase
except Exception:
    print('neo4j driver not installed; pip install neo4j')
    raise

ROOT = pathlib.Path('c:/jarvis')
GRAPH_DB = ROOT / 'memory' / 'sqlite' / 'graph.db'

def read_auth():
    auth_file = ROOT / 'security' / 'neo4j-auth.txt'
    if not auth_file.exists():
        return None
    txt = auth_file.read_text(encoding='utf-8').strip()
    if ':' in txt:
        user, pwd = txt.split(':',1)
        return (user.strip(), pwd.strip())
    return None


def main():
    if not GRAPH_DB.exists():
        print('No graph.db SQLite found at', GRAPH_DB)
        return

    uri = os.environ.get('NEO4J_URI', 'bolt://127.0.0.1:7687')
    auth = read_auth()
    if auth is None:
        print('No auth found in security/neo4j-auth.txt; aborting for safety')
        return

    driver = GraphDatabase.driver(uri, auth=auth)
    conn = sqlite3.connect(str(GRAPH_DB))
    cur = conn.cursor()

    # Heuristic: look for graph-style tables first, then fall back to workflow tables.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print('Found tables:', tables)
    nodes_table = None
    edges_table = None
    for t in tables:
        if t.lower().startswith('node') or t.lower().startswith('nodes'):
            nodes_table = t
        if t.lower().startswith('edge') or t.lower().startswith('edges'):
            edges_table = t

    if not nodes_table:
        for candidate in ('workflow_runs', 'workflow_steps'):
            if candidate in tables:
                nodes_table = candidate
                break

    if not nodes_table:
        print('No nodes table found; cannot seed Neo4j')
        return

    # Read nodes
    cur.execute(f'SELECT * FROM {nodes_table} LIMIT 1000')
    nodes = cur.fetchall()
    col_names = [c[0] for c in cur.description]
    print(f'Loading {len(nodes)} nodes (showing columns {col_names})')

    def tx_import(tx):
        for row in nodes:
            props = dict(zip(col_names, row))
            label = props.get('label') or props.get('type') or nodes_table[:-1].title().replace('_', '')
            nid = props.get('id') or props.get('run_id') or props.get('workflow_run_id') or props.get('step_id')
            if nid is not None:
                props['id'] = nid
            safe_label = ''.join(ch if ch.isalnum() else '_' for ch in str(label)) or 'Node'
            tx.run(f"CREATE (n:{safe_label} $props)", props=props)

    with driver.session() as session:
        session.execute_write(tx_import)

    if edges_table:
        cur.execute(f'SELECT * FROM {edges_table} LIMIT 1000')
        edges = cur.fetchall()
        ecols = [c[0] for c in cur.description]
        print(f'Loading {len(edges)} edges (cols {ecols})')

        def tx_edges(tx):
            for r in edges:
                rec = dict(zip(ecols, r))
                src = rec.get('source') or rec.get('from') or rec.get('src')
                dst = rec.get('target') or rec.get('to') or rec.get('dst')
                etype = rec.get('type') or 'RELATED'
                tx.run(
                    "MATCH (a),(b) WHERE a.id=$src AND b.id=$dst CREATE (a)-[r:"+etype+" ]->(b)",
                    src=src, dst=dst
                )
        with driver.session() as session:
            session.execute_write(tx_edges)
    elif 'workflow_steps' in tables and 'workflow_runs' in tables:
        cur.execute('SELECT * FROM workflow_steps LIMIT 1000')
        steps = cur.fetchall()
        step_cols = [c[0] for c in cur.description]
        print(f'Loading {len(steps)} workflow steps (cols {step_cols})')

        def tx_steps(tx):
            for row in steps:
                rec = dict(zip(step_cols, row))
                label = ''.join(ch if ch.isalnum() else '_' for ch in str(rec.get('step_type') or rec.get('name') or 'WorkflowStep'))
                tx.run(f"CREATE (n:{label} $props)", props=rec)

        with driver.session() as session:
            session.execute_write(tx_steps)

    print('Neo4j seeding complete')

if __name__ == '__main__':
    main()
