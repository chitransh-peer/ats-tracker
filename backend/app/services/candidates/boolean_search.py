"""Boolean candidate search: AND / OR / NOT, "quoted phrases", (parentheses), * wildcards.

`python AND (django OR flask) NOT intern` -- terms next to each other mean AND,
AND binds tighter than OR, and a leading `-` is shorthand for NOT. Every term is
matched, case-insensitively, against the candidate's name, email, title, company,
location, source, skills, tags and (for Ceipal imports) the imported Ceipal
fields. Resume file contents are not indexed, so they are not searched.
"""

import re

from sqlalchemy import Text, and_, cast, func, not_, or_
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import ValidationAppError
from app.db.models.candidate import Candidate, CandidateTag
from app.db.models.ceipal import CeipalProfile

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"([^"]*)"|(-?[^\s()"]+))')
_MAX_TERMS = 30


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:  # only trailing whitespace is left
            break
        pos = match.end()
        open_paren, close_paren, phrase, word = match.groups()
        if open_paren:
            tokens.append(("(", "("))
        elif close_paren:
            tokens.append((")", ")"))
        elif phrase is not None:
            if phrase.strip():
                tokens.append(("term", phrase.strip()))
        elif word:
            upper = word.upper()
            if upper in ("AND", "OR", "NOT"):
                tokens.append((upper, upper))
            elif word.startswith("-") and len(word) > 1:
                tokens.append(("NOT", "NOT"))
                tokens.append(("term", word[1:]))
            else:
                tokens.append(("term", word))
    return tokens


def _term_condition(term: str) -> ColumnElement[bool]:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("*", "%")
    like = f"%{escaped}%"
    return or_(
        Candidate.full_name.ilike(like),
        Candidate.email.ilike(like),
        Candidate.current_title.ilike(like),
        Candidate.current_company.ilike(like),
        Candidate.location.ilike(like),
        Candidate.source.ilike(like),
        func.array_to_string(Candidate.skills, " ").ilike(like),
        Candidate.tags.any(CandidateTag.tag.ilike(like)),
        Candidate.ceipal_profile.has(cast(CeipalProfile.fields, Text).ilike(like)),
    )


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0
        self.terms = 0

    def _peek(self) -> str | None:
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def parse(self) -> ColumnElement[bool]:
        expr = self._or()
        if self._peek() == ")":
            raise ValidationAppError("Boolean search has a ')' with no matching '('.")
        return expr

    def _or(self) -> ColumnElement[bool]:
        parts = [self._and()]
        while self._peek() == "OR":
            self.pos += 1
            parts.append(self._and())
        return parts[0] if len(parts) == 1 else or_(*parts)

    def _and(self) -> ColumnElement[bool]:
        parts = [self._not()]
        while True:
            kind = self._peek()
            if kind == "AND":
                self.pos += 1
            elif kind not in ("term", "(", "NOT"):
                break
            parts.append(self._not())
        return parts[0] if len(parts) == 1 else and_(*parts)

    def _not(self) -> ColumnElement[bool]:
        if self._peek() == "NOT":
            self.pos += 1
            return not_(self._not())
        return self._atom()

    def _atom(self) -> ColumnElement[bool]:
        kind = self._peek()
        if kind == "term":
            self.terms += 1
            if self.terms > _MAX_TERMS:
                raise ValidationAppError(f"Boolean search is limited to {_MAX_TERMS} terms.")
            term = self.tokens[self.pos][1]
            self.pos += 1
            return _term_condition(term)
        if kind == "(":
            self.pos += 1
            expr = self._or()
            if self._peek() != ")":
                raise ValidationAppError("Boolean search has a '(' with no matching ')'.")
            self.pos += 1
            return expr
        raise ValidationAppError("Boolean search is missing a term near an AND / OR / NOT.")


def candidate_search_condition(search: str) -> ColumnElement[bool] | None:
    """The SQL condition for `search`, or None when it holds no terms."""
    tokens = _tokenize(search)
    if not tokens:
        return None
    return _Parser(tokens).parse()
