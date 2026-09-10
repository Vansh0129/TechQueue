"""
TechQueue Interview Coach — Main Flow Test Script

Run this script to compile and test the interview prep flow locally.

Usage:
    export PYTHONPATH=/path/to/adk/src:/path/to/adk
    python3 main_flow.py
"""

import asyncio
import io
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from techqueue_interview_coach.tools.interview_prep_flow import build_interview_prep_flow


async def main() -> None:
    """Compile and test the interview prep flow locally."""
    print("=" * 60)
    print("TechQueue Interview Coach - Flow Test")
    print("=" * 60)

    # 1. Compile locally and save the spec
    model = build_interview_prep_flow.func(build_interview_prep_flow.a_model)
    compiled_flow = model.compile()

    generated_folder = Path(__file__).resolve().parent / "generated"
    generated_folder.mkdir(exist_ok=True)
    out_spec = generated_folder / "interview_prep_flow.json"
    compiled_flow.dump_spec(str(out_spec))
    print(f"[OK] Flow compiled successfully! Spec saved to: {out_spec}")

    # 2. Test invocation with a sample candidate profile
    test_input = {
        "name": "Jordan Lee",
        "job_role": "Software Engineer",
        "experience_level": "mid",
        "tech_stack": "Python, Django, PostgreSQL, AWS",
        "resume_summary": (
            "3 years building backend APIs at a fintech startup; "
            "led migration of monolith to microservices; "
            "passionate about clean code and system design."
        ),
    }

    print("\nTest candidate profile:")
    for k, v in test_input.items():
        print(f"  {k}: {v}")

    # Test the profile enrichment node
    from techqueue_interview_coach.tools.interview_prep_flow import parse_candidate_profile
    parsed = parse_candidate_profile(
        name=test_input["name"],
        job_role=test_input["job_role"],
        experience_level=test_input["experience_level"],
        tech_stack=test_input["tech_stack"],
        resume_summary=test_input["resume_summary"],
    )
    print("\n[OK] Parsed Candidate Context:")
    print(f"  {parsed.content}")

    # 3. Attempt live deployment if Orchestrate server is active
    try:
        flow_def = await build_interview_prep_flow.compile_deploy()
        print("\nInvoking deployed interview prep flow on Orchestrate ...\n")
        result = await flow_def.invoke(test_input, debug=True)
        print("\n--- Live Flow Output ---")
        print(result)
    except Exception as e:
        print(f"\n[INFO] Live Orchestrate deployment skipped ({e}).")
        print("       For local dev with Ollama, run: python dev_server.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
