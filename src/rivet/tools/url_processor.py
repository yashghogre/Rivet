import re


def check_url_validity(url: str) -> bool:
    url_pattern = re.compile(
        r"^(https?:\/\/)"
        r"(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})"
        r"(:[0-9]{1,5})?"
        r"(\/[^\s]*)?$"
    )
    return bool(url_pattern.match(url))
