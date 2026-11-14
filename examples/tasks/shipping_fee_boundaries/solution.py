def shipping_fee(weight_kg):
    """Fee by weight: up to 1 kg costs 4.0, up to 5 kg 7.5, up to 20 kg 15.0,
    then 1.2 per extra kg. Weight must be positive."""
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    if weight_kg <= 1:
        return 4.0
    if weight_kg <= 5:
        return 7.5
    if weight_kg <= 20:
        return 15.0
    return 15.0 + 1.2 * (weight_kg - 20)
