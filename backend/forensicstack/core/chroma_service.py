"""
ChromaDB wrapper for semantic search over forensic Findings.

After each analysis completes, the normalised Finding objects are vectorised
and stored here. Investigators can then search across ALL cases using natural
language queries (e.g. "process injecting into lsass", "suspicious registry run key").

ChromaDB uses the default all-MiniLM-L6-v2 sentence-transformer model for
embedding — no external API key required, runs fully locally.
"""
import json
import os
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "findings"


class ChromaService:
    """Thin wrapper around the ChromaDB HTTP client."""

    def __init__(self):
        self._client = None
        self._collection = None

    def _get_client(self):
        """Lazily connect to ChromaDB so that import-time failures don't break the API."""
        if self._client is None:
            import chromadb
            self._client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"[ChromaDB] Connected at {CHROMA_HOST}:{CHROMA_PORT}, collection='{COLLECTION_NAME}'")
        return self._client, self._collection

    # ── Indexing ───────────────────────────────────────────────────────────────

    def add_findings(self, findings: list, artifact_id: int, case_id: int):
        """
        Vectorise and store a list of Finding dataclass instances.

        Each finding becomes one ChromaDB document. The text representation is
        a JSON-serialisable concatenation of tool + artifact_type + data so that
        semantic search picks up specific field values.

        Args:
            findings:    List of Finding dataclasses (from normalizers)
            artifact_id: DB artifact ID (stored as metadata)
            case_id:     DB case ID (stored as metadata for filtering)
        """
        if not findings:
            return

        try:
            _, collection = self._get_client()

            documents = []
            metadatas = []
            ids = []

            for idx, f in enumerate(findings):
                # Build searchable text
                data_str = json.dumps(f.data, ensure_ascii=False, default=str)
                text = f"{f.tool} {f.artifact_type} {f.source or ''} {data_str}"

                documents.append(text[:4096])  # ChromaDB default max token safety
                metadatas.append({
                    "tool": f.tool,
                    "artifact_type": f.artifact_type,
                    "source": f.source or "",
                    "timestamp": f.timestamp or "",
                    "confidence": float(f.confidence),
                    "artifact_id": artifact_id,
                    "case_id": case_id,
                    "data_json": data_str[:2048],  # truncated snapshot for retrieval
                })
                ids.append(f"art{artifact_id}_{f.tool}_{idx}")

            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                collection.upsert(
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size],
                    ids=ids[i:i + batch_size],
                )

            print(f"[ChromaDB] Indexed {len(documents)} findings for artifact {artifact_id}")

        except Exception as e:
            # Never crash an analysis because ChromaDB is unavailable
            print(f"[ChromaDB] WARNING: Could not index findings: {e}")

    # ── Search ─────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n_results: int = 10,
        case_id: Optional[int] = None,
        tool: Optional[str] = None,
    ) -> List[dict]:
        """
        Perform a semantic similarity search over all indexed findings.

        Args:
            query:     Natural language query string
            n_results: Maximum number of results to return
            case_id:   If set, restrict results to this case
            tool:      If set, restrict results to this tool

        Returns:
            List of dicts with keys: score, tool, artifact_type, source,
            timestamp, artifact_id, case_id, confidence, data
        """
        try:
            _, collection = self._get_client()

            # Build where filter
            where = {}
            if case_id is not None and tool is not None:
                where = {"$and": [{"case_id": case_id}, {"tool": tool}]}
            elif case_id is not None:
                where = {"case_id": case_id}
            elif tool is not None:
                where = {"tool": tool}

            query_kwargs = {
                "query_texts": [query],
                "n_results": min(n_results, collection.count() or 1),
            }
            if where:
                query_kwargs["where"] = where

            results = collection.query(**query_kwargs)

            hits = []
            if not results or not results.get("ids"):
                return hits

            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = max(0.0, 1.0 - distance)   # cosine: distance 0 = identical

                # Deserialise stored data snapshot
                try:
                    data = json.loads(meta.get("data_json", "{}"))
                except Exception:
                    data = {}

                hits.append({
                    "score": round(score, 4),
                    "tool": meta.get("tool", ""),
                    "artifact_type": meta.get("artifact_type", ""),
                    "source": meta.get("source"),
                    "timestamp": meta.get("timestamp") or None,
                    "artifact_id": int(meta.get("artifact_id", 0)),
                    "case_id": int(meta.get("case_id", 0)),
                    "confidence": float(meta.get("confidence", 0)),
                    "data": data,
                })

            # Sort by score descending
            hits.sort(key=lambda x: x["score"], reverse=True)
            return hits

        except Exception as e:
            print(f"[ChromaDB] WARNING: Search failed: {e}")
            return []

    # ── Deletion ───────────────────────────────────────────────────────────────

    def delete_by_artifact(self, artifact_id: int):
        """Remove all findings belonging to a given artifact."""
        try:
            _, collection = self._get_client()
            collection.delete(where={"artifact_id": artifact_id})
            print(f"[ChromaDB] Deleted findings for artifact {artifact_id}")
        except Exception as e:
            print(f"[ChromaDB] WARNING: Could not delete findings for artifact {artifact_id}: {e}")

    def get_stats(self) -> dict:
        """Return basic collection statistics."""
        try:
            _, collection = self._get_client()
            return {"collection": COLLECTION_NAME, "total_findings": collection.count()}
        except Exception as e:
            return {"error": str(e)}


# Singleton
_chroma_service: Optional[ChromaService] = None


def get_chroma_service() -> ChromaService:
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaService()
    return _chroma_service
