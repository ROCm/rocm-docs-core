"""Utilities for formatting text"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, Optional, Tuple


class Formatter:
    """Formatting class for string substitution and comments parsing."""

    @dataclass
    class _Replacement:
        loc: Tuple[int, int]
        text: str

    def __init__(self, context: Dict[str, Any]):
        self.directive_pattern: re.Pattern = re.compile(
            r"(\$)?\{([a-zA-z][a-zA-Z0-9_]+)(?:\:([a-zA-Z0-9_\-\.]+))?\}"
        )
        self.context = context

    def _format_directive(self, match: re.Match) -> Optional[_Replacement]:
        # As a special case allow `{branch}` and `url` to alias `${branch}`
        # and '${url}' respectively for backwards compatibility.
        # Otherwise the '$' is required
        if match[1] is None:
            if match[2] not in ["branch", "url"]:
                return None

        if match[2] in ["branch", "url"]:
            # Cannot have a parameter
            if match[3] is not None:
                return None
            return self._Replacement(match.span(), self.context[match[2]])
        elif match[2] == "project":
            # Parameter is required
            if match[3] is None:
                return None
            if match[3] not in self.context["projects"]:
                return None
            return self._Replacement(
                match.span(), self.context["projects"][match[3]]
            )
        return None

    def _replacements(self, line: str) -> Generator[_Replacement, None, None]:
        for match in self.directive_pattern.finditer(line):
            replacement = self._format_directive(match)
            if replacement is not None:
                yield replacement

    def format_line(self, line: str) -> str:
        """Substitute references of the form ${<variable>}
        and ${directive:param} into line.

        >>> f = Formatter(
        ...     {
        ...         "branch": "develop",
        ...         "url": "https://example.com",
        ...         "projects": {"project": "https://project.com"},
        ...     }
        ... )
        >>> f.format_line('my branch is ${branch}, {branch} also works')
        'my branch is develop, develop also works'
        >>> f.format_line('Url: ${url} or {url}')
        'Url: https://example.com or https://example.com'
        >>> f.format_line('- url: ${project:project}')
        '- url: https://project.com'

        Unknown references are not replaced.
        >>> f.format_line('{invalid}')
        '{invalid}'
        """

        result: str = ""
        end: int = 0
        for replacement in self._replacements(line):
            assert replacement.loc[0] >= end
            result += line[end : replacement.loc[0]] + replacement.text
            end = replacement.loc[1]

        result += line[end:]
        return result

    def skip_comments(self, lines: Iterable[str]) -> Generator[str, None, None]:
        """Returns a sequence that skips lines as long as they start with '#'.
        Lines after the first "non-comment" line are returned as-is.

        >>> f = Formatter({})
        >>> for l in f.skip_comments(
        ...     ["#comment 0", "# comment 1", "text", "# will not be skipped"]
        ... ):
        ...     print(l)
        text
        # will not be skipped
        """

        it = iter(lines)
        for line in it:
            if not line.startswith("#"):
                yield line
                break
        yield from it


def format_toc(input_path: Path, output_path: Path, context: Dict[str, Any]):
    """Format the input table of contents with additional information."""

    formatter = Formatter(context)
    with open(input_path, "r", encoding="utf-8") as toc_in, open(
        output_path, "w", encoding="utf-8"
    ) as toc_out:
        for line in formatter.skip_comments(toc_in):
            toc_out.write(formatter.format_line(line))
