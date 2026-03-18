# 05_embed.R
# Semantic RAG with Embeddings (sentence-transformers via reticulate + SQLite)
# Pairs with 05_embed.py
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
# sqlite-vec (vec0), and run KNN search inside the database. Pairs with 05_embed.py.
# Requires sqlite-vec extension; set VEC_EXTENSION_PATH below.

# 0. SETUP ###################################

## 0.1 Load Packages ##########################

# Install R packages and python libraries
# install.packages(c("DBI", "RSQLite", "dplyr", "reticulate", "httr2", "jsonlite"))
# reticulate::py_install("sentence-transformers")
# reticulate::py_install("sqlite-vec")
# sentence-transformers will take a fair amount of space, fyi

# Load packages
library(DBI) # for database functions
library(RSQLite) # for SQLite db connections
library(dbplyr) # for dplyr-style database queries
library(dplyr) # for data wrangling
library(reticulate) # for loading python libraries in R
library(httr2)    # for HTTP requests
library(jsonlite) # for json operations
library(stringr) # for string operations
readRenviron(".env") # Read the .env file

# Check Python configuration
py_config()
# Install Python packages
py_require("sentence-transformers")
py_require("sqlite-vec")
# Check Python packages
py_list()

st = import("sentence_transformers")

## 0.2 Configuration ##########################

# Path to sqlite-vec extension. For example, mine was:
VEC_EXTENSION_PATH = "C:/Users/tmf77/AppData/Local/Programs/Python/Python312/Lib/site-packages/sqlite_vec/vec0"
# To find the path, in git bash run:
# python -c "import sqlite_vec; print(sqlite_vec.loadable_path())"

DB_PATH = "07_rag/data/embed.db" # path to your new vector embeddings database
if(file.exists(DB_PATH)) { unlink(DB_PATH, force = TRUE) }
DOCUMENT = "07_rag/data/lower_manhattan_recovery_plan.txt" # path to text doc
EMBED_MODEL = "all-MiniLM-L6-v2" # model for embedding text into vectors
VEC_DIM = 384L   # all-MiniLM-L6-v2 output size
MODEL = "gpt-oss:20b-cloud" # cloud model (Ollama Cloud; for RAG answer step)

# 1. FUNCTIONS ################################

# We're going to define a few helper functions to help us with the RAG workflow.

# Let's define our own custom agent_run function, using we're using Ollama Cloud.
# Expects an Ollama Cloud model name
agent_run = function(role, task, model = "gpt-oss:20b-cloud"){

  # Get API key from environment variable
  OLLAMA_API_KEY = Sys.getenv("OLLAMA_API_KEY")

  # Check if API key is set
  if (OLLAMA_API_KEY == "") { stop("OLLAMA_API_KEY not found in .env file. Please set it up first.") }

  # Ollama Cloud API endpoint
  url = "https://ollama.com/api/chat"

  # Construct the request body as a list
  body = list(
    model = model,  # Low-cost cloud model
    messages = list(
      list(role = "system", content = role),
      list(role = "user", content = task)
    ),
    stream = FALSE  # Non-streaming response
  )

  # Build and send the POST request to Ollama Cloud API
  res = request(url) %>%
    req_headers(
      "Authorization" = paste0("Bearer ", OLLAMA_API_KEY),
      "Content-Type" = "application/json"
    ) %>%
    req_body_json(body) %>%   # Attach the JSON body
    req_method("POST") %>%   # Set HTTP method
    req_perform()             # Execute the request

  # Parse the response JSON
  response = resp_body_json(res)

  # Extract the model's reply
  # Ollama chat API returns message content directly
  output = response$message$content
  return(output)

}


# We want to convert a given text sentence into a vector of numbers, called an 'embedding'
# These embeddings are then stored in a database and can be used to numerically search for the most relevant chunks for a given query.
# We'll use sentence-transformers to embed the text.
# Load sentence_transformers once; encode() returns a numpy array, we coerce to R numeric.

# Get the sentence-transformers model
get_embed_model = function(.model = NULL) {
  if (is.null(.model)) .model <<- st$SentenceTransformer(EMBED_MODEL)
  .model
}
# Encode the text into a vector of numbers
embed = function(text) {
  m = get_embed_model()
  vec = m$encode(text)
  as.vector(vec)   # numpy array -> R numeric
}

# Float32 blob for sqlite-vec (4 bytes per element).
vec_embedding_to_blob = function(vec) {
  writeBin(as.numeric(vec), raw(), size = 4)
}
# JSON string for the MATCH ? placeholder in KNN queries.
vec_embedding_to_json = function(vec) {
  paste0("[", paste(as.numeric(vec), collapse = ","), "]")
}


# Write a function to read in the document into meaningful text chunks.
get_text = function(DOCUMENT){
  # Split the document into chunks
  DOCUMENT %>%
    # Read the document into lines
    readLines(encoding = "UTF-8") %>% 
    # Concatenate the lines into a single string
    paste0(collapse = " ") %>% 
    # Split the document into chunks anytime there is a period
    str_split("\\.") %>% unlist() %>%
    # Trim whitespace
    str_trim() %>%
    # Return only non-empty chunks
    {.[. != ""]}
}

# Embed each chunk and insert into vec_chunks (float32 blob + text).
build_index_from_document = function(conn, chunks) {
  # Given a database connection 'conn' and a vector of text chunks 'chunks',
  # embed each chunk and insert into database table vec_chunks (float32 blob + text).
  n = length(chunks)
  message("Embedding ", n, " chunks with ", EMBED_MODEL, "...")
  for (i in seq_len(n)) {
    # Get the i-th chunk
    text = chunks[[i]]
    # Embed the chunk
    vec = embed(text)
    # Convert the vector to a float32 blob
    blob = vec_embedding_to_blob(vec)
    # Insert the chunk into the database
    dbExecute(conn, "INSERT INTO vec_chunks (id, embedding, text) VALUES (?, ?, ?)",
              params = list(i - 1L, list(blob), text))
  }
  message("Index built.\n")
}


# SEMANTIC SEARCH

# Create a function to perform semantic search on the vector embeddings database,
# using the KNN search algorithm for similarity search with sqlite-vec.
# KNN runs inside the DB: embed query, MATCH in SQL, return top k. Score = 1 - distance (higher = more similar).
search_embed_sql = function(conn, query, k = 3) {
  query_vec = embed(query)
  query_json = vec_embedding_to_json(query_vec)
  out = dbGetQuery(conn,
    "SELECT id, text, distance FROM vec_chunks WHERE embedding MATCH ? AND k = ?",
    params = list(query_json, k))
  if (nrow(out) == 0) return(out)
  out$score = 1 - out$distance
  result = out %>% select(id, score, text)
  result = result %>% as_tibble()
  return(result)
}

# 2. WORKFLOW ################

# Finally, in this section, we'll put it all together and build the index from the document.

# Read in the document into meaningful chunks, where each chunk is a sentence.
chunks = get_text(DOCUMENT)
n = length(chunks)
message("Found ", n, " chunks in the document.")


# Connect and load sqlite-vec. If path not set, try pip-installed sqlite_vec (reticulate).
conn = dbConnect(RSQLite::SQLite(), DB_PATH)

# If you need to start over, disconnect from the database and remove the database file
# dbDisconnect(conn)
# unlink(DB_PATH, force = TRUE)

# Load the SQLite-vec extension, in order to use vector search
dbExecute(conn, sprintf("SELECT load_extension(%s)", dbQuoteString(conn, VEC_EXTENSION_PATH)))

# Create the vec_chunks table
# vec0 virtual table: id, embedding (float32), +text. Cosine distance for similarity search.
dbExecute(conn, sprintf("
  CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    id INTEGER PRIMARY KEY,
    embedding float[%d] distance_metric=cosine,
    +text TEXT
  )
", VEC_DIM))

# Construct the embedding database (takes longer for larger text documents)
n_chunks = dbGetQuery(conn, "SELECT COUNT(*) AS n FROM vec_chunks")$n
if (n_chunks == 0) {
  time = system.time(build_index_from_document(conn, chunks))
  message("Time taken to build index: ", time[["elapsed"]], " seconds\n")
} else {
  message("Using existing embedding index.\n")
}

# Preview the vec_chunks table
conn %>% tbl("vec_chunks")


# Do a test search
test = search_embed_sql(conn, "vulnerability", k = 3)

print("--------------------------------")
print("🔍 TEST SEARCH:")
print("--------------------------------")

print(test)

# Disconnect from the database
dbDisconnect(conn)

# 3. RAG WORKFLOW #############################

# Reconnect to the database
conn = dbConnect(RSQLite::SQLite(), DB_PATH)
# Load the SQLite-vec extension, in order to use vector search
dbExecute(conn, sprintf("SELECT load_extension(%s)", dbQuoteString(conn, VEC_EXTENSION_PATH)))

# A real query from a user!
query = "Does the recovery plan use a community resilience approach to recovery?"
result1 = search_embed_sql(conn, query, k = 3)
context = paste(result1$text, collapse = "\n\n")
context

role = paste(
  "You are a helpful assistant that answers questions about a community recovery plan. ",
  "Answer the question provided by the user, using only the context provided by the user. ",
  "Format your response as markdown with a title and clear bullet points. ",
  "Content will be provided to the assistant in the following format: ",
  "<user original query> | <context from vector database search>"
)

result2 = agent_run(role = role, task = paste0(query, " | ", context), model = MODEL)




# Or, perhaps we rate the truthfulness of a statement..
role = paste(
   "You are an analyst tasked with performing fact-checking using content provided to you. ",
   "System will provide you with a user query and a context from a vector database search. ",
   "Your task is to: ",
   "1) reframe the user query into a TRUE or FALSE statement, then ",
   "2) answer the user query as TRUE or FALSE, then ",
   "3) provide a 1-5 likert scale score for how true it is, ",
   "where 1 = completely false, 2 = somewhat false, 3 = it's complicated, 4 = somewhat true, 5 = completely true ",
   "Return your response as a valid JSON string in this exact format, with no extra ```json or formatting. ",
   "{",
   "  \"query\": \"<user original query>\",",
   " \"reframed_query\": \"<reframed user query as a TRUE or FALSE statement>\",",
   "  \"answer\": \"TRUE\" or \"FALSE\",",
   "  \"score\": 1-5",
   "}"
)

# Execute the query...
result3 = agent_run(role = role, task = paste0(query, " | ", context), model = MODEL)
result3
result3 %>% fromJSON() # parse the JSON string!

# Disconnect from the database
dbDisconnect(conn)
