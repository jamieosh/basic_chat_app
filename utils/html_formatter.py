import html


_CODE_BLOCK_CLASS = "bg-gray-800 text-gray-100 p-2 rounded-md overflow-x-auto text-sm my-2"


def _format_text_segment(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _format_code_block(raw_block: str) -> str:
    language = ""
    code = raw_block

    if raw_block.startswith("\n"):
        code = raw_block[1:]
    else:
        first_line, separator, remainder = raw_block.partition("\n")
        if separator:
            language = first_line.strip()
            code = remainder

    code_html = html.escape(code.rstrip("\n"))
    language_attr = f' class="language-{html.escape(language)}"' if language else ""
    return f'<pre class="{_CODE_BLOCK_CLASS}"><code{language_attr}>{code_html}</code></pre>'


def format_response_as_html(response: str) -> str:
    """Format text as HTML while keeping fenced code blocks structurally safe."""
    if not isinstance(response, str):
        raise TypeError("Response must be a string")

    formatted_parts: list[str] = []
    cursor = 0

    while True:
        block_start = response.find("```", cursor)
        if block_start == -1:
            formatted_parts.append(_format_text_segment(response[cursor:]))
            break

        block_end = response.find("```", block_start + 3)
        if block_end == -1:
            formatted_parts.append(_format_text_segment(response[cursor:]))
            break

        formatted_parts.append(_format_text_segment(response[cursor:block_start]))
        formatted_parts.append(_format_code_block(response[block_start + 3:block_end]))
        cursor = block_end + 3

    return "".join(formatted_parts)
