from supabase import create_client, Client
from .config import settings

class SupabaseClient:
    """
    Wrapper around Supabase for storing/retrieving flashcards.
    """
    def __init__(self):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def insert_flashcards(self, cards: list[dict]):
        # Upsert into "flashcards" and associate tags
        for card in cards:
            # Insert flashcard
            resp = (
                self.client
                .from_("flashcards")
                .insert({
                    "question": card["question"],
                    "answer":   card["answer"],
                    # "level":    card.get("level", "beginner")
                })
                .execute()
            )
            record = resp.data[0]
            flashcard_id = record["id"]

            # Insert tags and relationships
            for tag in card.get("tags", []):
                # Upsert tag
                tag_resp = (
                    self.client
                    .from_("tags")
                    .upsert({"name": tag}, on_conflict="name")
                    .execute()
                )
                tag_id = tag_resp.data[0]["id"]

                # Link table
                self.client.from_("flashcard_tags").insert({
                    "flashcard_id": flashcard_id,
                    "tag_id":       tag_id
                }).execute()
