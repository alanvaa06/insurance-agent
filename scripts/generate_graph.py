"""Render the compiled LangGraph workflow to graph.png.

Run manually (it needs network access for Mermaid rendering); it is intentionally
not executed on import.

    python scripts/generate_graph.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.graph import create_claims_processing_graph  # noqa: E402


def main() -> None:
    graph = create_claims_processing_graph()
    png_bytes = graph.get_graph().draw_mermaid_png()
    out = Path("graph.png")
    out.write_bytes(png_bytes)
    print(f"Wrote {out.resolve()} ({len(png_bytes)} bytes)")


if __name__ == "__main__":
    main()
