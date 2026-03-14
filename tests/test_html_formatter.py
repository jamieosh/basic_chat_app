import pytest

from utils.html_formatter import format_response_as_html


def test_formatter_escapes_html():
    response = format_response_as_html("<script>alert('x')</script>")

    assert "<script>" not in response
    assert "&lt;script&gt;" in response


def test_formatter_formats_fenced_code_blocks():
    raw = "Example:\n```python\nprint('ok')\n```"
    response = format_response_as_html(raw)

    assert "<pre" in response
    assert "language-python" in response
    assert "print(&#x27;ok&#x27;)" in response


def test_formatter_replaces_newlines_with_breaks():
    raw = "one\ntwo\nthree"
    response = format_response_as_html(raw)

    assert response == "one<br>two<br>three"


def test_formatter_formats_code_block_without_language():
    raw = "```\nprint('x')\n```"
    response = format_response_as_html(raw)

    assert "<pre" in response
    assert "language-" not in response
    assert "print(&#x27;x&#x27;)" in response


def test_formatter_formats_multiple_code_blocks():
    raw = "A\n```python\nx=1\n```\nB\n```js\ny=2\n```"
    response = format_response_as_html(raw)

    assert response.count("<pre") == 2
    assert "language-python" in response
    assert "language-js" in response


def test_formatter_keeps_unmatched_fence_as_plain_text():
    raw = "Before\n```python\nprint('oops')"
    response = format_response_as_html(raw)

    assert "<pre" not in response
    assert "```python" in response
    assert "print(&#x27;oops&#x27;)" in response


def test_formatter_handles_mixed_text_and_code_blocks():
    raw = "Intro\n```python\nprint('ok')\n```\nOutro"
    response = format_response_as_html(raw)

    assert response.startswith("Intro<br>")
    assert "<pre" in response
    assert response.endswith("<br>Outro")


def test_formatter_rejects_non_string_input():
    with pytest.raises(TypeError, match="Response must be a string"):
        format_response_as_html(["not", "text"])


def test_formatter_returns_empty_string_for_empty_response():
    assert format_response_as_html("") == ""


def test_formatter_formats_empty_fenced_code_block():
    response = format_response_as_html("```\n```")

    assert '<pre class="' in response
    assert "<code></code>" in response


def test_formatter_formats_adjacent_fenced_code_blocks():
    raw = "```python\nx=1\n``````js\ny=2\n```"
    response = format_response_as_html(raw)

    assert response.count("<pre") == 2
    assert "language-python" in response
    assert "language-js" in response
    assert "x=1" in response
    assert "y=2" in response
