def chunk(items, size):
    if size < 1:
        raise ValueError("size must be at least 1")
    parts = []
    current = []
    for item in items:
        current.append(item)
        if len(current) == size:
            parts.append(current)
            current = []
    if current:
        parts.append(current)
    return parts
