"""
TechQueue Interview Coach — Profile & Question Generation Tools

Handles candidate profile intake, experience-level classification,
and structured question set generation for technical + behavioral interviews.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CandidateProfile(BaseModel):
    """Input schema for capturing a candidate's interview profile."""
    name: str = Field(..., description="Full name of the candidate")
    job_role: str = Field(
        ...,
        description=(
            "Target job role, e.g. 'Software Engineer', 'Data Scientist', "
            "'Product Manager', 'DevOps Engineer'"
        )
    )
    experience_level: str = Field(
        ...,
        description="Experience level: 'entry', 'mid', or 'senior'"
    )
    tech_stack: Optional[List[str]] = Field(
        default=None,
        description="List of primary technologies/languages, e.g. ['Python', 'React', 'AWS']"
    )
    resume_summary: Optional[str] = Field(
        default=None,
        description="Short summary of the candidate's resume or career highlights"
    )


class ProfileSummary(BaseModel):
    """Structured candidate profile confirmation."""
    name: str = Field(description="Candidate name")
    job_role: str = Field(description="Target job role")
    experience_level: str = Field(description="Normalised experience level")
    focus_areas: List[str] = Field(description="Key focus areas derived from the profile")
    recommended_question_types: List[str] = Field(
        description="Recommended interview question categories"
    )
    preparation_tip: str = Field(description="Personalised quick-start tip for the candidate")


class QuestionSetRequest(BaseModel):
    """Request schema for generating a tailored question set."""
    job_role: str = Field(..., description="Target job role")
    experience_level: str = Field(
        ..., description="Experience level: 'entry', 'mid', or 'senior'"
    )
    question_types: List[str] = Field(
        ...,
        description=(
            "Types of questions to include, e.g. "
            "['technical', 'behavioral', 'system_design', 'hr']"
        )
    )
    count_per_type: int = Field(
        default=5,
        description="Number of questions per question type (1–10)"
    )


class InterviewQuestion(BaseModel):
    """A single interview question with metadata."""
    question_type: str = Field(description="Category: technical / behavioral / system_design / hr")
    question: str = Field(description="The interview question text")
    difficulty: str = Field(description="Difficulty: easy / medium / hard")
    hint: Optional[str] = Field(default=None, description="Optional hint or approach pointer")


class QuestionSet(BaseModel):
    """A complete tailored question set for the candidate."""
    job_role: str = Field(description="Target job role")
    experience_level: str = Field(description="Experience level")
    total_questions: int = Field(description="Total number of questions generated")
    questions: List[InterviewQuestion] = Field(description="List of interview questions")
    estimated_duration_minutes: int = Field(
        description="Estimated time to practise all questions"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def build_candidate_profile(profile: CandidateProfile) -> ProfileSummary:
    """
    Build and validate a structured candidate profile for personalised interview prep.

    Args:
        profile (CandidateProfile): The candidate's basic info, role, and experience.

    Returns:
        ProfileSummary: A structured summary with focus areas and preparation tips.
    """
    level = profile.experience_level.lower().strip()
    if level not in ("entry", "mid", "senior"):
        level = "mid"

    role_lower = profile.job_role.lower()

    # Derive focus areas based on role & level
    focus_areas: List[str] = []
    recommended_types: List[str] = ["behavioral", "hr"]

    if any(k in role_lower for k in ("software", "engineer", "developer", "swe", "backend", "frontend", "fullstack")):
        focus_areas += ["Data Structures & Algorithms", "System Design", "Code Quality"]
        recommended_types += ["technical", "system_design"]
    if any(k in role_lower for k in ("data", "scientist", "ml", "machine learning", "ai")):
        focus_areas += ["Statistics & ML Theory", "Model Evaluation", "Data Wrangling"]
        recommended_types += ["technical", "case_study"]
    if any(k in role_lower for k in ("product", "manager", "pm")):
        focus_areas += ["Product Strategy", "Prioritisation Frameworks", "Stakeholder Management"]
        recommended_types += ["case_study", "situational"]
    if any(k in role_lower for k in ("devops", "cloud", "infra", "sre", "platform")):
        focus_areas += ["CI/CD Pipelines", "Cloud Architecture", "Incident Management"]
        recommended_types += ["technical", "system_design"]

    if profile.tech_stack:
        focus_areas.append(f"Stack proficiency: {', '.join(profile.tech_stack)}")

    if not focus_areas:
        focus_areas = ["Domain Knowledge", "Communication Skills", "Problem Solving"]

    tips = {
        "entry": "Focus on DSA fundamentals and be ready to walk through your academic/project work step-by-step.",
        "mid": "Prepare concrete STAR-format stories from past projects; be ready to discuss trade-offs.",
        "senior": "Emphasise leadership, system design at scale, and how you drive engineering culture.",
    }

    return ProfileSummary(
        name=profile.name,
        job_role=profile.job_role,
        experience_level=level,
        focus_areas=list(dict.fromkeys(focus_areas)),  # deduplicate, preserve order
        recommended_question_types=list(dict.fromkeys(recommended_types)),
        preparation_tip=tips[level],
    )


@tool(permission=ToolPermission.READ_ONLY)
def get_question_set_config(request: QuestionSetRequest) -> QuestionSet:
    """
    Generate a structured interview question set tailored to a role and experience level.

    Uses curated question banks aligned with industry interview standards.
    The knowledge base RAG layer supplements this with the latest role-specific content.

    Args:
        request (QuestionSetRequest): Role, level, question types, and count per type.

    Returns:
        QuestionSet: A complete, categorised set of interview questions.
    """
    count = max(1, min(request.count_per_type, 10))
    level = request.experience_level.lower().strip()
    role = request.job_role

    # Curated seed banks keyed by (type, level)
    seed_questions = {
        ("technical", "entry"): [
            "Explain the difference between a stack and a queue.",
            "What is time complexity? Give an example of O(n log n).",
            "How does garbage collection work in your primary language?",
            "Write a function to reverse a linked list.",
            "What is REST, and how does it differ from GraphQL?",
        ],
        ("technical", "mid"): [
            "Design a rate limiter for a high-traffic API.",
            "How would you optimise a slow SQL query with millions of rows?",
            "Explain eventual consistency vs. strong consistency.",
            "What are the SOLID principles? Give an example of each.",
            "How do you handle distributed transactions?",
        ],
        ("technical", "senior"): [
            "How would you architect a real-time collaborative editing system?",
            "Describe your approach to database sharding at 10× current load.",
            "How do you ensure zero-downtime deployments for a critical service?",
            "What trade-offs would you consider when choosing between microservices and a monolith?",
            "How do you design for observability in a distributed system?",
        ],
        ("behavioral", "entry"): [
            "Tell me about a time you faced a challenging technical problem.",
            "Describe a project you are most proud of and your role in it.",
            "How do you handle feedback from code reviews?",
            "Give an example of when you had to learn something quickly.",
            "How do you prioritise tasks when juggling multiple deadlines?",
        ],
        ("behavioral", "mid"): [
            "Describe a time you disagreed with a technical decision and how you handled it.",
            "Tell me about a project that failed. What did you learn?",
            "How have you mentored junior engineers?",
            "Give an example of driving a cross-functional initiative.",
            "Describe a time you had to balance technical debt against new features.",
        ],
        ("behavioral", "senior"): [
            "Tell me about a time you changed the technical direction of a team.",
            "How have you built engineering culture and standards at your organisation?",
            "Describe a situation where you influenced a major architectural decision.",
            "How do you handle underperforming team members?",
            "Give an example of driving organisation-wide technical change.",
        ],
        ("system_design", "entry"): [
            "Design a URL shortener (e.g., bit.ly).",
            "How would you design a simple key-value store?",
            "Design a basic notification system.",
            "Walk me through a design for a file upload service.",
            "How would you design a simple chat application?",
        ],
        ("system_design", "mid"): [
            "Design Twitter's trending topics feature.",
            "How would you design a ride-sharing backend like Uber?",
            "Design a distributed job scheduler.",
            "How would you build a scalable e-commerce checkout system?",
            "Design a real-time leaderboard for a gaming platform.",
        ],
        ("system_design", "senior"): [
            "Design a global CDN from scratch.",
            "How would you architect a multi-region active-active database system?",
            "Design a ML feature store for a recommendation engine at Netflix scale.",
            "How would you build a secure, compliant payment processing platform?",
            "Design a fault-tolerant event streaming platform (Kafka-like).",
        ],
        ("hr", "entry"): [
            "Why do you want to join our company?",
            "Where do you see yourself in 3 years?",
            "What are your greatest strengths and weaknesses?",
            "How do you handle work-life balance?",
            "Why are you looking to leave your current role?",
        ],
        ("hr", "mid"): [
            "What motivates you beyond compensation?",
            "How do you approach continuous learning?",
            "Describe your ideal team and working environment.",
            "How do you align your personal goals with company objectives?",
            "What is your leadership style?",
        ],
        ("hr", "senior"): [
            "How do you build high-performing engineering teams?",
            "What is your philosophy on technical hiring?",
            "How do you balance innovation with stability?",
            "Describe how you align engineering strategy with business goals.",
            "What legacy do you want to leave at your next company?",
        ],
    }

    difficulty_map = {"entry": "easy", "mid": "medium", "senior": "hard"}
    difficulty = difficulty_map.get(level, "medium")

    questions: List[InterviewQuestion] = []
    for q_type in request.question_types:
        key = (q_type.lower(), level)
        bank = seed_questions.get(key, seed_questions.get((q_type.lower(), "mid"), []))
        for i in range(min(count, len(bank))):
            questions.append(
                InterviewQuestion(
                    question_type=q_type,
                    question=bank[i],
                    difficulty=difficulty,
                    hint=None,
                )
            )

    estimated_minutes = len(questions) * 4  # ~4 min average per question

    return QuestionSet(
        job_role=role,
        experience_level=level,
        total_questions=len(questions),
        questions=questions,
        estimated_duration_minutes=estimated_minutes,
    )
