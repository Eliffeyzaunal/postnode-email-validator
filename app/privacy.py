import hashlib


def email_hash(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode("utf-8")).hexdigest()


def mask_email(value: str | None) -> str:
    if not value:
        return "***"
    if "@" not in value:
        return "***"
    local, domain = value.rsplit("@", 1)
    if not local:
        masked_local = "***"
    elif len(local) == 1:
        masked_local = f"{local[0]}***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain.casefold()}"

