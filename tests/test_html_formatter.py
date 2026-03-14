import asyncio
import threading

from utils.html_formatter import format_response_as_html


def _run_async(coroutine):
    result = {"value": None}
    error = {"value": None}

    def _target():
        try:
            result["value"] = asyncio.run(coroutine)
        except Exception as exc:  # pragma: no cover - only used on failure paths
            error["value"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join()

    if error["value"] is not None:
        raise error["value"]
    return result["value"]


def test_formatter_escapes_html():
    response = _run_async(format_response_as_html("<script>alert('x')</script>"))

    assert "<script>" not in response
    assert "&lt;script&gt;" in response


def test_formatter_formats_fenced_code_blocks():
    raw = "Example:\n```python\nprint('ok')\n```"
    response = _run_async(format_response_as_html(raw))

    assert "<pre" in response
    assert "language-python" in response
    assert "print(&#x27;ok&#x27;)" in response


def test_formatter_replaces_newlines_with_breaks():
    raw = "one\ntwo\nthree"
    response = _run_async(format_response_as_html(raw))

    assert response == "one<br>two<br>three"


def test_formatter_formats_code_block_without_language():
    raw = "```\nprint('x')\n```"
    response = _run_async(format_response_as_html(raw))

    assert "<pre" in response
    assert "language-" in response
    assert "print(&#x27;x&#x27;)" in response


def test_formatter_formats_multiple_code_blocks():
    raw = "A\n```python\nx=1\n```\nB\n```js\ny=2\n```"
    response = _run_async(format_response_as_html(raw))

    assert response.count("<pre") == 2
    assert "language-python" in response
    assert "language-js" in response
