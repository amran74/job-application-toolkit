import re
from collections import Counter

STOP = set("""
a an and are as at be by for from has have if in into is it its of on or that the their there these this to was were will with you your
""".split())

def normalize(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9+\s#./-]", " ", text)
    tokens = [t.strip() for t in text.split() if t.strip()]
    tokens = [t for t in tokens if t not in STOP and len(t) > 2]
    return tokens

def top_keywords(job_desc: str, k: int = 25) -> list[str]:
    toks = normalize(job_desc)
    c = Counter(toks)
    items = [w for w,_ in c.most_common(200) if not w.isdigit()]
    return items[:k]

def coverage(job_desc: str, cv_text: str, k: int = 25):
    keys = top_keywords(job_desc, k=k)
    cv_set = set(normalize(cv_text))
    hit = [w for w in keys if w in cv_set]
    miss = [w for w in keys if w not in cv_set]
    score = (len(hit) / len(keys) * 100) if keys else 0
    return score, hit, miss, keys
