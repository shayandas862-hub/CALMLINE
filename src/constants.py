"""The embedding contract — defined once, read everywhere.

The vendored RAG pipeline hardcoded these in two separate files; CalmLine
centralises them. The migration's vector dimension, the corpus embedder, and
the query path all read from here, so a model change is a one-line edit.
"""

# OpenAI embedding model shared with the vendored pipeline (1536 dimensions,
# cosine distance). Changing the model means changing the dimension AND
# re-embedding the corpus — never change one without the others.
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# Asymmetric prefixes: documents are embedded as "passage: ...", queries as
# "query: ...". Retrieval quality depends on both sides using these exactly.
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "
