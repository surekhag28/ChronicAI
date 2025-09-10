def deep_merge(left: dict | None, right: dict | None) -> dict:
    left, right = left or {}, right or {}
    out = dict(left)
    for k, v in right.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
