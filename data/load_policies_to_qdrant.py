# data/load_policies_to_qdrant.py
import re
from pathlib import Path
from datetime import date
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding

POLICIES_DIR = Path(__file__).parent / "policies"
COLLECTION = "policies"
FILENAME_RE = re.compile(r"^(?P<name>[a-z_]+)__v(?P<version>\d+)__(?P<date>\d{4}-\d{2}-\d{2})\.md$")


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars and current:
            chunks.append(current)
            current = ""
        current += ("\n\n" if current else "") + p
    if current:
        chunks.append(current)
    return chunks


def main():
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    client = QdrantClient(url="http://localhost:6333")

    sample_dim = len(list(model.embed(["dim probe"]))[0])
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=sample_dim, distance=Distance.COSINE),
    )

    points, point_id = [], 0
    for path in sorted(POLICIES_DIR.glob("*.md")):
        m = FILENAME_RE.match(path.name)
        if not m:
            raise ValueError(f"Filename doesn't match policy naming convention: {path.name}")
        policy_name, version, effective_date = m["name"], int(m["version"]), m["date"]

        chunks = chunk_text(path.read_text())
        vectors = list(model.embed(chunks))
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            points.append(PointStruct(
                id=point_id,
                vector=vec.tolist(),
                payload={
                    "policy_name": policy_name, "version": version,
                    "effective_date": effective_date, "chunk_index": i, "text": chunk,
                },
            ))
            point_id += 1

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Loaded {len(points)} chunks from {len(list(POLICIES_DIR.glob('*.md')))} policy files.")


if __name__ == "__main__":
    main()