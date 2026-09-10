"""
TechQueue Interview Coach — Answer Evaluation & Improvement Tools

Evaluates candidate answers against best-practice criteria and
provides structured feedback with improvement tips.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AnswerEvaluationRequest(BaseModel):
    """Input for evaluating a candidate's answer to an interview question."""
    question: str = Field(..., description="The interview question that was answered")
    candidate_answer: str = Field(..., description="The candidate's answer to evaluate")
    question_type: str = Field(
        ...,
        description="Type of question: 'technical', 'behavioral', 'system_design', or 'hr'"
    )
    experience_level: str = Field(
        ...,
        description="Candidate experience level: 'entry', 'mid', or 'senior'"
    )


class ScoreDimension(BaseModel):
    """Score for a single evaluation dimension."""
    dimension: str = Field(description="Evaluation dimension name")
    score: int = Field(description="Score from 1 (poor) to 5 (excellent)")
    feedback: str = Field(description="Brief feedback for this dimension")


class AnswerEvaluation(BaseModel):
    """Comprehensive evaluation of a candidate's answer."""
    question: str = Field(description="The evaluated question")
    overall_score: int = Field(description="Overall score from 1 to 10")
    grade: str = Field(description="Letter grade: A / B / C / D / F")
    dimension_scores: List[ScoreDimension] = Field(description="Detailed dimension scores")
    strengths: List[str] = Field(description="What the candidate did well")
    improvement_areas: List[str] = Field(description="Areas needing improvement")
    model_answer_outline: str = Field(description="Outline of an ideal answer")
    follow_up_questions: List[str] = Field(
        description="Follow-up questions an interviewer might ask"
    )


class MockInterviewRequest(BaseModel):
    """Request to run a full mock interview session summary."""
    job_role: str = Field(..., description="Target job role")
    experience_level: str = Field(..., description="Experience level")
    answered_questions: int = Field(..., description="Total questions answered")
    average_score: float = Field(..., description="Average score across all answers (1–10)")


class MockInterviewReport(BaseModel):
    """Final report card for a completed mock interview session."""
    job_role: str = Field(description="Target job role")
    experience_level: str = Field(description="Experience level")
    overall_readiness: str = Field(description="Readiness level: Not Ready / Needs Work / Ready / Strong")
    overall_score: float = Field(description="Average interview score")
    strengths_summary: str = Field(description="Summary of overall strengths")
    key_gaps: List[str] = Field(description="Key gaps to address before the real interview")
    action_plan: List[str] = Field(description="Concrete next steps to improve")
    recommended_resources: List[str] = Field(description="Recommended resources for improvement")
    confidence_boost: str = Field(description="Motivational message tailored to the candidate's level")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def evaluate_answer(request: AnswerEvaluationRequest) -> AnswerEvaluation:
    """
    Evaluate a candidate's interview answer and provide structured feedback.

    Scores the answer across multiple dimensions (clarity, depth, relevance,
    structure, examples) and provides improvement suggestions plus a model
    answer outline for the candidate to compare against.

    Args:
        request (AnswerEvaluationRequest): The question, answer, type, and level.

    Returns:
        AnswerEvaluation: Scored evaluation with feedback, strengths, and improvement tips.
    """
    answer = request.candidate_answer.strip()
    q_type = request.question_type.lower()
    level = request.experience_level.lower()

    # Heuristic scoring dimensions based on answer characteristics
    word_count = len(answer.split())
    has_example = any(kw in answer.lower() for kw in ("for example", "for instance", "such as", "i worked", "we built", "i designed", "in my"))
    has_structure = any(kw in answer.lower() for kw in ("first", "second", "then", "finally", "additionally", "however", "because"))
    has_technical_depth = word_count > 80

    clarity_score = 4 if has_structure else 3
    depth_score = 4 if has_technical_depth else 2
    relevance_score = 3  # baseline — RAG layer will refine
    example_score = 5 if has_example else 2
    structure_score = 4 if has_structure else 2

    raw_avg = (clarity_score + depth_score + relevance_score + example_score + structure_score) / 5
    overall = round(raw_avg * 2)  # scale 1–5 average → 1–10

    grade_map = {10: "A", 9: "A", 8: "B", 7: "B", 6: "C", 5: "C", 4: "D"}
    grade = grade_map.get(overall, "F")

    dimensions = [
        ScoreDimension(dimension="Clarity", score=clarity_score,
                       feedback="Answer is clear and easy to follow." if clarity_score >= 4 else "Improve logical flow and structure."),
        ScoreDimension(dimension="Depth", score=depth_score,
                       feedback="Good technical depth shown." if depth_score >= 4 else "Add more detail and technical specifics."),
        ScoreDimension(dimension="Relevance", score=relevance_score,
                       feedback="Answer is on-topic." if relevance_score >= 4 else "Ensure your answer directly addresses the question."),
        ScoreDimension(dimension="Examples", score=example_score,
                       feedback="Great use of concrete examples." if example_score >= 4 else "Include real-world examples or STAR-format stories."),
        ScoreDimension(dimension="Structure", score=structure_score,
                       feedback="Well-structured answer." if structure_score >= 4 else "Use signposting words (first, then, finally) for clarity."),
    ]

    strengths = []
    improvements = []

    if example_score >= 4:
        strengths.append("Effectively used concrete examples to support the answer.")
    else:
        improvements.append("Add at least one specific example (project, incident, or result).")

    if has_structure:
        strengths.append("Answer has a clear logical structure.")
    else:
        improvements.append("Structure the answer with clear signposting (e.g., STAR method for behavioral, or Step 1/2/3 for technical).")

    if has_technical_depth:
        strengths.append("Demonstrated solid technical depth.")
    else:
        improvements.append("Expand on the technical specifics — interviewers want to see depth, not just surface-level knowledge.")

    if word_count < 50:
        improvements.append("Answer is too brief. Aim for 100–200 words per question.")

    # Type-specific model answer outlines
    outlines = {
        "technical": "1. State the concept/approach clearly. 2. Explain the mechanism or algorithm. 3. Discuss time/space complexity or trade-offs. 4. Give a real-world use-case or code snippet.",
        "behavioral": "Use the STAR method: Situation → Task → Action → Result. Quantify impact where possible.",
        "system_design": "1. Clarify requirements (functional + non-functional). 2. Estimate scale. 3. High-level design (components). 4. Deep-dive on critical path. 5. Discuss trade-offs and failure handling.",
        "hr": "Be authentic, align your answer with the company's values, and back claims with a brief story or example.",
    }
    model_outline = outlines.get(q_type, outlines["behavioral"])

    follow_ups = {
        "technical": ["What is the time complexity of your solution?", "How would you scale this?", "Are there edge cases you haven't handled?"],
        "behavioral": ["What would you do differently now?", "How did that experience shape your approach?", "What was the measurable outcome?"],
        "system_design": ["How would you handle a 10× traffic spike?", "What monitoring would you put in place?", "How would you migrate from the current system?"],
        "hr": ["Can you give another example?", "How does that value align with our mission?", "What does success look like for you here?"],
    }

    return AnswerEvaluation(
        question=request.question,
        overall_score=overall,
        grade=grade,
        dimension_scores=dimensions,
        strengths=strengths if strengths else ["Attempted to answer the question."],
        improvement_areas=improvements if improvements else ["Keep practising to sharpen delivery."],
        model_answer_outline=model_outline,
        follow_up_questions=follow_ups.get(q_type, follow_ups["behavioral"]),
    )


@tool(permission=ToolPermission.READ_ONLY)
def generate_mock_interview_report(request: MockInterviewRequest) -> MockInterviewReport:
    """
    Generate a final performance report card after a complete mock interview session.

    Provides an overall readiness assessment, key gaps, and a concrete action plan
    to help the candidate improve before their real interview.

    Args:
        request (MockInterviewRequest): Role, level, question count, and average score.

    Returns:
        MockInterviewReport: A comprehensive final report with action plan.
    """
    score = request.average_score
    level = request.experience_level.lower()

    if score >= 8.5:
        readiness = "Strong"
        strengths_summary = "Excellent performance across all areas. The candidate demonstrates interview-ready confidence and depth."
    elif score >= 7.0:
        readiness = "Ready"
        strengths_summary = "Solid performance with minor gaps. A few more practice sessions will build strong confidence."
    elif score >= 5.5:
        readiness = "Needs Work"
        strengths_summary = "Competent base but needs targeted improvement in depth and structure."
    else:
        readiness = "Not Ready"
        strengths_summary = "Foundational preparation required before attempting real interviews."

    key_gaps = []
    action_plan = []

    if score < 7:
        key_gaps.append("Answer depth and technical specificity")
        action_plan.append("Practise explaining concepts using the Feynman Technique — explain it simply first, then add depth.")
    if score < 6:
        key_gaps.append("Structured storytelling for behavioral questions")
        action_plan.append("Write out 5 STAR-format stories covering: challenge, collaboration, failure, leadership, and innovation.")
    if level in ("mid", "senior") and score < 7.5:
        key_gaps.append("System design breadth and trade-off articulation")
        action_plan.append("Study 3 system design case studies per week from resources like 'Designing Data-Intensive Applications'.")

    action_plan += [
        f"Complete at least 2 more full mock interviews targeting {request.job_role} roles.",
        "Record yourself answering questions to review pacing and filler words.",
        "Research the target company's tech stack and tailor examples accordingly.",
    ]

    resources = [
        "LeetCode (DSA practice): https://leetcode.com",
        "System Design Primer: https://github.com/donnemartin/system-design-primer",
        "Grokking the Behavioural Interview: https://www.educative.io",
        "STAR Method Guide: https://www.themuse.com/advice/star-interview-method",
        "TechQueue Question Bank (this agent's knowledge base)",
    ]

    confidence_messages = {
        "entry": "Every expert was once a beginner. Keep practising — your progress is real and the interviews are winnable!",
        "mid": "You have valuable experience. Structure your stories, show your depth, and you'll stand out in the room.",
        "senior": "Your experience is your superpower. Articulate your impact clearly and lead with outcomes.",
    }

    return MockInterviewReport(
        job_role=request.job_role,
        experience_level=level,
        overall_readiness=readiness,
        overall_score=round(score, 1),
        strengths_summary=strengths_summary,
        key_gaps=key_gaps if key_gaps else ["Minor polish on delivery and conciseness."],
        action_plan=action_plan,
        recommended_resources=resources,
        confidence_boost=confidence_messages.get(level, confidence_messages["mid"]),
    )
