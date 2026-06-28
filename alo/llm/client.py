import os
from alo.config import load_config
from alo.llm.schemas import AssessmentResponse, GeneratedAssessmentQuestion, LearningPath, LearningPathsResponse, RoadmapItem, RoadmapResponse, LearningSession, LearningEvaluation

def generate_assessment(subject: str, goal: str, level: str, background: str) -> AssessmentResponse | None:
    cfg = load_config()
    
    if cfg.llm_provider not in ["openai", "openai-compatible"]:
        raise ValueError("Only openai and openai-compatible providers are implemented.")
        
    api_key = os.environ.get(cfg.api_key_env_var)
    if not api_key:
        raise ValueError("Configured API key environment variable is missing.")

    import openai
    from alo.llm.prompts import ASSESSMENT_PROMPT
    
    prompt = ASSESSMENT_PROMPT.format(
        subject=subject,
        goal=goal,
        level=level,
        background=background
    )

    client_kwargs = {"api_key": api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
        
    client = openai.OpenAI(**client_kwargs)
    
    try:
        response = client.beta.chat.completions.parse(
            model=cfg.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format=AssessmentResponse,
            temperature=0.7
        )
        return response.choices[0].message.parsed
    except Exception:
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return AssessmentResponse.model_validate_json(content)
        except Exception as fallback_e:
            raise ValueError(f"Failed to generate valid JSON assessment. Error: {fallback_e}")

def generate_mock_assessment(subject: str) -> AssessmentResponse:
    questions = []
    for i in range(20):
        diff = "foundation"
        if i >= 5:
            diff = "intermediate"
        if i >= 12:
            diff = "advanced"
        if i >= 17:
            diff = "professional"
        
        questions.append(GeneratedAssessmentQuestion(
            id=f"ALO-AS-MOCK-{i:03d}",
            domain=f"{subject} Basics",
            difficulty=diff,
            question=f"Mock question about {subject} {i}",
            choices=["Choice A", "Choice B", "Choice C", "Choice D"],
            correct_choice_index=0,
            explanation=f"Explanation for {subject} {i}",
            weakness_topic=f"{subject} concept {i}"
        ))
    return AssessmentResponse(questions=questions)

def generate_paths(context: str) -> LearningPathsResponse | None:
    cfg = load_config()
    
    if cfg.llm_provider not in ["openai", "openai-compatible"]:
        raise ValueError("Only openai and openai-compatible providers are implemented.")
        
    api_key = os.environ.get(cfg.api_key_env_var)
    if not api_key:
        raise ValueError("Configured API key environment variable is missing.")

    import openai
    from alo.llm.prompts import PATHS_PROMPT
    
    prompt = PATHS_PROMPT.format(context=context)

    client_kwargs = {"api_key": api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
        
    client = openai.OpenAI(**client_kwargs)
    
    try:
        response = client.beta.chat.completions.parse(
            model=cfg.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format=LearningPathsResponse,
            temperature=0.7
        )
        return response.choices[0].message.parsed
    except Exception:
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return LearningPathsResponse.model_validate_json(content)
        except Exception as fallback_e:
            raise ValueError(f"Failed to generate valid JSON paths. Error: {fallback_e}")

def generate_mock_paths(subject: str) -> LearningPathsResponse:
    paths = []
    for i in range(1, 4):
        paths.append(LearningPath(
            id=f"ALO-PATH-00{i}",
            title=f"Mock {subject} Path {i}",
            summary=f"A simulated learning path for {subject}.",
            who_it_is_for="Test users",
            why_it_matches_user="Because it is a mock.",
            expected_outcome="Testing success.",
            core_topics=[f"{subject} Concept A", f"{subject} Concept B"],
            estimated_duration=f"{i} weeks",
            difficulty="intermediate" if i == 2 else "foundation",
            tradeoffs="None",
            first_step="Run the mock.",
            avoid_for_now="Real LLM APIs.",
            confidence="high"
        ))
    return LearningPathsResponse(paths=paths)

def generate_roadmap(context: str) -> RoadmapResponse | None:
    cfg = load_config()
    
    if cfg.llm_provider not in ["openai", "openai-compatible"]:
        raise ValueError("Only openai and openai-compatible providers are implemented.")
        
    api_key = os.environ.get(cfg.api_key_env_var)
    if not api_key:
        raise ValueError("Configured API key environment variable is missing.")

    import openai
    from alo.llm.prompts import ROADMAP_PROMPT
    
    prompt = ROADMAP_PROMPT.format(context=context)

    client_kwargs = {"api_key": api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
        
    client = openai.OpenAI(**client_kwargs)
    
    try:
        response = client.beta.chat.completions.parse(
            model=cfg.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format=RoadmapResponse,
            temperature=0.7
        )
        return response.choices[0].message.parsed
    except Exception:
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return RoadmapResponse.model_validate_json(content)
        except Exception as fallback_e:
            raise ValueError(f"Failed to generate valid JSON roadmap. Error: {fallback_e}")

def generate_mock_roadmap(subject: str) -> RoadmapResponse:
    items = []
    for i in range(1, 11):
        items.append(RoadmapItem(
            id=f"ALO-RM-{i:03d}",
            title=f"Mock {subject} Item {i}",
            summary=f"A simulated roadmap item for {subject}.",
            level="foundation" if i < 5 else "intermediate",
            status="todo",
            estimated_time="30 minutes",
            prerequisites="None",
            success_criteria="Complete it",
            practice_task="Mock practice",
            assessment_method="Mock assessment",
            resources_to_find="Mock resources",
            depends_on=f"ALO-RM-{i-1:03d}" if i > 1 else ""
        ))
    return RoadmapResponse(items=items)

def generate_learning_session(context: str, item_content: str) -> LearningSession | None:
    cfg = load_config()
    
    if cfg.llm_provider not in ["openai", "openai-compatible"]:
        raise ValueError("Only openai and openai-compatible providers are implemented.")
        
    api_key = os.environ.get(cfg.api_key_env_var)
    if not api_key:
        raise ValueError("Configured API key environment variable is missing.")

    import openai
    from alo.llm.prompts import SESSION_PROMPT
    
    prompt = SESSION_PROMPT.format(context=context, item_content=item_content)

    client_kwargs = {"api_key": api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
        
    client = openai.OpenAI(**client_kwargs)
    
    try:
        response = client.beta.chat.completions.parse(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=LearningSession,
            temperature=0.7
        )
        return response.choices[0].message.parsed
    except Exception:
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return LearningSession.model_validate_json(content)
        except Exception as fallback_e:
            raise ValueError(f"Failed to generate valid JSON learning session. Error: {fallback_e}")

def evaluate_learning_session(context: str, item_content: str, lesson_content: str, question: str, user_answer: str) -> LearningEvaluation | None:
    cfg = load_config()
    
    if cfg.llm_provider not in ["openai", "openai-compatible"]:
        raise ValueError("Only openai and openai-compatible providers are implemented.")
        
    api_key = os.environ.get(cfg.api_key_env_var)
    if not api_key:
        raise ValueError("Configured API key environment variable is missing.")

    import openai
    from alo.llm.prompts import EVALUATION_PROMPT
    
    prompt = EVALUATION_PROMPT.format(
        context=context, 
        item_content=item_content,
        lesson_content=lesson_content,
        question=question,
        user_answer=user_answer
    )

    client_kwargs = {"api_key": api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
        
    client = openai.OpenAI(**client_kwargs)
    
    try:
        response = client.beta.chat.completions.parse(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=LearningEvaluation,
            temperature=0.7
        )
        return response.choices[0].message.parsed
    except Exception:
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            return LearningEvaluation.model_validate_json(content)
        except Exception as fallback_e:
            raise ValueError(f"Failed to generate valid JSON evaluation. Error: {fallback_e}")

def generate_mock_learning_session(item_id: str) -> LearningSession:
    return LearningSession(
        topic="Mock Topic",
        roadmap_item_id=item_id,
        short_lesson=f"This is a mock lesson for {item_id}.",
        example="Mock example.",
        common_mistake="Mock mistake.",
        practice_question="What is the mock answer?",
        expected_answer_guidance="Expect 'mock answer'."
    )

def evaluate_mock_learning_session(user_answer: str) -> LearningEvaluation:
    from alo.llm.schemas import WeaknessEntrySchema
    if "fail" in user_answer.lower():
        return LearningEvaluation(
            result="fail",
            score=30,
            feedback="Mock failure feedback.",
            strengths="Mock strengths.",
            weaknesses="Mock weaknesses.",
            recommended_next_step="Try again.",
            roadmap_status_update="needs_review",
            weakness_entries=[
                WeaknessEntrySchema(
                    topic="Mock weakness topic",
                    evidence="Failed the mock question.",
                    recommended_practice="Review mock materials."
                )
            ]
        )
    return LearningEvaluation(
        result="pass",
        score=90,
        feedback="Mock pass feedback.",
        strengths="Mock strengths.",
        weaknesses="None.",
        recommended_next_step="Move to next item.",
        roadmap_status_update="passed_once",
        weakness_entries=[]
    )
