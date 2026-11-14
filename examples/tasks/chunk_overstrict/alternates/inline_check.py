def chunk(items, size):
    if size <= 0:
        raise ValueError("size must be a positive integer")
    parts = []
    start = 0
    while start < len(items):
        parts.append(items[start:start + size])
        start += size
    return parts
