from alo.ui import rtl

def test_has_rtl_text():
    # Persian/Arabic
    assert rtl.has_rtl_text("سلام خوبی")
    assert rtl.has_rtl_text("مرحبا")
    # Mixed
    assert rtl.has_rtl_text("Hello سلام")
    # English
    assert not rtl.has_rtl_text("Hello world")
    assert not rtl.has_rtl_text("C:\\windows\\path")
    assert not rtl.has_rtl_text("https://google.com")

def test_format_rtl_mixed_text():
    # It should reverse RTL lines if support is enabled, but not paths or URLs
    mixed_text = (
        "Hello\n"
        "سلام\n"
        "C:\\some\\path\n"
        "https://test.com\n"
        "```python\nسلام داخل کد\n```"
    )
    
    formatted = rtl.format_mixed_text_for_display(mixed_text)
    
    # English line should be unchanged
    assert "Hello" in formatted
    # Path unchanged
    assert "C:\\some\\path" in formatted
    # URL unchanged
    assert "https://test.com" in formatted
    
    if rtl.HAS_RTL_SUPPORT:
        # Code block should remain completely unchanged (including the RTL text inside)
        assert "سلام داخل کد" in formatted
        # The main RTL text will be reshaped and bidi'd
        assert "سلام" not in formatted.split('\n')[1] # the original string shouldn't be there verbatim, it should be reversed/reshaped
    else:
        # Fallback keeps it exactly the same
        assert "سلام" in formatted

def test_graceful_fallback(monkeypatch):
    monkeypatch.setattr(rtl, "HAS_RTL_SUPPORT", False)
    assert rtl.format_mixed_text_for_display("سلام") == "سلام"
