
from typing import List

from backend.supabase_client import supabase_admin
from backend.models.scheme import SchemeSummary
from backend.services.scheme_service import SchemeService


class BookmarkService:

    @staticmethod
    def get_bookmarks(
        session_id: str = "default_citizen",
        language: str = "en"
    ) -> List[SchemeSummary]:

        response = (
            supabase_admin.table("bookmarks")
            .select("scheme_id, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .execute()
        )

        results = []

        for row in response.data or []:
            scheme = SchemeService.get_scheme_detail(
                row["scheme_id"],
                language=language
            )

            if scheme:
                results.append(
                    SchemeSummary(
                        id=scheme.id,
                        category=scheme.category,
                        color=scheme.color,
                        icon=scheme.icon,
                        url=scheme.url,
                        sourceUrl=scheme.sourceUrl,
                        ministry=scheme.ministry,
                        name=scheme.name,
                        names=scheme.names,
                        tagline=scheme.tagline,
                        description=scheme.description,
                        descriptions=scheme.descriptions,
                        benefit=scheme.benefit,
                    )
                )

        return results

    @staticmethod
    def add_bookmark(
        scheme_id: str,
        session_id: str = "default_citizen"
    ) -> bool:

        scheme = SchemeService.get_scheme_by_id(scheme_id)

        if not scheme:
            return False

        (
            supabase_admin.table("bookmarks")
            .upsert(
                {
                    "session_id": session_id,
                    "scheme_id": scheme_id
                },
                on_conflict="session_id,scheme_id"
            )
            .execute()
        )

        return True

    @staticmethod
    def remove_bookmark(
        scheme_id: str,
        session_id: str = "default_citizen"
    ) -> bool:

        response = (
            supabase_admin.table("bookmarks")
            .delete()
            .eq("session_id", session_id)
            .eq("scheme_id", scheme_id)
            .execute()
        )

        return bool(response.data)

    @staticmethod
    def is_bookmarked(
        scheme_id: str,
        session_id: str = "default_citizen"
    ) -> bool:

        response = (
            supabase_admin.table("bookmarks")
            .select("id")
            .eq("session_id", session_id)
            .eq("scheme_id", scheme_id)
            .limit(1)
            .execute()
        )

        return bool(response.data)
