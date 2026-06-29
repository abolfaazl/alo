import re

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL_SUPPORT = True
except ImportError:
    HAS_RTL_SUPPORT = False

def has_rtl_text(text: str) -> bool:
    """Detects if the text contains any Arabic/Persian/RTL characters."""
    # Unicode block for Arabic/Persian: \u0600-\u06FF, \u0750-\u077F, \u08A0-\u08FF, \uFB50-\uFDFF, \uFE70-\uFEFF
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text))

def format_rtl_for_display(text: str) -> str:
    """Formats an entirely RTL string for correct display."""
    if not HAS_RTL_SUPPORT or not has_rtl_text(text):
        return text
    
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def format_mixed_text_for_display(text: str) -> str:
    """
    Carefully applies RTL formatting to natural text, preserving URLs, JSON, commands, and markdown where possible.
    For simplicity and safety, we only process lines that contain RTL characters and do not appear to be code blocks.
    """
    if not HAS_RTL_SUPPORT or not has_rtl_text(text):
        return text

    lines = text.split('\n')
    out_lines = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            out_lines.append(line)
            continue
            
        if in_code_block:
            out_lines.append(line)
            continue

        # Skip paths/URLs that might accidentally contain RTL (very rare, but safe to skip)
        if line.strip().startswith("http://") or line.strip().startswith("https://") or re.match(r'^[a-zA-Z]:\\', line.strip()) or line.strip().startswith("/"):
            out_lines.append(line)
            continue
            
        # We also want to skip lines that are entirely JSON (starting with { or [).
        if line.strip().startswith("{") or line.strip().startswith("["):
            out_lines.append(line)
            continue

        if has_rtl_text(line):
            # Extract out Markdown headers to prevent flipping the #
            match = re.match(r'^(#+)\s+(.*)', line)
            if match:
                header, rest = match.groups()
                formatted_rest = format_rtl_for_display(rest)
                out_lines.append(f"{header} {formatted_rest}")
            else:
                out_lines.append(format_rtl_for_display(line))
        else:
            out_lines.append(line)

    return '\n'.join(out_lines)
