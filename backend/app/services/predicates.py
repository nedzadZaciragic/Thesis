from typing import Any, Dict, Optional


class ChatPredicates:
    @staticmethod
    def requires_local_recommendations(message: str, apartment: Optional[Dict[str, Any]]) -> bool:
        lowered = (message or "").lower()
        if not apartment:
            return False
        local_keywords = [
            "nightlife", "night life", "bars", "clubs", "pubs", "party", "drink",
            "restaurants", "food", "eat", "dining", "cafes", "coffee",
            "activities", "things to do", "attractions", "visit", "see",
            "shopping", "buy", "stores", "markets"
        ]
        return any(keyword in lowered for keyword in local_keywords)

    @staticmethod
    def is_follow_up_question(message: str) -> bool:
        lowered = (message or "").lower()
        return any(token in lowered for token in ["how", "when", "where", "what", "which", "who", "why"])
