import asyncio
import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agent_service import get_agent_service


async def main():
    agent = get_agent_service()
    queries = [
        "What courses does Sunbeam offer?",
        "Compare Core Java and C++.",
        "What are the internship eligibility requirements?",
        "Explain Python decorators in 2 sentences.",
        "Where is the Hinjawadi campus located?",
        "What are the fees for Core Java?",
        "What is the duration of the Generative AI internship?",
        "Can I take courses in online mode?",
        "What facilities are available at the Sunbeam campus?",
        "Tell me about Apache Spark course prerequisites.",
    ]

    print("=" * 70)
    print("RUNNING 10 DIVERSE REALISTIC QUERIES ON SUNBEAM AGENTIC RAG SYSTEM")
    print("=" * 70)

    for i, q in enumerate(queries, 1):
        print(f"\n[QUERY {i}/10]: \"{q}\"")
        try:
            res = await agent.execute(q)
            print(f"  • Intent: {res.intent}")
            print(f"  • Requires RAG: {res.requires_rag}")
            print(f"  • Tools Executed: {res.tools_used}")
            print(f"  • Sources: {res.sources}")
            print(f"  • Latency: {res.execution_time_ms} ms")
            print(f"  • Response Preview: {res.response[:140]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 70)
    print("ALL 10 AGENT QUERIES COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
