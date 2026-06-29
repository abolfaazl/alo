from typing import List
from textual.widgets import OptionList, Static
from textual.containers import Vertical
from textual.app import ComposeResult
from textual.message import Message

class ChoicePrompt(Vertical):
    """
    A reusable choice prompt component that renders an OptionList inline.
    It can be navigated with arrows and selected with Enter.
    """
    
    class Selected(Message):
        """Emitted when an option is selected."""
        def __init__(self, value: str):
            super().__init__()
            self.value = value

    class Cancelled(Message):
        """Emitted when the selection is cancelled."""
        pass

    def __init__(self, label: str, options: List[str], id: str = None, **kwargs):
        super().__init__(id=id, **kwargs)
        self.label_text = label
        self.options_list = options

    def compose(self) -> ComposeResult:
        from alo.ui.rtl import format_rtl_for_display
        yield Static(format_rtl_for_display(self.label_text), classes="choice-prompt-label")
        # Format options for RTL if needed, but we keep the original values to return them
        formatted_options = [format_rtl_for_display(opt) for opt in self.options_list]
        option_list = OptionList(*formatted_options, id="choice-option-list")
        yield option_list

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Stop the event so it doesn't bubble if we don't want it to
        event.stop()
        # Return the original unformatted string based on index
        selected_value = self.options_list[event.option_index]
        self.post_message(self.Selected(selected_value))

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())
