def extract_code_from_response(response: str) -> str:
    """
    Extract code from LLM response (handles ```python blocks)
    """
    if "```python" in response:
        code = response.split("```python")[1].split("```")[0].strip()
        return code
    elif "```" in response:
        code = response.split("```")[1].split("```")[0].strip()
        return code
    else:
        return response.strip()