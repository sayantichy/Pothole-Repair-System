def compute_priority(size_1_10: int) -> str:
    if size_1_10 >= 8: return "High"
    if size_1_10 >= 5: return "Medium"
    return "Low"
