from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatRequest
from app.services.ai_service import StableChatOrchestrator

logger = get_logger(__name__)

api_router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ChatRouteService:
    def __init__(self, db, get_openai_client):
        self.db = db
        self.get_openai_client = get_openai_client
        self.logger = get_logger(__name__)

    async def handle_guest_chat(self, request: Request, chat_request: ChatRequest, apartment: dict, branding: dict, session_id: str, proximity_response: str = ""):
        self.logger.log("handle_guest_chat", "handling guest chat request")
        if proximity_response:
            return proximity_response

        recent_messages = await self.db.chat_messages.find(
            {"session_id": session_id},
            {"content": 1, "type": 1, "timestamp": 1, "_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(length=None)
        recent_messages.reverse()

        orchestrator = StableChatOrchestrator(client_factory=self.get_openai_client)
        orchestrator_result = await orchestrator.respond(
            apartment=apartment,
            branding=branding,
            message=chat_request.message,
            session_id=session_id,
            history=recent_messages,
        )
        return orchestrator_result["response"]

    async def save_messages(self, apartment_id: str, session_id: str, user_message: str, assistant_response: str, client_ip: str):
        self.logger.log("save_messages", "persisting chat turn")
        user_chat_message = ChatMessage(
            apartment_id=apartment_id,
            message=user_message,
            response="",
            session_id=session_id,
            content=user_message,
            type="user",
            guest_ip=client_ip,
        )
        await self.db.chat_messages.insert_one(user_chat_message.dict())

        assistant_chat_message = ChatMessage(
            apartment_id=apartment_id,
            message="",
            response=assistant_response,
            session_id=session_id,
            content=assistant_response,
            type="assistant",
            guest_ip=client_ip,
        )
        await self.db.chat_messages.insert_one(assistant_chat_message.dict())
