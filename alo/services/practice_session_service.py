import re
from typing import List, Optional
from pydantic import BaseModel

class PracticeItem(BaseModel):
    index: int
    prompt: str
    expected_answer: Optional[str] = None

class PracticeSessionState(BaseModel):
    session_id: str
    total_items: int
    current_index: int = 0
    items: List[PracticeItem]
    # To store evaluations
    results: List[dict] = []

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
            result.append(PracticeItem(index=i+1, prompt=prompt))
        return result
        
    return [PracticeItem(index=1, prompt=question_text)]
