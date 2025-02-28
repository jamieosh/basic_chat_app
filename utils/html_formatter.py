import html

async def format_response_as_html(response: str) -> str:
    """Format a text response as HTML with code block handling
    
    Args:
        response: Raw text response to format
        
    Returns:
        str: HTML formatted response with code blocks and line breaks
    """
    # Escape HTML in the response to prevent XSS
    safe_response = html.escape(response)
    
    # Format the response with line breaks
    formatted_response = safe_response.replace('\n', '<br>')
    
    # Process code blocks if present (simple markdown-like formatting)
    if '```' in formatted_response:
        # Replace code blocks with styled pre elements
        parts = formatted_response.split('```')
        formatted_parts = []
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                formatted_parts.append(part)
            else:  # Code block
                # Check if the code block has a language specified
                lines = part.split('<br>', 1)
                if len(lines) > 1:
                    language = lines[0].strip()
                    code = lines[1]
                    formatted_parts.append(f'<pre class="bg-gray-800 text-gray-100 p-2 rounded-md overflow-x-auto text-sm my-2"><code class="language-{language}">{code}</code></pre>')
                else:
                    formatted_parts.append(f'<pre class="bg-gray-800 text-gray-100 p-2 rounded-md overflow-x-auto text-sm my-2"><code>{part}</code></pre>')
        
        formatted_response = ''.join(formatted_parts)
        
    return formatted_response 