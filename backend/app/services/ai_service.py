import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from agents import Agent, ModelSettings, Runner

from app.core.config import AppConfig
from app.core.logging import get_logger

backend_root = Path(__file__).resolve().parents[2]
load_dotenv(backend_root / ".env", override=False)


class BaseAIService:
    def __init__(self, logger=None) -> None:
        self.logger = logger or get_logger(__name__)
        self._bootstrap_environment()

    def _bootstrap_environment(self) -> None:
        config = AppConfig.from_environment()
        if config.openai_api_key:
            os.environ["OPENAI_API_KEY"] = config.openai_api_key
        if config.emergent_llm_key:
            os.environ["EMERGENT_LLM_KEY"] = config.emergent_llm_key
        if not os.getenv("OPENAI_BASE_URL"):
            os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def log(self, method_name: str, message: str, **kwargs) -> None:
        self.logger.log(method_name, message, **kwargs)

    def log_error(self, method_name: str, message: str, **kwargs) -> None:
        self.logger.error(method_name, message, **kwargs)


class PromptBuilder(BaseAIService):
    def build_system_prompt(self, apartment: Optional[Dict[str, Any]], branding: Optional[Dict[str, Any]]) -> str:
        self.log("build_system_prompt", "building prompt for apartment chat")
        brand_name = (branding or {}).get("brand_name", "My Host IQ")
        apartment_address = (apartment or {}).get("address", "") or ""
        apartment_city = self._extract_city(apartment_address)
        city_label = apartment_city or "this area"

        prompt_parts = [
            f"You are a helpful stay concierge for {brand_name}.",
            "Your job is to answer guest questions about the apartment, the stay, and local recommendations in the same city as the property.",
            "Be concise, factual, friendly, and predictable.",
            "Use plain text only. Do not use markdown formatting.",
            "If information is missing, say so clearly and offer the next best helpful step.",
            f"The property is in {city_label}.",
            "Stay within the scope of the apartment, the stay, and local recommendations for that city.",
            "If the guest asks about other cities, politely redirect to the local city or say that the assistant is designed for this property area.",
            "Always answer in the same language as the guest message."
        ]

        if apartment:
            description = apartment.get("description")
            if description:
                prompt_parts.append(f"Property description: {description}")
            if apartment_address:
                prompt_parts.append(f"Property address: {apartment_address}")

            check_in = apartment.get("check_in_time") or apartment.get("check_in_instructions")
            check_out = apartment.get("check_out_time") or apartment.get("check_out_instructions")
            if check_in:
                prompt_parts.append(f"Check-in info: {check_in}")
            if check_out:
                prompt_parts.append(f"Check-out info: {check_out}")

            wifi_network = apartment.get("wifi_network")
            wifi_password = apartment.get("wifi_password")
            wifi_instructions = apartment.get("wifi_instructions")
            if wifi_network or wifi_password or wifi_instructions:
                wifi_lines = []
                if wifi_network:
                    wifi_lines.append(f"Wi-Fi network: {wifi_network}")
                if wifi_password:
                    wifi_lines.append(f"Wi-Fi password: {wifi_password}")
                if wifi_instructions:
                    wifi_lines.append(f"Wi-Fi instructions: {wifi_instructions}")
                prompt_parts.append("Wi-Fi details: " + " | ".join(wifi_lines))

            rules = apartment.get("rules") or []
            if rules:
                prompt_parts.append("House rules: " + ", ".join(rules))

        prompt_parts.extend([
            "When answering local recommendations, prefer short, practical suggestions and mention that the guest can verify details locally.",
            "Keep each answer to a short paragraph or a small list of 3 bullets at most."
        ])
        return "\n".join(prompt_parts)

    def _extract_city(self, address: str) -> str:
        if not address:
            return ""
        parts = [part.strip() for part in address.split(",") if part.strip()]
        for index, part in enumerate(parts):
            if any(char.isdigit() for char in part[:10]):
                continue
            if len(part) <= 8 and any(char.isdigit() for char in part) and len([char for char in part if char.isdigit()]) >= 2:
                continue
            if index == len(parts) - 1 and len(parts) > 2:
                continue
            if len(part) >= 3:
                return part
        if len(parts) >= 2:
            fallback = parts[-2].strip()
            if not any(char.isdigit() for char in fallback):
                return fallback
        if len(parts) == 3:
            return parts[1].strip()
        return ""


class MessageComposer(BaseAIService):
    def build_messages(self, system_prompt: str, message: str, history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
        self.log("build_messages", "building chat message history")
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for item in history[-8:]:
                role = item.get("type")
                content = item.get("content") or item.get("message") or item.get("response") or ""
                if not content:
                    continue
                if role == "assistant":
                    messages.append({"role": "assistant", "content": str(content)})
                else:
                    messages.append({"role": "user", "content": str(content)})
        messages.append({"role": "user", "content": message})
        return messages


class ResponseFormatter(BaseAIService):
    def detect_language(self, message: str) -> str:
        text = (message or "").lower()
        if any(token in text for token in ["hola", "gracias", "como", "donde", "puedo", "ayuda", "estancia"]):
            return "es"
        if any(token in text for token in ["bonjour", "merci", "comment", "où", "pouvez", "aide", "séjour"]):
            return "fr"
        if any(token in text for token in ["hallo", "danke", "hilfe", "aufenthalt"]) and not any(token in text for token in ["where", "wifi", "password", "check-in", "check in"]):
            return "de"
        if any(token in text for token in ["ciao", "grazie", "come", "dove", "puoi", "aiuto", "soggiorno"]):
            return "it"
        if any(token in text for token in ["hvala", "kako", "gdje", "možete", "pomoc", "boravak"]):
            return "bs"
        return "en"

    def build_fallback_response(self, message: str, apartment: Optional[Dict[str, Any]], language: str) -> str:
        self.log("build_fallback_response", "using deterministic fallback response")
        if language == "es":
            return "Puedo ayudar con tu estancia. No he podido contactar con el servicio de IA en este momento, así que estoy usando una respuesta segura. Revisa los datos del apartamento o contacta con el anfitrión para información específica."
        if language == "fr":
            return "Je peux aider pour votre séjour. Je n’ai pas pu joindre le service d’IA pour l’instant, donc j’utilise une réponse de secours. Vérifiez les détails de l’appartement ou contactez l’hôte pour des informations précises."
        if language == "de":
            return "Ich kann bei Ihrem Aufenthalt helfen. Ich konnte den KI-Dienst gerade nicht erreichen und verwende daher eine sichere Ausweichantwort. Bitte prüfen Sie die Apartmentdetails oder kontaktieren Sie den Gastgeber für spezifische Informationen."
        if language == "it":
            return "Posso aiutarti con il tuo soggiorno. Non sono riuscito a contattare il servizio AI in questo momento, quindi sto usando una risposta di sicurezza. Controlla i dettagli dell’appartamento o contatta l’host per informazioni specifiche."
        if language == "bs":
            return "Mogu vam pomoći sa vašim boravkom. Trenutno nisam mogao da kontaktiram AI uslugu, pa koristim sigurnosni odgovor. Provjerite detalje apartmana ili kontaktirajte domaćina za konkretnije informacije."
        return "I can help with your stay. I could not reach the AI service at the moment, so I am using a safe fallback response. Please check the apartment details or contact the host for specific information."


class StableChatOrchestrator(BaseAIService):
    def __init__(self, client=None, client_factory=None, model: str = "gpt-4o-mini", logger=None) -> None:
        super().__init__(logger=logger)
        self.client = client
        self.client_factory = client_factory
        self.model = model
        self.temperature = 0.2
        self.max_tokens = 700
        self.top_p = 1.0
        self.presence_penalty = 0.0
        self.frequency_penalty = 0.0
        self.timeout = 15.0
        self.prompt_builder = PromptBuilder(logger=logger)
        self.message_composer = MessageComposer(logger=logger)
        self.response_formatter = ResponseFormatter(logger=logger)

    def _get_client(self):
        if self.client is not None:
            return self.client
        if self.client_factory is not None:
            return self.client_factory()
        raise ValueError("No OpenAI client or client factory configured")

    def _build_agent(self, system_prompt: str) -> Agent:
        model_settings = ModelSettings(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
        )
        return Agent(
            name="stay_concierge",
            instructions=system_prompt,
            model=self.model,
            model_settings=model_settings,
        )

    async def _respond_with_legacy_client(self, message: str, apartment: Optional[Dict[str, Any]], language: str) -> str:
        client = self._get_client()
        if client is None:
            raise ValueError("legacy client unavailable")
        if hasattr(client, "chat") and hasattr(client.chat, "completions") and hasattr(client.chat.completions, "create"):
            await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.prompt_builder.build_system_prompt(apartment, None)}, {"role": "user", "content": message}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                presence_penalty=self.presence_penalty,
                frequency_penalty=self.frequency_penalty,
            )
            raise RuntimeError("legacy client path is not intended for this environment")
        raise RuntimeError("legacy client interface not supported")

    def _extract_response_text(self, result: Any) -> str:
        if result is None:
            return ""

        for attr in ["final_output", "final_output_text", "output_text"]:
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if hasattr(result, "final_output_as"):
            try:
                return str(result.final_output_as())
            except TypeError:
                pass

        if hasattr(result, "to_input_list"):
            try:
                return str(result.to_input_list())
            except Exception:
                pass

        return str(result)

    async def respond(
        self,
        apartment: Optional[Dict[str, Any]],
        branding: Optional[Dict[str, Any]],
        message: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.log("respond", "starting chat orchestration")
        language = self.response_formatter.detect_language(message)
        system_prompt = self.prompt_builder.build_system_prompt(apartment, branding)
        if history:
            history_context = "\n".join(
                f"{item.get('type', 'user')}: {item.get('content') or item.get('message') or item.get('response') or ''}" for item in history[-6:]
            )
            system_prompt = f"{system_prompt}\n\nConversation history:\n{history_context}"

        try:
            if self.client is not None:
                await self._respond_with_legacy_client(message, apartment, language)
            agent = self._build_agent(system_prompt)
            result = await Runner.run(starting_agent=agent, input=message)
            response_text = self._extract_response_text(result)
            if not response_text or not response_text.strip():
                raise ValueError("empty output")
            used_fallback = False
        except Exception as exc:
            self.log_error("respond", "model request failed", error=str(exc))
            response_text = self.response_formatter.build_fallback_response(message, apartment, language)
            used_fallback = True

        return {
            "response": response_text,
            "session_id": session_id,
            "language": language,
            "used_fallback": used_fallback,
            "model": self.model,
        }
