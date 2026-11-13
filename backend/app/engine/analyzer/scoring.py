def normalize_score(score: int) -> int:
    return max(0, min(score, 100))
