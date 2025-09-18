from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
load_dotenv()

VECTOR_INDEX_NAME = "doc_embedding_index"
FULLTEXT_INDEX_NAME = "doc_fulltext"
NEO4J_URI=os.getenv("NEO4J_URL","bolt://localhost:7687")
NEO4J_USER=os.getenv("NEO4J_USER","neo4j")
NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD","asdfghjk")
class Neo4JStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()


    @staticmethod
    def ensure_schema():
        """
        create the unique id constraint, and wait for indexes to be online.
        """
        driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        with driver.session() as s:
            s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Doc) REQUIRE d.id IS UNIQUE")
            s.run(f"""
            CREATE FULLTEXT INDEX {FULLTEXT_INDEX_NAME} IF NOT EXISTS
            FOR (d:Doc) ON EACH [d.title, d.text]
            """)
            s.run("CALL db.awaitIndexes()")
        driver.close()

    def _get_vector_index_dim(self) -> Optional[int]:
        """
        return existing vector index dimension if present, else None.
        """
        with self.driver.session() as s:
            rec = s.run(f"""
            SHOW INDEXES YIELD name, type, properties
            WHERE name = $name
            RETURN name, type, properties
            """, name=VECTOR_INDEX_NAME).single()
            if not rec:
                return None
            props = rec["properties"] or {}
            return None

    def _ensure_vector_index(self, dim: int):
        """
        create the vector index once with the provided dimension.
        if an index already exists with a different dimension, raise an error.
        """
        with self.driver.session() as s:
            s.run(f"""
            CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
            FOR (d:Doc) ON (d.embedding)
            OPTIONS {{
              indexConfig: {{
                `vector.dimensions`: {dim},
                `vector.similarity_function`: 'cosine'
              }}
            }}
            """)
            s.run("CALL db.awaitIndexes()")




    def upsert_doc(self, d: Dict[str, Any]):
        """
        Upsert a document node; ensures the vector index exists before writing the first embedding.
        """
        dim = len(d.get("embedding", []) or [])
        if dim:
            self._ensure_vector_index(dim)

        q = """
        MERGE (x:Doc {id:$id})
        SET x.title=$title,
            x.url=$url,
            x.text=$text,
            x.embedding=$embedding
        RETURN x
        """
        with self.driver.session() as s:
            s.run(q, **d)





    def vector_search(self, q_emb: List[float], top_k: int) -> List[Dict]:
        cypher = f"""
        WITH $q AS queryVec
        CALL db.index.vector.queryNodes('{VECTOR_INDEX_NAME}', {top_k}, queryVec)
        YIELD node, score
        RETURN node.id AS id, node.title AS title, node.url AS url, node.text AS text, score
        """
        with self.driver.session() as s:
            return [r.data() for r in s.run(cypher, q=q_emb)]

    def fulltext_search(self, query: str, top_k: int) -> List[Dict]:
        cypher = f"""
        CALL db.index.fulltext.queryNodes('{FULLTEXT_INDEX_NAME}', $q, {{limit:$k}})
        YIELD node, score
        RETURN node.id AS id, node.title AS title, node.url AS url, node.text AS text, score
        """
        with self.driver.session() as s:
            return [r.data() for r in s.run(cypher, q=query, k=top_k)]

def ensure_schema():
    Neo4JStore.ensure_schema()
