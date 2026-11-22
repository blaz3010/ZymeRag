import torch
torch.set_num_threads(1)
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from Backend.Utils.Logger import logger

class Embedder(Embeddings):

    def __init__(self, model_name="Qwen/Qwen3-Embedding-0.6B"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, chunks):
        logger.info(f"Embedding {len(chunks)} documents using model {self.model.__class__.__name__}")
        return self.model.encode(
            chunks,
            normalize_embeddings=True,
            show_progress_bar=True
        ).astype("float32").tolist()

    def embed_query(self, query):
        logger.info(f"Embedding query using model {self.model.__class__.__name__}")
        return self.model.encode(
            query,
            normalize_embeddings=True
        ).astype("float32").tolist()

embedder=Embedder()