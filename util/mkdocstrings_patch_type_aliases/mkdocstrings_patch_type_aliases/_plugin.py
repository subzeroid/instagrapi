import re
from re import Pattern
from typing import Callable

from mkdocs.plugins import BasePlugin
from mkdocs.structure.nav import Page

ReplaceFunc = Callable[[str], str]


def simple_replace(look_for: str, replace_with: str) -> ReplaceFunc:
    def _replace(text: str) -> str:
        return text.replace(look_for, replace_with)

    return _replace


def regex_replace(look_for: Pattern, replace_with: str) -> ReplaceFunc:
    def _replace(text: str) -> str:
        # breakpoint()
        return re.sub(look_for, replace_with, text)

    return _replace


# Order is significant
REPLACE_FUNCS = [
    # Possible: Python flattens nested unions, so need special handling for normal and nested.
    regex_replace(
        re.compile(r"Union\[([][\w, ]+, ([][\w, ]+)), instagrapi\._interaction\._Sentinel]"),
        r"Possible[Union[\1]]"
    ),
    regex_replace(
        re.compile(r"Union\[([][\w, ]+), instagrapi\._interaction\._Sentinel]"),
        r"Possible[\1]"
    ),
    # StaticOrDynamicValue: Handling for simple and generic types
    regex_replace(
        re.compile(r"Union\[(\w+), Callable\[\[Mapping\[str, Union\[bool, str]]], \w+]]"),
        r"StaticOrDynamicValue[\1]"
    ),
    regex_replace(
        re.compile(r"Union\[([][\w]+), Callable\[\[Mapping\[str, Union\[bool, str]]], [][\w]+]]"),
        r"StaticOrDynamicValue[\1]]"
    ),
    simple_replace("Callable[[Mapping[str, Union[bool, str]]], bool]", "ShouldAsk"),
    simple_replace("Callable[[str, Mapping[str, Union[bool, str]]], Optional[str]]", "Validator"),
    simple_replace("Union[Echo, Acknowledge, Question]", "Interaction"),
    simple_replace("Mapping[str, Union[bool, str]]", "Answers"),
    # Wrapped with square brackets to not replace value in type alias table
    simple_replace("[List[str]]", "[OptionList]"),
    # Any Optional values that were flattened as a nested union
    regex_replace(re.compile(r"Union\[(\w+), NoneType]"), r"Optional[\1]"),
    # Sentinel
    simple_replace("&lt;_Sentinel.A: 0&gt;", "_Sentinel"),
    simple_replace(
        """&lt;</span><span class="n">_Sentinel</span><span class="o">.</span>"""
        """<span class="n">A</span><span class="p">:</span> <span class="mi">0</span>"""
        """<span class="o">&gt;""",
        """<span class="n">_Sentinel</span>"""),
]


class PatchTypeAliases(BasePlugin):
    """
    Manually put type aliases back into documentation.

    mkdocstrings shows the actual type instead of the type alias.
    https://github.com/pawamoy/pytkdocs/issues/80
    """

    def on_post_page(self, output: str, page: Page, config: dict) -> str:
        if page.title == "Reference":
            for replace in REPLACE_FUNCS:
                output = replace(output)
        return output
