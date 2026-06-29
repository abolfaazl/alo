ASSESSMENT_PROMPT = """You are an expert tutor.
The user is learning about: {subject}
Their target goal is: {goal}
Their current experience level is: {level}
Their known background is: {background}

Generate exactly 20 multiple-choice questions to assess their current skill level in this subject.

CRITICAL INSTRUCTIONS:
1. If the user is an absolute beginner or knows nothing, the assessment must still be possible, but foundational and non-punitive. Generate basic calibration questions about core concepts or prerequisites.
2. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
3. Ensure exactly one correct choice per question.
4. Do NOT include private company names.
5. Ensure questions are relevant to the learning subject.
"""

PATHS_PROMPT = """You are an expert tutor.
Review the following context about the user's learning project:
{context}

Generate exactly 3 targeted learning path proposals for the user.
The paths must be specific to the workspace subject.

CRITICAL INSTRUCTIONS:
1. Generate exactly 3 distinct learning paths.
2. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
3. If no formal assessment exists in the context, set the path confidence to "low" or "medium".
4. Ensure the paths directly address the user's current level, goals, and any identified weaknesses.
"""

ROADMAP_PROMPT = """You are an expert tutor.
Review the following context about the user's learning project, especially the Active Learning Path:
{context}

Generate a detailed, step-by-step roadmap for the current learning workspace based on the selected active learning path.
The roadmap must be subject-specific.

CRITICAL INSTRUCTIONS:
1. Generate between 8 and 15 roadmap items. Do not generate fewer than 8 or more than 15.
2. Ensure the roadmap is beginner-friendly if the user's profile indicates they are a beginner.
3. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
4. Each item must have a stable ID starting from ALO-RM-001 (e.g., ALO-RM-001, ALO-RM-002).
5. Do NOT include private company names unless the privacy rules permit it.
6. The items must be small, actionable learning units suitable for a single or small group of study sessions.
7. Use valid status values. Default to "todo".
"""

SESSION_PROMPT = """You are an expert tutor.
Review the following context about the user's learning workspace:
{context}

Target Roadmap Item:
{item_content}

Generate a short, practical, subject-specific learning session for this roadmap item.
CRITICAL INSTRUCTIONS:
1. Ensure the lesson size is approximately 400 to 800 words (or less for simple topics).
2. The lesson must be aligned with the user's level and the roadmap item.
3. Be privacy-aware; do not include private names unless permitted.
4. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
5. Provide a practice_question that tests their understanding of the lesson.
"""

EVALUATION_PROMPT = """You are an expert tutor evaluating a user's answer.
Context:
{context}

Roadmap Item:
{item_content}

Lesson Provided:
{lesson_content}

Practice Question:
{question}

User's Answer to Practice Question:
{user_answer}

Evaluate the user's answer.
CRITICAL INSTRUCTIONS:
1. 'pass' should usually update roadmap item to 'passed_once'.
2. 'partial' should usually update roadmap item to 'practiced' or 'needs_review'.
3. 'fail' should update roadmap item to 'needs_review'.
4. Do not mark any item as 'mastered'.
5. Only add weakness_entries if the answer reveals a real, actionable knowledge gap.
6. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
"""

REVIEW_PROMPT = """You are an expert tutor.
Review the following context about the user's learning workspace:
{context}

Target for Review:
ID: {target_id}
Type: {target_type}
Content: {target_content}

Generate a short, targeted review session focusing on this specific weak area or topic.
CRITICAL INSTRUCTIONS:
1. The review must focus strictly on the target content, directly addressing misunderstandings, mistakes, or gaps.
2. Ensure the lesson size is approximately 200 to 500 words.
3. Be practical, concise, and subject-specific.
4. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
5. Provide a review_question to test their understanding of the review lesson.
"""

REVIEW_EVALUATION_PROMPT = """You are an expert tutor evaluating a user's answer to a review question.
Context:
{context}

Review Target:
ID: {target_id}
Type: {target_type}
Content: {target_content}

Review Lesson Provided:
{lesson_content}

Review Question:
{question}

User's Answer:
{user_answer}

Evaluate the user's answer and score it (pass, partial, fail).
CRITICAL INSTRUCTIONS:
1. If the target is a roadmap_item:
   - 'pass' may update status to 'passed_once'.
   - 'partial' may update status to 'practiced' or 'needs_review'.
   - 'fail' should update status to 'needs_review'.
2. If the target is a weakness:
   - 'pass' may update status to 'resolved' or 'improving'.
   - 'partial' may update status to 'improving' or 'active'.
   - 'fail' should keep status 'active'.
3. Do not mark anything as 'mastered'.
4. Use the provided JSON schema. Ensure output is strict JSON with no markdown wrapping.
"""
