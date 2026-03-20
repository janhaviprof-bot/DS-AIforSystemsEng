# 05_embed.py
# Semantic RAG with Embeddings (sentence-transformers + SQLite)
# Pairs with 05_embed.R
# Tim Fraser

# In this exercise, we're going to look at the first few pages of the Lower Manhattan Recovery Plan after Hurricane Sandy,
# shown in data/lower_manhattan_recovery_plan.txt.
# For more details, see: https://doi.org/10.1016/j.jenvman.2025.127089
# More plans at: https://github.com/timothyfraser/ny_committees/tree/main/text

# We're going to use semantic search RAG to answer questions about the plan.
# Why use semantic search RAG rather than 'naive' RAG (basic keyword search)?
# - can find relevant chunks even if keywords are not present
# Requirements:
# - need to encode the text into vector 'embeddings' (transform them into numbers)
# - need to store the embeddings in a database
# - need to run a similarity search on the embeddings to find the most relevant chunks
# - need to generate a response based on the relevant chunks

# Semantic RAG: embed text with sentence-transformers, store in SQLite via
# sqlite-vec (vec0), and run KNN search inside the database. Pairs with 05_embed.R.
# Requires sqlite-vec extension; Python uses sqlite_vec.load() to load it.


# 0. SETUP ###################################

## 0.1 Load Packages ##########################

# Install python libraries
# pip install sentence-transformers sqlite-vec requests
# sentence-transformers will take a fair amount of space, fyi

# Prefer local 07_rag/functions.py over the PyPI "functions" package (incompatible with Python 3).
import json
import os        # for file path operations
import runpy     # for executing another Python script
from dotenv import load_dotenv
import requests  # for HTTP requests
import sqlite3
from sentence_transformers import SentenceTransformer
from sqlite_vec import load as sqlite_vec_load, serialize_float32

# 0.2 Working Directory #################################

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__name__))
os.chdir(script_dir)

## 0.3 Start Ollama Server (source 01_ollama.py) #################################

# Execute 01_ollama.py as if we were sourcing it in R.
# This will configure environment variables and start `ollama serve` in the background.
ollama_script_path = os.path.join(os.getcwd(), "01_ollama.py")
_ = runpy.run_path(ollama_script_path)


# Load .env into environment if available (mirrors R readRenviron(".env"))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

## 0.2 Configuration ##########################

# Path to sqlite-vec extension is handled by sqlite_vec.load() in Python.
# To find the path for use in R, in git bash run:
# python -c "import sqlite_vec; print(sqlite_vec.loadable_path())"

DB_PATH = "data/embed.db"  # path to your new vector embeddings database
if os.path.exists(DB_PATH): os.remove(DB_PATH) 
else: print("No database found, creating new one.")
DOCUMENT = "data/lower_manhattan_recovery_plan.txt"  # path to text doc
EMBED_MODEL = "all-MiniLM-L6-v2"  # model for embedding text into vectors
VEC_DIM = 384   # all-MiniLM-L6-v2 output size
MODEL = "gpt-oss:20b-cloud"  # cloud model (Ollama Cloud; for RAG answer step)


# 1. FUNCTIONS ################################

# We're going to define a few helper functions to help us with the RAG workflow.

# Let's define our own custom agent_run function, since we're using Ollama Cloud.
# Expects an Ollama Cloud model name
def agent_run(role, task, model="gpt-oss:20b-cloud"):
    # Get API key from environment variable
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

    # Check if API key is set
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY not found in .env file. Please set it up first.")

    # Ollama Cloud API endpoint
    url = "https://ollama.com/api/chat"

    # Construct the request body
    body = {
        "model": model,  # Low-cost cloud model
        "messages": [
            {"role": "system", "content": role},
            {"role": "user", "content": task}
        ],
        "stream": False  # Non-streaming response
    }

    # Build and send the POST request to Ollama Cloud API
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        },
        json=body
    )
    response.raise_for_status()

    # Parse the response JSON
    data = response.json()

    # Extract the model's reply
    # Ollama chat API returns message content directly
    output = data["message"]["content"]
    return output


# We want to convert a given text sentence into a vector of numbers, called an 'embedding'
# These embeddings are then stored in a database and can be used to numerically search for the most relevant chunks for a given query.
# We'll use sentence-transformers to embed the text.
# Load sentence_transformers once; encode() returns a list of floats.

_embed_model = None

# Get the sentence-transformers model
def get_embed_model(model_name=None):
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model

# Encode the text into a vector of numbers
def embed(text):
    m = get_embed_model()
    vec = m.encode(text)
    return vec.tolist()  # numpy array -> list of floats

# Write a function to read in the document into meaningful text chunks.
def get_text(document_path):
    # Split the document into chunks
    with open(document_path, "r", encoding="UTF-8") as f:
        raw = f.read()
    # Concatenate the lines into a single string (already one string), split on period
    parts = raw.replace("\n", " ").split(".")
    # Trim whitespace and return only non-empty chunks
    chunks = [p.strip() for p in parts if p.strip()]
    return chunks

# Embed each chunk and insert into vec_chunks (float32 blob + text).
# R uses a single vec0 table with id, embedding, +text; Python sqlite_vec uses
# a vec0 virtual table (rowid, embedding) plus a chunks table (id, text) for compatibility.
def build_index_from_document(conn, chunks):
    # Given a database connection 'conn' and a list of text chunks 'chunks',
    # embed each chunk and insert into database (chunks table + vec_chunks virtual table).
    n = len(chunks)
    print(f"Embedding {n} chunks with {EMBED_MODEL}...")
    for i, text in enumerate(chunks):
        # Embed the chunk
        vec = embed(text)
        # Convert the vector to a float32 blob
        blob = serialize_float32(vec)
        # Insert the chunk into the chunks table
        conn.execute("INSERT INTO chunks (id, text) VALUES (?, ?)", (i, text))
        # Insert into vec_chunks (rowid aligns with chunks.id)
        conn.execute(
            "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
            (i, blob)
        )
    conn.commit()
    print("Index built.\n")


# SEMANTIC SEARCH

# Create a function to perform semantic search on the vector embeddings database,
# using the KNN search algorithm for similarity search with sqlite-vec.
# KNN runs inside the DB: embed query, MATCH in SQL, return top k. Score = 1 - distance (higher = more similar).
def search_embed_sql(conn, query, k=3):
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

# Connect and load sqlite-vec.
def connect_db(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec_load(conn)
    conn.enable_load_extension(False)
    return conn

# 2. SEMANTIC SEARCHWORKFLOW ################

print("--------------------------------")
print("🔍 SEMANTIC SEARCH WORKFLOW:")
print("--------------------------------")

# Finally, in this section, we'll put it all together and build the index from the document.

# Read in the document into meaningful chunks, where each chunk is a sentence.
chunks = get_text(DOCUMENT)
n = len(chunks)
print(f"Found {n} chunks in the document.")



conn = connect_db(DB_PATH)

# Create the chunks table and vec_chunks virtual table.
# vec0 virtual table: rowid, embedding (float32). Cosine distance for similarity search.
# We keep id and text in chunks so we can join after MATCH.
conn.execute("CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
conn.execute("DROP TABLE IF EXISTS vec_chunks")
conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[{VEC_DIM}] distance_metric=cosine)")
conn.commit()

# Construct the embedding database (takes longer for larger text documents)
n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
if n_chunks == 0:
    import time
    start = time.perf_counter()
    build_index_from_document(conn, chunks)
    elapsed = time.perf_counter() - start
    print(f"Time taken to build index: {elapsed:.2f} seconds\n")
else:
    print("Using existing embedding index.\n")
#
# conn.execute("SELECT * FROM chunks LIMIT 3;").fetchall()
# conn.execute("SELECT * FROM vec_chunks LIMIT 3;").fetchall()

print("--------------------------------")
print("🔍 PREVIEW VEC_CHUNKS TABLE:")
print("--------------------------------")

# Preview the vec_chunks table (we show chunks since vec_chunks is virtual)
preview = conn.execute("SELECT id, text FROM chunks LIMIT 5").fetchall()
for row in preview:
    print(row)

# Do a test search
test = search_embed_sql(conn, "vulnerability", k=3)

print("--------------------------------")
print("🔍 TEST SEARCH:")
print("--------------------------------")

print(test)

# Disconnect from the database
conn.close()

# 3. RAG WORKFLOW #############################

print("--------------------------------")
print("🔍 RAG WORKFLOW:")
print("--------------------------------")

# Reconnect to the database
conn = connect_db(DB_PATH)

# A real query from a user!
query = "Does the recovery plan use a community resilience approach to recovery?"
result1 = search_embed_sql(conn, query, k=3)
context = "\n\n".join(row["text"] for row in result1)
print(context)

role = (
    "You are a helpful assistant that answers questions about a community recovery plan. "
    "Answer the question provided by the user, using only the context provided by the user. "
    "Format your response as markdown with a title and clear bullet points. "
    "Content will be provided to the assistant in the following format: "
    "<user original query> | <context from vector database search>"
)

result2 = agent_run(role=role, task=f"{query} | {context}", model=MODEL)
print(result2)


print("--------------------------------")
print("🔍 FACT-CHECKING WORKFLOW:")
print("--------------------------------")

# Or, perhaps we rate the truthfulness of a statement..
role = (
    "You are an analyst tasked with performing fact-checking using content provided to you. "
    "System will provide you with a user query and a context from a vector database search. "
    "Your task is to: "
    "1) reframe the user query into a TRUE or FALSE statement, then "
    "2) answer the user query as TRUE or FALSE, then "
    "3) provide a 1-5 likert scale score for how true it is, "
    "where 1 = completely false, 2 = somewhat false, 3 = it's complicated, 4 = somewhat true, 5 = completely true "
    "Return your response as a valid JSON string in this exact format, with no extra ```json or formatting. "
    "{"
    "  \"query\": \"<user original query>\","
    "  \"reframed_query\": \"<reframed user query as a TRUE or FALSE statement>\","
    "  \"answer\": \"TRUE\" or \"FALSE\","
    "  \"score\": 1-5"
    "}"
)

# Execute the query...
result3 = agent_run(role=role, task=f"{query} | {context}", model=MODEL)
print(result3)
print(json.loads(result3))  # parse the JSON string!

# Disconnect from the database
conn.close()
