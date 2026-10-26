from typing import Any
from pydantic import BaseModel, Field

class LocalizedText(BaseModel):
    en: str
    kn: str | None = None
    hi: str | None = None

    def get(self, lang: str = "en") -> str:
        if lang == "kn" and self.kn:
            return self.kn
        if lang == "hi" and self.hi:
            return self.hi
        return self.en

class EligibilityRule(BaseModel):
    min_age: int | None = 0
    max_age: int | None = 120
    genders: list[str] = Field(default_factory=lambda: ["woman", "man", "other"])
    locations: list[str] = Field(default_factory=lambda: ["rural", "urban"])
    occupations: list[str] = Field(default_factory=lambda: ["all"])
    income_tiers: list[str] = Field(default_factory=lambda: ["below-1", "1-2.5", "2.5-5", "above-5"])
    states: list[str] = Field(default_factory=lambda: ["all"])
    criteria: dict[str, str] = Field(default_factory=dict)

class Scheme(BaseModel):
    id: str
    category: str
    color: str = "#eaf3ec"
    icon: str = "sparkle"
    url: str
    sourceUrl: str | None = None
    ministry: str | None = None
    name: dict[str, str]
    tagline: dict[str, str] | None = None
    description: dict[str, str]
    benefit: dict[str, str] | None = None
    eligibility: EligibilityRule
    documents: dict[str, list[str]]
    steps: dict[str, list[str]]

class SchemeSummary(BaseModel):
    id: str
    category: str
    color: str
    icon: str
    url: str
    sourceUrl: str | None = None
    ministry: str | None = None
    name: str
    names: dict[str, str]
    tagline: str | None = None
    description: str
    descriptions: dict[str, str]
    benefit: str | None = None
    relevance_reason: str | None = None

class SchemeDetail(SchemeSummary):
    eligibility: EligibilityRule
    documents: list[str]
    documents_all: dict[str, list[str]]
    steps: list[str]
    steps_all: dict[str, list[str]]
