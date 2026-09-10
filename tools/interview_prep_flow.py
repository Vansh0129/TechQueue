"""
TechQueue Interview Coach — Interview Preparation Flow

Orchestrates the full interview prep pipeline:
  1. Collect candidate profile
  2. Build personalised focus areas
  3. Generate tailored question set via LLM + knowledge base
  4. Deliver structured prep plan
"""

from pydantic import BaseModel, Field
from typing import List, Optional

from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# ---------------------------------------------------------------------------
# Flow input / output schemas
# ---------------------------------------------------------------------------

class InterviewPrepFlowInput(BaseModel):
    """Input for the full interview prep flow."""
    name: str = Field(..., description="Candidate's full name")
    job_role: str = Field(
        ...,
        description="Target job role, e.g. 'Software Engineer', 'Data Scientist'"
    )
    experience_level: str = Field(
        ...,
        description="Experience level: 'entry', 'mid', or 'senior'"
    )
    tech_stack: Optional[str] = Field(
        default=None,
        description="Comma-separated list of technologies, e.g. 'Python, React, AWS'"
    )
    resume_summary: Optional[str] = Field(
        default=None,
        description="Brief resume summary or career highlights"
    )


class InterviewPrepFlowOutput(BaseModel):
    """Final structured output of the interview prep flow."""
    candidate_name: str = Field(default="", description="Candidate's name")
    job_role: str = Field(default="", description="Target job role")
    experience_level: str = Field(default="", description="Experience level")
    preparation_plan: str = Field(default="", description="Full personalised interview preparation plan")
    question_preview: str = Field(default="", description="Preview of key questions to practise")
    next_steps: str = Field(default="", description="Concrete next steps for the candidate")


# ---------------------------------------------------------------------------
# Helper tool (self-contained — no cross-file imports)
# ---------------------------------------------------------------------------

class PrepInput(BaseModel):
    """Parsed prep context forwarded to the LLM prompt node."""
    name: str = Field(description="Candidate name")
    job_role: str = Field(description="Target job role")
    experience_level: str = Field(description="Experience level")
    focus_areas: str = Field(description="Comma-separated focus areas")
    question_types: str = Field(description="Comma-separated question types")
    tip: str = Field(description="Personalised preparation tip")
    tech_stack: str = Field(description="Tech stack string")


@tool(permission=ToolPermission.READ_ONLY)
def parse_candidate_profile(
    name: str,
    job_role: str,
    experience_level: str,
    tech_stack: Optional[str] = None,
    resume_summary: Optional[str] = None,
) -> PrepInput:
    """
    Parse and enrich the raw candidate input into a structured prep context.

    Derives focus areas and recommended question types based on the job role
    and experience level, producing a clean context object for LLM prompt nodes.

    Args:
        name (str): Candidate's full name.
        job_role (str): Target job role.
        experience_level (str): Experience level: 'entry', 'mid', or 'senior'.
        tech_stack (str, optional): Comma-separated list of technologies.
        resume_summary (str, optional): Brief resume summary or career highlights.

    Returns:
        PrepInput: Enriched preparation context ready for LLM generation.
    """
    level = experience_level.lower().strip()
    if level not in ("entry", "mid", "senior"):
        level = "mid"

    role_lower = job_role.lower()
    focus_areas = []
    question_types = ["behavioral", "hr"]

    if any(k in role_lower for k in ("software", "engineer", "developer", "swe", "backend", "frontend", "fullstack")):
        focus_areas += ["Data Structures & Algorithms", "System Design", "Code Quality", "SOLID Principles"]
        question_types += ["technical", "system_design"]
    if any(k in role_lower for k in ("data", "scientist", "ml", "machine learning", "ai")):
        focus_areas += ["Statistics", "ML Model Evaluation", "Data Wrangling", "Experiment Design"]
        question_types += ["technical", "case_study"]
    if any(k in role_lower for k in ("product", "manager", "pm")):
        focus_areas += ["Product Strategy", "Prioritisation", "Stakeholder Management", "Metrics"]
        question_types += ["case_study", "situational"]
    if any(k in role_lower for k in ("devops", "cloud", "sre", "platform", "infra")):
        focus_areas += ["CI/CD", "Cloud Architecture", "Reliability", "Incident Response"]
        question_types += ["technical", "system_design"]

    if not focus_areas:
        focus_areas = ["Domain Expertise", "Communication", "Problem Solving"]

    tips = {
        "entry": "Focus on core fundamentals and walk through your academic projects clearly.",
        "mid": "Prepare STAR-format stories from real projects and be ready to discuss trade-offs.",
        "senior": "Lead with impact and system-level thinking; show how you influence architecture and teams.",
    }

    tech = tech_stack or "Not specified"

    return PrepInput(
        name=name,
        job_role=job_role,
        experience_level=level,
        focus_areas=", ".join(list(dict.fromkeys(focus_areas))),
        question_types=", ".join(list(dict.fromkeys(question_types))),
        tip=tips[level],
        tech_stack=tech,
    )


# ---------------------------------------------------------------------------
# Flow definition
# ---------------------------------------------------------------------------

@flow(
    name="interview_prep_flow",
    display_name="TechQueue Interview Prep Flow",
    description=(
        "Generates a personalised interview preparation plan for a candidate "
        "based on their profile, job role, and experience level using RAG from "
        "the interview knowledge base."
    ),
    input_schema=InterviewPrepFlowInput,
)
def build_interview_prep_flow(aflow: Flow) -> Flow:
    """
    Full interview preparation orchestration flow.

    Steps:
      1. parse_candidate_profile tool → enrich raw input into structured context
      2. LLM prompt node → generate comprehensive prep plan using knowledge base RAG
    """
    # Step 1: Parse and enrich candidate profile
    profile_node = aflow.tool(parse_candidate_profile)

    # Step 2: LLM generates personalised prep plan
    prep_plan_node = aflow.prompt(
        name="generate_prep_plan",
        system_prompt=(
            "You are TechQueue, an expert AI Interview Coach powered by RAG. "
            "You have access to a comprehensive knowledge base of role-specific interview questions, "
            "behavioral frameworks, system design guides, HR expectations, and model answers. "
            "Your job is to create a thorough, personalised interview preparation plan. "
            "Always use the knowledge base to retrieve the most relevant and up-to-date questions. "
            "Structure your output with clear sections: "
            "1) Welcome & Profile Summary, "
            "2) Key Focus Areas, "
            "3) Recommended Question Set (with 3–5 questions per category), "
            "4) Preparation Strategy & Tips, "
            "5) Next Steps & Resources. "
            "Be specific, actionable, and encouraging."
        ),
        user_prompt=(
            "Generate a comprehensive interview preparation plan for the following candidate:\n\n"
            "Name: {name}\n"
            "Target Role: {job_role}\n"
            "Experience Level: {experience_level}\n"
            "Tech Stack: {tech_stack}\n"
            "Focus Areas: {focus_areas}\n"
            "Recommended Question Types: {question_types}\n"
            "Personalised Tip: {tip}\n\n"
            "Please search the knowledge base for the most relevant questions and preparation "
            "strategies for this specific role and level. Include both technical and soft-skill "
            "questions, model answer outlines, and concrete next steps."
        ),
        llm="ibm/granite-3-3-8b-instruct",
        input_schema=PrepInput,
        output_schema=InterviewPrepFlowOutput,
    )

    aflow.sequence(START, profile_node, prep_plan_node, END)
    return aflow
