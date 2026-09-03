# scripts/export_langsmith_traces.py
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client

def main():
    client = Client()
    runs = client.runs.query(project_name=os.environ["LANGSMITH_PROJECT"], is_root=True)
    exported = [{
        "id": str(r.id), "name": r.name, "start_time": str(r.start_time),
        "status": r.status,
    } for r in runs]
    out = Path("data/generated/held_out/langsmith_traces_export.json")
    out.write_text(json.dumps(exported, indent=2, default=str))
    print(f"Exported {len(exported)} root runs to {out}")

if __name__ == "__main__":
    main()