def _validate_size(size):
    if size < 1:
        raise ValueError("size must be a positive integer")


def chunk(items, size):
    _validate_size(size)
    parts = []
    for start in range(0, len(items), size):
        parts.append(items[start:start + size])
    return parts
