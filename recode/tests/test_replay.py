"""Unit tests for edit replay and context extraction (BRIEF section 10)."""

import pytest

from replay import (
    ReplayError,
    extract_context,
    find_section_heading,
    find_span,
    replay_chain,
    split_paragraphs,
)

DOC = """# Title

## Section One

First paragraph of section one.

Second paragraph, the one we will edit. It has several sentences in it.

Third paragraph after the edit target.

## Section Two

Closing paragraph.
"""


def _record(find, replace, strategy="exact", round_number=1, **kw):
    base = {
        "model_display": "TestModel",
        "model_id": "test/model",
        "document_id": "test_doc",
        "condition_id": "baseline",
        "round_number": round_number,
        "find_text": find,
        "replace_text": replace,
        "match_strategy": strategy,
        "no_change": False,
        "error": None,
    }
    base.update(kw)
    return base


class TestReplayChain:
    def test_sequential_application_and_state(self):
        records = [
            _record("Second paragraph", "EDITED paragraph", round_number=1),
            _record("EDITED paragraph", "TWICE-EDITED paragraph", round_number=2),
        ]
        results, final = replay_chain(DOC, records)
        assert "TWICE-EDITED paragraph" in final
        assert "Second paragraph" not in final
        assert all(r["span"] is not None for r in results)
        assert [r["replay_strategy"] for r in results] == ["exact", "exact"]

    def test_round_two_sees_round_one_state(self):
        # An edit whose FIND only exists after round 1 was applied.
        records = [
            _record("Second paragraph", "INSERTED-TOKEN paragraph", round_number=1),
            _record("INSERTED-TOKEN", "X", round_number=2),
        ]
        _, final = replay_chain(DOC, records)
        assert "X paragraph" in final

    def test_strategy_mismatch_raises(self):
        records = [_record("Second paragraph", "x", strategy="fuzzy")]
        with pytest.raises(ReplayError, match="replay strategy"):
            replay_chain(DOC, records)

    def test_ambiguous_match_count_raises(self):
        records = [_record("paragraph", "x")]  # occurs many times
        with pytest.raises(ReplayError, match="match_count"):
            replay_chain(DOC, records)

    def test_error_and_no_change_records_skip_state(self):
        records = [
            _record("", "", error="RetryError[boom]", round_number=1),
            _record("[NO CHANGE]", "[NO CHANGE]", strategy="no_change",
                    no_change=True, round_number=2),
            _record("Second paragraph", "EDITED", round_number=3),
        ]
        results, final = replay_chain(DOC, records)
        assert results[0]["span"] is None and results[1]["span"] is None
        assert "EDITED, the one we will edit" in final

    def test_whitespace_strategy_reproduced(self):
        find = "Second  paragraph,\tthe one we   will edit."
        records = [_record(find, "REPLACED.", strategy="whitespace")]
        results, final = replay_chain(DOC, records)
        assert results[0]["replay_strategy"] == "whitespace"
        assert "REPLACED." in final
        # whitespace span excludes surrounding whitespace: the leading newline
        # before the paragraph survives.
        assert "\n\nREPLACED." in final


class TestFindSpan:
    def test_exact_span_offsets(self):
        span = find_span(DOC, "Second paragraph")
        assert DOC[span.start : span.end] == "Second paragraph"
        assert span.match_strategy == "exact"

    def test_missing_raises(self):
        with pytest.raises(ReplayError):
            find_span(DOC, "text that is not there at all, definitely not")


class TestContextExtraction:
    def test_paragraph_split_offsets(self):
        paragraphs = split_paragraphs(DOC)
        assert [p.text for p in paragraphs][:3] == [
            "# Title",
            "## Section One",
            "First paragraph of section one.",
        ]
        for p in paragraphs:
            assert DOC[p.start : p.end].strip("\n") == p.text

    def test_context_fields(self):
        span = find_span(DOC, "Second paragraph, the one we will edit.")
        ctx = extract_context(DOC, span.start, span.end)
        assert ctx["section_heading"] == "Section One"
        assert ctx["context_before"] == "First paragraph of section one."
        assert ctx["context_after"] == "Third paragraph after the edit target."

    def test_document_edges(self):
        span = find_span(DOC, "# Title")
        ctx = extract_context(DOC, span.start, span.end)
        assert ctx["context_before"] == ""
        span = find_span(DOC, "Closing paragraph.")
        ctx = extract_context(DOC, span.start, span.end)
        assert ctx["context_after"] == ""
        assert ctx["section_heading"] == "Section Two"

    def test_multi_paragraph_span(self):
        span = find_span(
            DOC,
            "Second paragraph, the one we will edit. It has several sentences in it.\n\n"
            "Third paragraph after the edit target.",
        )
        ctx = extract_context(DOC, span.start, span.end)
        assert ctx["context_before"] == "First paragraph of section one."
        assert ctx["context_after"] == "## Section Two"


BARE_DOC = """Document Title

Published

Front matter paragraph that sits above the first real heading and wraps
onto a second line without terminal punctuation on line one

Being broadly safe

Body paragraph under the bare-line heading. It has enough text to be a
real paragraph.

Broadly safe behaviors include:

- a list item
- another list item

Closing paragraph of the section.
"""

BRACKET_DOC = """Preamble line before any tag.

[outer_section]

Text inside the outer section.

[inner_section]

Text inside the inner section.

[/inner_section]

Text after the closed inner section, still inside outer.

Data Scope
Bare heading leading straight into its paragraph text.

[/outer_section]

Text after everything was closed.
"""

BOLD_DOC = """Plain preamble paragraph with **inline bold** that is not a heading.

**II. Your Formatting Toolkit**

* **A bold list item that must not count as a heading.**

Mangled Heading**

Paragraph under the mangled bold heading.
"""

FENCE_DOC = """# Real Heading

Some text.

```
# not a heading, it is inside a code fence
code line
```

Paragraph after the fence.
"""


class TestSectionHeadingStyles:
    def _heading_at(self, doc, needle, doc_id):
        pos = doc.find(needle)
        assert pos >= 0
        return find_section_heading(doc, pos + len(needle), doc_id)

    def test_bare_standalone_heading(self):
        h = self._heading_at(BARE_DOC, "Body paragraph under", "claude_constitution")
        assert h == "Being broadly safe"

    def test_bare_rejects_colon_lines_and_lists(self):
        # "Broadly safe behaviors include:" ends with ':' and list items start
        # with '-': neither is a heading, so the nearest heading above the
        # closing paragraph is still the section heading.
        h = self._heading_at(BARE_DOC, "Closing paragraph", "claude_constitution")
        assert h == "Being broadly safe"

    def test_bare_rejects_wrapped_prose_first_lines(self):
        # The front-matter paragraph's first line has no terminal punctuation
        # but is not blank-below, so it is not a heading; the scan falls
        # through to the standalone lines above it.
        h = self._heading_at(BARE_DOC, "onto a second line", "claude_constitution")
        assert h == "Published"

    def test_bare_style_disabled_for_unknown_documents(self):
        assert self._heading_at(BARE_DOC, "Body paragraph under", "other_doc") == ""

    def test_bracket_tag_heading(self):
        h = self._heading_at(BRACKET_DOC, "Text inside the inner section.", "opus_system_prompt")
        assert h == "inner_section"

    def test_bracket_closed_sibling_is_skipped(self):
        h = self._heading_at(
            BRACKET_DOC, "Text after the closed inner section", "opus_system_prompt"
        )
        assert h == "outer_section"

    def test_bracket_all_closed_falls_to_preamble(self):
        h = self._heading_at(BRACKET_DOC, "Text after everything was closed.", "opus_system_prompt")
        assert h == ""

    def test_bracket_span_containing_closing_tag_keeps_section(self):
        # An edit at a section's tail boundary — its span starts at the
        # section's closing tag — still resolves to that section, because
        # closes at or below the span's first line don't wall it off.
        needle = "[/inner_section]"
        pos = BRACKET_DOC.find(needle)
        h = find_section_heading(
            BRACKET_DOC, pos + len(needle), "opus_system_prompt", span_start=pos
        )
        assert h == "inner_section"

    def test_bracket_close_above_span_still_walls_off(self):
        # Same offsets but with span_start below the closing tag: the close
        # is above the span, so inner_section is correctly skipped.
        needle = "Text after the closed inner section"
        pos = BRACKET_DOC.find(needle)
        h = find_section_heading(
            BRACKET_DOC, pos + len(needle), "opus_system_prompt", span_start=pos
        )
        assert h == "outer_section"

    def test_bare_blank_above_heading(self):
        h = self._heading_at(
            BRACKET_DOC, "Bare heading leading straight into", "opus_system_prompt"
        )
        assert h == "Data Scope"

    def test_bold_line_heading(self):
        h = self._heading_at(BOLD_DOC, "A bold list item", "gemini_system_prompt")
        assert h == "II. Your Formatting Toolkit"

    def test_bold_mangled_trailing_only(self):
        h = self._heading_at(BOLD_DOC, "Paragraph under the mangled", "gemini_system_prompt")
        assert h == "Mangled Heading"

    def test_bold_inline_and_preamble_not_headings(self):
        h = self._heading_at(BOLD_DOC, "not a heading.", "gemini_system_prompt")
        assert h == ""

    def test_atx_inside_fence_ignored(self):
        h = self._heading_at(FENCE_DOC, "Paragraph after the fence.", "openai_model_spec")
        assert h == "Real Heading"

    def test_atx_recognized_in_every_document(self):
        assert self._heading_at(FENCE_DOC, "Some text.", "claude_constitution") == "Real Heading"
