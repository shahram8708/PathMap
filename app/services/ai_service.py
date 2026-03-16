import json
from google import genai
from google.genai import types
from ..models.roadmap import PivotRoadmap
from ..models.role import Role

client = genai.Client()


def _extract_text(response):
    if not response:
        return ''
    if getattr(response, 'text', None):
        return response.text
    try:
        return response.candidates[0].content.parts[0].text
    except Exception:
        return ''

def _format_motivation(code: str) -> str:
    mapping = {
        'feeling_stuck': 'feeling stuck in your current role',
        'automation_threat': 'concerned about automation risk',
        'better_income': 'seeking better income and stability',
        'passion_mismatch': 'feeling a mismatch between your work and passions',
        'burnout': 'experiencing burnout from your current work',
        'returning_to_work': 'returning to work after a break',
        'early_career_regret': 'looking to correct an early career choice',
        'other': 'exploring what comes next'
    }
    return mapping.get(code or '', 'navigating your next career move')


def get_dashboard_welcome(user, assessment):
    try:
        active_roadmap = (
            PivotRoadmap.query
            .filter_by(user_id=user.id, is_active=True)
            .order_by(PivotRoadmap.created_at.desc())
            .first()
        )
        role_category = None
        if user.current_role_id:
            role = Role.query.get(user.current_role_id)
            if role:
                role_category = role.category
        completion_state = 'not_started'
        if assessment:
            completion_state = 'complete' if assessment.completed_modules_count == 5 else 'in_progress'
        motivation_text = _format_motivation(getattr(user, 'pivot_motivation', ''))
        prompt_parts = [
            'You are PathMap, a calm career pivot guide.',
            'Write a concise 2-3 sentence welcome (60-80 words).',
            f"User: {user.first_name or 'PathMapper'}; experience: {getattr(user, 'years_experience', '')} years; motivation: {motivation_text}.",
            f"Current role category: {role_category or 'not provided'}.",
        ]
        if completion_state == 'not_started':
            prompt_parts.append('They have not started the assessment. Emphasize starting it and the clarity it unlocks.')
        elif completion_state == 'in_progress':
            prompt_parts.append('Assessment is in progress. Encourage finishing the remaining modules and name what they will gain.')
        else:
            if active_roadmap:
                prompt_parts.append('Assessment is complete and roadmap exists. Reference their pivot direction and nudge this week\'s focus.')
            else:
                prompt_parts.append('Assessment is complete but no roadmap. Encourage running a skill analysis to pick a direction and build a roadmap next.')
        if active_roadmap:
            prompt_parts.append('Mention the 90-day pivot plan and weekly action focus without sounding robotic.')
        prompt = '\n'.join(prompt_parts)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or f"Welcome back, {user.first_name or 'there'}."
    except Exception:
        first_name = user.first_name or 'there'
        return f"Welcome back, {first_name}. Your next step is waiting — let's keep moving."


def get_ai_career_insight(question: str, user_context_dict: dict):
    try:
        system_prompt = (
            "You are PathMap AI, a compassionate, data-driven career pivot advisor. "
            "Use the provided user context to ground your answer. Be specific, 100-200 words, cite uncertainties, avoid guarantees."
        )
        context_json = json.dumps(user_context_dict or {}, ensure_ascii=False)
        full_prompt = f"{system_prompt}\nUser context: {context_json}\nQuestion: {question}"
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt
        )
        return _extract_text(response).strip() or "I'm unable to answer right now. Please try again shortly."
    except Exception:
        return "I'm unable to answer right now. Please try again shortly."


def get_job_market_insights(target_role_title: str):
    try:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])
        prompt = (
            "Provide a concise job market outlook for the role in India, covering demand trends, "
            "average salary range in INR, top hiring cities, key skills, and 12-month growth prospects. "
            "Keep it practical and current. Role: " + target_role_title
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            config=config,
            contents=prompt
        )
        return _extract_text(response).strip() or "We couldn't fetch market insights right now. Please try again soon."
    except Exception:
        return "We couldn't fetch market insights right now. Please try again soon."


def generate_career_profile_narrative(profile_summary_dict: dict):
    try:
        prompt = (
            "Create a 3-paragraph personalized career profile narrative (200-250 words). "
            "Use second person voice. Warm, specific, actionable. Reflect top values, dominant style, skill categories, constraints, and vision themes.\n"
            f"Profile data: {json.dumps(profile_summary_dict or {}, ensure_ascii=False)}"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or "Here is your profile: you have clear strengths and priorities. Let's align opportunities to them and move forward with confidence."
    except Exception:
        return "Here is your profile: you have clear strengths and priorities. Let's align opportunities to them and move forward with confidence."


def generate_decision_commitment_statement(decision_data_dict: dict):
    try:
        prompt = (
            "Create a 3-5 sentence commitment statement that names the chosen career direction, references top values, "
            "acknowledges the key assumption, and ends with a motivating action sentence.\n"
            f"Decision framework data: {json.dumps(decision_data_dict or {}, ensure_ascii=False)}"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or "I will commit to the direction we outlined, honor my values, watch the key assumptions, and take the next step this week."
    except Exception:
        return "I will commit to the direction we outlined, honor my values, watch the key assumptions, and take the next step this week."


def generate_roadmap_task_descriptions(skill_name: str, role_title: str) -> str:
    fallback = (
        f"Build proficiency in {skill_name} through structured practice and real-world application relevant to {role_title} work."
    )
    try:
        prompt = (
            "Provide 3 specific, actionable sub-tasks to build the skill named below for someone pivoting to the target role. "
            "Each sub-task should be concise, outcome-focused, and directly tied to the role's day-to-day work. "
            "Respond as a short paragraph (70-90 words) combining the three sub-tasks in a cohesive description.\n"
            f"Skill: {skill_name}\nTarget role: {role_title}\nRegion: India\nTone: direct, motivating, professional."
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or fallback
    except Exception:
        return fallback


def generate_reflection_insight(reflection_text: str, week_number: int, mood_rating: int) -> str:
    fallback = "Keep going. Every consistent week builds the foundation for your pivot."
    try:
        prompt = (
            "You are PathMap AI, a warm but pragmatic accountability partner for career pivots. "
            "Read the user's weekly reflection and mood rating (1-5). Respond in 2-3 sentences (max 80 words). "
            "Acknowledge what they wrote, note any risks or patterns, and give one specific, practical suggestion for next week. "
            f"Week number: {week_number}. Mood rating: {mood_rating}. Reflection: {reflection_text}"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or fallback
    except Exception:
        return fallback


def summarize_journey_for_ai_insight(journey) -> str:
    try:
        summary_parts = [
            f"Origin role: {journey.origin_role.title if journey.origin_role else journey.origin_role_id}",
            f"Target role: {journey.target_role.title if journey.target_role else journey.target_role_id}",
            f"Outcome: {journey.outcome_status}",
            f"Timeline months: {journey.timeline_months}",
            f"Income change pct: {journey.income_change_pct}",
            f"Experience at pivot: {journey.experience_at_pivot}",
            f"Region: {journey.geographic_region}",
            f"What worked: {journey.what_worked}",
            f"What failed: {journey.what_failed}",
            f"Unexpected: {journey.unexpected_discoveries}",
            f"Advice: {journey.advice_to_others}"
        ]
        prompt = (
            "Create a concise, factual summary (approx 150 words) of this career pivot journey. "
            "Highlight the transition, timeline, income direction, what worked, what failed, and key advice. "
            "Tone: data-driven and candid.\n" + '\n'.join(summary_parts)
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return _extract_text(response).strip() or journey.summary
    except Exception:
        return journey.summary
