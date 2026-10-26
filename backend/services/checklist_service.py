
from backend.supabase_client import supabase_admin
from backend.models.bookmark import ChecklistProgressItem
from backend.services.scheme_service import SchemeService


class ChecklistService:

    @staticmethod
    def get_progress(
        scheme_id: str,
        session_id: str = "default_citizen"
    ) -> ChecklistProgressItem:

        response = (
            supabase_admin.table("checklist_progress")
            .select("checked_indices")
            .eq("session_id", session_id)
            .eq("scheme_id", scheme_id)
            .limit(1)
            .execute()
        )

        checked_indices = []

        if response.data:
            checked_indices = (
                response.data[0].get("checked_indices") or []
            )

        # Find total required documents
        scheme = SchemeService.get_scheme_by_id(scheme_id)

        total_items = 0

        if scheme and scheme.documents:
            documents = (
                scheme.documents.get("en")
                or next(iter(scheme.documents.values()), [])
            )
            total_items = len(documents)

        # Keep only valid document indices
        checked_indices = sorted({
            int(index)
            for index in checked_indices
            if isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < total_items
        })

        percentage = 0.0

        if total_items > 0:
            percentage = round(
                len(checked_indices) / total_items * 100.0,
                1
            )

        return ChecklistProgressItem(
            scheme_id=scheme_id,
            checked_indices=checked_indices,
            total_items=total_items,
            progress_percentage=percentage,
            session_id=session_id
        )

    @staticmethod
    def save_progress(
        scheme_id: str,
        checked_indices: list[int],
        session_id: str = "default_citizen"
    ) -> ChecklistProgressItem:

        scheme = SchemeService.get_scheme_by_id(scheme_id)

        if not scheme:
            raise ValueError(
                f"Scheme '{scheme_id}' does not exist."
            )

        documents = (
            scheme.documents.get("en")
            or next(iter(scheme.documents.values()), [])
        )

        total_items = len(documents)

        valid_indices = sorted({
            int(index)
            for index in checked_indices
            if isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < total_items
        })

        (
            supabase_admin.table("checklist_progress")
            .upsert(
                {
                    "session_id": session_id,
                    "scheme_id": scheme_id,
                    "checked_indices": valid_indices,
                },
                on_conflict="session_id,scheme_id"
            )
            .execute()
        )

        return ChecklistService.get_progress(
            scheme_id,
            session_id
        )
