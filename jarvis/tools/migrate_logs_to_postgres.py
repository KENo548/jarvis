import sqlite3
import json
import os

def export_sqlite_to_json(sqlite_path: str, out_path: str):
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM interactions")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            obj = dict(zip(cols, r))
            f.write(json.dumps(obj) + "\n")
    conn.close()


def print_postgres_copy_instructions(jsonl_path: str, table_name: str = 'interactions'):
    print(f"Exported JSONL: {jsonl_path}")
    print("Use your preferred tool to import into Postgres. Example (psql + jq):")
    print("cat data.jsonl | jq -c . | while read line; do psql -c \"INSERT INTO interactions_json (payload) VALUES ('$line'::jsonb);\"; done")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--sqlite', default=os.path.join(os.path.dirname(__file__), '..', 'logs', 'interactions.db'))
    p.add_argument('--out', default='interactions_export.jsonl')
    args = p.parse_args()
    export_sqlite_to_json(args.sqlite, args.out)
    print_postgres_copy_instructions(args.out)
