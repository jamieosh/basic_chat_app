import asyncio

from utils.html_formatter import format_response_as_html


def test_formatter_escapes_html():
    response = asyncio.run(format_response_as_html("<script>alert('x')</script>"))

    assert "<script>" not in response
    assert "&lt;script&gt;" in response


def test_formatter_formats_fenced_code_blocks():
    raw = "Example:\n```python\nprint('ok')\n```"
    response = asyncio.run(format_response_as_html(raw))

    assert "<pre" in response
    assert "language-python" in response
    assert "print(&#x27;ok&#x27;)" in response


def test_formatter_replaces_newlines_with_breaks():
    raw = "one\ntwo\nthree"
    response = asyncio.run(format_response_as_html(raw))

    assert response == "one<br>two<br>three"


def test_formatter_formats_code_block_without_language():
    raw = "```\nprint('x')\n```"
    response = asyncio.run(format_response_as_html(raw))

    assert "<pre" in response
    assert "language-" in response
    assert "print(&#x27;x&#x27;)" in response


def test_formatter_formats_multiple_code_blocks():
    raw = "A\n```python\nx=1\n```\nB\n```js\ny=2\n```"
    response = asyncio.run(format_response_as_html(raw))

    assert response.count("<pre") == 2
    assert "language-python" in response
    assert "language-js" in response
