DEFAULT_LOG_TEXT_LIMIT = 512


def truncate_log_text(text, limit: int = DEFAULT_LOG_TEXT_LIMIT) -> str:
    text = "" if text is None else str(text)
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}... [truncated {omitted} chars; total {len(text)}]"
