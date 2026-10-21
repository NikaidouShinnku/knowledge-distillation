USAGE = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "price": None,
}


def update_usage(usage, price=None):
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        USAGE[name] += getattr(usage, name, 0) or 0
    if price is not None:
        USAGE["price"] = (USAGE["price"] or 0) + price
    return dict(USAGE)


def get_usage():
    return dict(USAGE)
