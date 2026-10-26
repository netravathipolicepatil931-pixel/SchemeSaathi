
import json
from typing import Optional

from backend.supabase_client import supabase
from backend.models.scheme import Scheme, SchemeSummary, SchemeDetail


class SchemeService:

    @staticmethod
    def get_all_schemes() -> list[Scheme]:
        response = (
            supabase.table("schemes")
            .select("data_json")
            .order("id")
            .execute()
        )

        schemes = []

        for row in response.data or []:
            data = row["data_json"]

            # Supabase JSONB normally returns a Python dictionary.
            if isinstance(data, str):
                data = json.loads(data)

            schemes.append(Scheme(**data))

        return schemes

    @staticmethod
    def get_scheme_by_id(scheme_id: str) -> Optional[Scheme]:
        response = (
            supabase.table("schemes")
            .select("data_json")
            .eq("id", scheme_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        data = response.data[0]["data_json"]

        if isinstance(data, str):
            data = json.loads(data)

        return Scheme(**data)

    @classmethod
    def filter_schemes(
        cls,
        query: Optional[str] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        language: str = "en",
    ) -> list[SchemeSummary]:

        all_schemes = cls.get_all_schemes()
        results: list[SchemeSummary] = []

        q = (query or "").strip().lower()
        cat = (category or "").strip().lower()

        for s in all_schemes:

            # Category filter
            if cat and cat != "all" and s.category.lower() != cat:
                continue

            # State filter
            if state and state.lower() not in ("all", "other"):
                scheme_states = [
                    st.lower() for st in s.eligibility.states
                ]

                if (
                    "all" not in scheme_states
                    and state.lower() not in scheme_states
                ):
                    continue

            # Search across localized scheme information
            if q:
                searchable_text = " ".join([
                    s.id,
                    s.category,
                    s.ministry or "",
                    *s.name.values(),
                    *(s.tagline.values() if s.tagline else []),
                    *s.description.values(),
                ]).lower()

                if q not in searchable_text:
                    continue

            name_text = (
                s.name.get(language)
                or s.name.get("en", s.id)
            )

            tagline_text = (
                s.tagline.get(language)
                if s.tagline else None
            )

            desc_text = (
                s.description.get(language)
                or s.description.get("en", "")
            )

            benefit_text = (
                s.benefit.get(language)
                if s.benefit else None
            )

            results.append(
                SchemeSummary(
                    id=s.id,
                    category=s.category,
                    color=s.color,
                    icon=s.icon,
                    url=s.url,
                    sourceUrl=s.sourceUrl or s.url,
                    ministry=s.ministry,
                    name=name_text,
                    names=s.name,
                    tagline=tagline_text,
                    description=desc_text,
                    descriptions=s.description,
                    benefit=benefit_text,
                )
            )

        return results

    @classmethod
    def get_scheme_detail(
        cls,
        scheme_id: str,
        language: str = "en"
    ) -> Optional[SchemeDetail]:

        s = cls.get_scheme_by_id(scheme_id)

        if not s:
            return None

        name_text = (
            s.name.get(language)
            or s.name.get("en", s.id)
        )

        tagline_text = (
            s.tagline.get(language)
            if s.tagline else None
        )

        desc_text = (
            s.description.get(language)
            or s.description.get("en", "")
        )

        benefit_text = (
            s.benefit.get(language)
            if s.benefit else None
        )

        docs = (
            s.documents.get(language)
            or s.documents.get("en", [])
        )

        steps = (
            s.steps.get(language)
            or s.steps.get("en", [])
        )

        return SchemeDetail(
            id=s.id,
            category=s.category,
            color=s.color,
            icon=s.icon,
            url=s.url,
            sourceUrl=s.sourceUrl or s.url,
            ministry=s.ministry,
            name=name_text,
            names=s.name,
            tagline=tagline_text,
            description=desc_text,
            descriptions=s.description,
            benefit=benefit_text,
            eligibility=s.eligibility,
            documents=docs,
            documents_all=s.documents,
            steps=steps,
            steps_all=s.steps,
        )
