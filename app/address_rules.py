"""Deterministic, configuration-backed address risk rules for Task 1."""

from __future__ import annotations

import re


ROLE_SUFFIX_PATTERN = re.compile(r"[._-]")


def is_disposable_domain(domain: str, blocked_domains: set[str]) -> bool:
    """Match the domain itself or a listed registrable parent, never a bare TLD."""
    labels = domain.casefold().split(".")
    return any(".".join(labels[index:]) in blocked_domains for index in range(len(labels) - 1))


def is_role_account(
    local_part: str,
    role_accounts: set[str],
    allowed_suffixes: set[str],
) -> bool:
    """Detect exact roles plus conservative tag/region variants.

    Examples: ``info+ticket``, ``sales-eu`` and ``support.tr``.  A role word
    appearing later in a personal mailbox (``elif.support``) is not matched.
    """
    normalized = local_part.casefold()
    if normalized in role_accounts:
        return True

    if "+" in normalized:
        base, suffix = normalized.split("+", 1)
        return base in role_accounts and suffix in allowed_suffixes

    parts = ROLE_SUFFIX_PATTERN.split(normalized, maxsplit=1)
    return (
        len(parts) == 2
        and parts[0] in role_accounts
        and parts[1] in allowed_suffixes
    )


def bounded_levenshtein(left: str, right: str, limit: int) -> int | None:
    """Return edit distance up to *limit* without allocating a full matrix."""
    if abs(len(left) - len(right)) > limit:
        return None
    previous = list(range(len(right) + 1))
    for row_index, left_char in enumerate(left, 1):
        current = [row_index]
        row_minimum = row_index
        for column_index, right_char in enumerate(right, 1):
            value = min(
                current[-1] + 1,
                previous[column_index] + 1,
                previous[column_index - 1] + (left_char != right_char),
            )
            current.append(value)
            row_minimum = min(row_minimum, value)
        if row_minimum > limit:
            return None
        previous = current
    return previous[-1] if previous[-1] <= limit else None


def suggest_domain_typo(
    domain: str,
    exact_typos: dict[str, str],
    popular_domains: set[str],
) -> str | None:
    """Return an exact or uniquely-nearest conservative provider suggestion.

    Fuzzy matching is limited to known providers with the same TLD.  It never
    declares an address invalid; the caller emits only a suspicious finding.
    """
    normalized = domain.casefold()
    if normalized in exact_typos:
        return exact_typos[normalized]
    if normalized in popular_domains or normalized.count(".") != 1:
        return None

    name, tld = normalized.rsplit(".", 1)
    candidates: list[tuple[int, str]] = []
    for candidate in popular_domains:
        if candidate.count(".") != 1:
            continue
        candidate_name, candidate_tld = candidate.rsplit(".", 1)
        if candidate_tld != tld:
            continue
        limit = 1 if max(len(name), len(candidate_name)) < 10 else 2
        distance = bounded_levenshtein(name, candidate_name, limit)
        if distance is not None and distance > 0:
            candidates.append((distance, candidate))

    if not candidates:
        return None
    candidates.sort()
    best_distance = candidates[0][0]
    best = [candidate for distance, candidate in candidates if distance == best_distance]
    return best[0] if len(best) == 1 else None
