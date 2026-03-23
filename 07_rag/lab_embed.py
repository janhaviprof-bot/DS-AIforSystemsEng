# lab_embed.py
# Semantic RAG for Aircraft Inspiration (adapts 05_embed.py)
# Pairs with 05_embed.py
# Tim Fraser

# This lab adapts the semantic search RAG workflow for the aircraft database.
# Uses aircraft.csv (3000+ aircraft with specs) and get_aircraft_chunks() to build
# embeddings for semantic search. Queries like "stealth fighter" or "long range
# transport" retrieve relevant aircraft for design inspiration.

# 0. SETUP ###################################

## 0.1 Load Packages ##########################

# pip install sentence-transformers sqlite-vec requests
import json
import os
import time

# Load .env for OPENAI_API_KEY
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sqlite3
import requests
from sentence_transformers import SentenceTransformer
from sqlite_vec import load as sqlite_vec_load, serialize_float32

# Import aircraft chunks from functions (includes spec fields for better search)
from functions import get_aircraft_chunks

## 0.2 Configuration ##########################

# Aircraft-specific database (separate from Lower Manhattan embed.db)
DB_PATH = "data/aircraft_embed.db"
AIRCRAFT_CSV = "data/aircraft.csv"
EMBED_MODEL = "all-MiniLM-L6-v2"
VEC_DIM = 384
MODEL = "gpt-4o-mini"  # OpenAI model for RAG answer step

# Working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)


# 1. FUNCTIONS ################################

def agent_run(role, task, model="gpt-4o-mini"):
    """Call OpenAI API for RAG answer generation."""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in .env file. Please set it up first.")

    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": role},
            {"role": "user", "content": task}
        ],
        "stream": False
    }
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json=body
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


_embed_model = None


def get_embed_model(model_name=None):
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def embed(text):
    m = get_embed_model()
    return m.encode(text).tolist()


def build_index_from_chunks(conn, chunks):
    """Embed chunks and insert into vec_chunks + chunks tables."""
    n = len(chunks)
    print(f"Embedding {n} aircraft chunks with {EMBED_MODEL}...")
    for i, text in enumerate(chunks):
        vec = embed(text)
        blob = serialize_float32(vec)
        conn.execute("INSERT INTO chunks (id, text) VALUES (?, ?)", (i, text))
        conn.execute(
            "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
            (i, blob)
        )
    conn.commit()
    print("Index built.\n")


def search_embed_sql(conn, query, k=5):
    """Semantic search: embed query, KNN match, return top k chunks."""
    query_vec = embed(query)
    query_blob = serialize_float32(query_vec)
    cur = conn.execute(
        """
        SELECT rowid, distance
        FROM vec_chunks
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (query_blob, k)
    )
    rows = cur.fetchall()
    if not rows:
        return []
    out = []
    for rowid, distance in rows:
        (text,) = conn.execute("SELECT text FROM chunks WHERE id = ?", (rowid,)).fetchone()
        score = 1 - distance
        out.append({"id": rowid, "score": score, "text": text})
    return out


def connect_db(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec_load(conn)
    conn.enable_load_extension(False)
    return conn


# 2. BUILD AIRCRAFT INDEX ################################

# Load aircraft chunks (includes name, type, description, and spec fields)
chunks = get_aircraft_chunks(csv_path=AIRCRAFT_CSV, include_specs=True)
n = len(chunks)
print(f"Loaded {n} aircraft chunks from {AIRCRAFT_CSV}.\n")

conn = connect_db(DB_PATH)

# Create tables (drop if exists so we rebuild each run)
conn.execute("DROP TABLE IF EXISTS vec_chunks")
conn.execute("DROP TABLE IF EXISTS chunks")
conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
conn.execute(f"CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[{VEC_DIM}] distance_metric=cosine)")
conn.commit()

start = time.perf_counter()
build_index_from_chunks(conn, chunks)
elapsed = time.perf_counter() - start
print(f"Time taken to build index: {elapsed:.2f} seconds\n")

# Preview first few chunks
preview = conn.execute("SELECT id, text FROM chunks LIMIT 3").fetchall()
for row in preview:
    print(f"[{row[0]}] {row[1][:150]}...\n")

# 3. TEST SEARCH ################################

# Example: find stealth aircraft
test_query = "stealth fighter"
results = search_embed_sql(conn, test_query, k=3)
print(f"Test search: '{test_query}'")
for r in results:
    print(f"  Score {r['score']:.3f}: {r['text'][:120]}...\n")

# 4. RAG WORKFLOW ################################

# User query about aircraft design inspiration
query = "What aircraft are good inspiration for a long-range stealth reconnaissance design?"
results = search_embed_sql(conn, query, k=5)
context = "\n\n---\n\n".join(row["text"] for row in results)

print("Retrieved context (top 5):\n")
for i, row in enumerate(results):
    text = row["text"]
    preview = text[:400] + "..." if len(text) > 400 else text
    print(f"[{i}] {preview}\n")

role = (
    "You are an aircraft design consultant. The user is designing an aircraft and seeks inspiration from historical aircraft. "
    "Answer the question using only the context provided (retrieved aircraft). "
    "Recommend 2-3 specific aircraft with brief reasons why they are relevant. "
    "Format your response as markdown with a title and bullet points. "
    "Content format: <user query> | <context from vector search>. "
    "Recommend ONLY aircraft that appear in the context. Do not mention any aircraft that are not listed in the context."
)

answer = agent_run(role=role, task=f"{query} | {context}", model=MODEL)
print("RAG Answer:\n")
print(answer)

conn.close()
print("\nDone.")
