from Embeddings.Embeddingmaker import embedder 
from functools import lru_cache
from pathlib import Path
BASE_DIR=Path("Data").resolve()
import asyncio

from langchain_community.vectorstores import FAISS


class SemanticQuery:
    def __init__(self):
        pass
    @staticmethod
    @lru_cache(maxsize=32)
    def load_vectorstore(path: str):
        return FAISS.load_local(
            path,
            embedder,
            allow_dangerous_deserialization=True,
        )
    
    def load_and_search(self, path: str, query: str, k: int = 6):
        vectorstore = self.load_vectorstore(path)
        return vectorstore.similarity_search_with_score(query, k=6)
    
    async def get_semantic_chunks_fromFeed(self,query:str,uuids:list[str],top_k:int=5):
        result=[]
        paths=[]
        for uuid in uuids:
            feed_path=f"{BASE_DIR}/Feed/{uuid}"
            pathexsistence=Path(feed_path)
            if pathexsistence.exists()!=True :
                continue
            paths.append(feed_path)
        tasks=[asyncio.to_thread(self.load_and_search,path,query) for path in paths]
        all_result=await asyncio.gather(*tasks)
        for chunks in all_result:
            result.extend(chunks)
        if(len(result)>6):
            result.sort(key=lambda x: x[1],reverse=True)
        return result[:top_k]
    async def get_semantic_chunks_fromContent(self,query:str,uuids:list[str],top_k:int=5):
        result=[]
        paths=[]
        for uuid in uuids:
            content_path=f"{BASE_DIR}/Content/{uuid}"
            pathexsistence=Path(content_path)
            if pathexsistence.exists()!=True :
                continue
            paths.append(content_path)
        tasks=[asyncio.to_thread(self.load_and_search,path,query) for path in paths]
        all_result=await asyncio.gather(*tasks)
        for chunks in all_result:
            result.extend(chunks)
        if(len(result)>6):
            result.sort(key=lambda x: x[1],reverse=True)
        return result[:top_k]
    

        