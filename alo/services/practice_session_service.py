import re
from typing import List, Optional
from pydantic import BaseModel

class PracticeItem(BaseModel):
    index: int
    prompt: str  # The full prompt for evaluator
    display_prompt: str  # The cleaner prompt for UI
    expected_answer: Optional[str] = None

class PracticeItemResult(BaseModel):
    index: int
    result: str
    score: int

class PracticeSummary(BaseModel):
    total_items: int
    passed: int
    partial: int
    failed: int
    average_score: int
    warnings: List[str] = []

class PracticeSessionState(BaseModel):
    session_id: str
    total_items: int
    current_index: int = 0
    items: List[PracticeItem]
    # To store evaluations
    results: List[PracticeItemResult] = []

def summarize_practice_results(results: List[PracticeItemResult]) -> PracticeSummary:
    passed = 0
    partial = 0
    failed = 0
    total_score = 0
    warnings = []
    
    for r in results:
        res = r.result.lower()
        if res == "pass":
            passed += 1
        elif res == "partial":
            partial += 1
        elif res == "fail":
            failed += 1
        else:
            failed += 1
            warnings.append(f"Unknown result type '{res}' counted as fail.")
            
        total_score += r.score
        
    avg_score = round(total_score / len(results)) if results else 0
    
    return PracticeSummary(
        total_items=len(results),
        passed=passed,
        partial=partial,
        failed=failed,
        average_score=avg_score,
        warnings=warnings
    )

def parse_practice_items(question_text: str) -> List[PracticeItem]:
    lines = question_text.split('\n')
    preamble = []
    items = []
    current_item = []
    
    pattern = re.compile(r'^\s*(\d+)[\.\)]\s+(.*)')
    
    for line in lines:
        match = pattern.match(line)
        if match:
            if current_item:
                items.append('\n'.join(current_item))
            current_item = [line.strip()]
        else:
            if current_item:
                current_item.append(line)
            else:
                preamble.append(line)
                
    if current_item:
        items.append('\n'.join(current_item))
        
    if len(items) > 1:
        preamble_str = '\n'.join(preamble).strip()
        result = []
        for i, item in enumerate(items):
            prompt = f"{preamble_str}\n\n{item}" if preamble_str else item
            result.append(PracticeItem(index=i+1, prompt=prompt, display_prompt=item))
        return result
        
    return [PracticeItem(index=1, prompt=question_text, display_prompt=question_text)]
