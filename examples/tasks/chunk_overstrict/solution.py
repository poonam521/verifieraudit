def _validate_size(size):
    if size <= 0:
        raise ValueError("size must be a positive integer")


def chunk(items, size):
    """Split ``items`` into consecutive lists of at most ``size`` elements."""
    _validate_size(size)
    return [items[i:i + size] for i in range(0, len(items), size)]
