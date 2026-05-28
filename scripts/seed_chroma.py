"""
Seed Chroma with text from `memory/obsidian-vault` (markdown files).

Requires: `chromadb` and a local embeddings provider. This script uses a
sentence-transformers embedding model when available so seeding stays local.

Usage:
  python scripts/seed_chroma.py
"""
import pathlib
import os
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    print('chromadb not installed; install with: pip install chromadb')
    raise

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

def simple_text_from_md(path: pathlib.Path):
    text = path.read_text(encoding='utf-8')
    # very small cleanup
    return text

def main():
    vault = pathlib.Path('memory/obsidian-vault')
    if not vault.exists():
        print('No Obsidian vault found at memory/obsidian-vault. Exiting.')
        return

    # Use the default client constructor; persistent directory will be under memory/chroma
    client = chromadb.Client()
    try:
        collection = client.get_or_create_collection('obsidian')
    except Exception:
        collection = client.create_collection('obsidian')

    embedding_model = None
    if SentenceTransformer is not None:
        embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    docs = []
    metadatas = []
    ids = []
    for f in vault.rglob('*.md'):
        txt = simple_text_from_md(f)
        ids.append(str(f))
        docs.append(txt)
        metadatas.append({'path': str(f)})

    if docs:
        if embedding_model is not None:
            embeddings = embedding_model.encode(docs, normalize_embeddings=True).tolist()
            collection.add(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
        else:
            collection.add(ids=ids, documents=docs, metadatas=metadatas)
        # Newer chromadb client persists automatically; no explicit persist()
        print(f'Added {len(docs)} documents to Chroma')
    else:
        print('No markdown files found to seed.')

if __name__ == '__main__':
    main()
