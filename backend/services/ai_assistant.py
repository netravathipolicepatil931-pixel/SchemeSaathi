
import re

from backend.supabase_client import supabase_admin
from backend.models.chat import ChatRequest, ChatResponse, FAQItem
from backend.models.scheme import SchemeSummary
from backend.services.scheme_service import SchemeService


class AIAssistantService:

    @staticmethod
    def detect_language(text: str, fallback: str = "en") -> str:
        if re.search(r"[\u0C80-\u0CFF]", text):
            return "kn"

        if re.search(r"[\u0900-\u097F]", text):
            return "hi"

        return fallback if fallback in ("en", "kn", "hi") else "en"

    @classmethod
    def answer_query(cls, request: ChatRequest) -> ChatResponse:

        lang = cls.detect_language(
            request.query,
            fallback=request.language
        )

        all_schemes = SchemeService.get_all_schemes()
        query_lower = request.query.lower()

        matched_schemes = []

        for s in all_schemes:

            names = [
                s.id,
                s.category,
                s.name.get("en", ""),
                s.name.get("kn", ""),
                s.name.get("hi", "")
            ]

            if any(
                name and name.lower() in query_lower
                for name in names
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "kisan", "farmer", "ಕೃಷಿ", "ರೈತ", "किसान"
                ])
                and s.id == "pm-kisan"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "house", "awaas", "ಮನೆ", "ಆವಾಸ್",
                    "मकान", "आवास"
                ])
                and s.id == "pmay-g"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "health", "hospital", "ayushman",
                    "ಆರೋಗ್ಯ", "ಆಯುಷ್ಮಾನ್",
                    "स्वास्थ्य", "आयुष्मान"
                ])
                and s.id == "ayushman-bharat"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "gas", "cylinder", "lpg", "ujjwala",
                    "ಉಜ್ವಲ", "उज्ज्वला"
                ])
                and s.id == "pm-ujjwala"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "scholarship", "student", "ವಿದ್ಯಾರ್ಥಿ",
                    "ವಿದ್ಯಾರ್ಥಿವೇತನ", "छात्रवृत्ति"
                ])
                and s.id == "national-scholarship"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "vendor", "svanidhi", "ಬೀದಿ ಬದಿ",
                    "ಸ್ವನಿಧಿ", "रेहड़ी", "स्वनिधि"
                ])
                and s.id == "pm-svanidhi"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "girl", "daughter", "sukanya",
                    "ಹೆಣ್ಣು ಮಗು", "ಸುಕನ್ಯಾ",
                    "सुकन्या", "बेटी"
                ])
                and s.id == "sukanya-samriddhi"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "pension", "atal", "ಪಿಂಚಣಿ",
                    "ಅಟಲ್", "पेंशन", "अटल"
                ])
                and s.id == "atal-pension"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "loan", "mudra", "ಸಾಲ",
                    "ಮುದ್ರಾ", "ऋण", "मुद्रा"
                ])
                and s.id == "pm-mudra"
            ):
                matched_schemes.append(s)

            elif (
                any(word in query_lower for word in [
                    "lakshmi", "karnataka", "2000",
                    "ಗೃಹಲಕ್ಷ್ಮಿ", "ಕರ್ನಾಟಕ", "गृह लक्ष्मी"
                ])
                and s.id == "gruha-lakshmi"
            ):
                matched_schemes.append(s)

        # Remove duplicate schemes
        seen = set()
        unique_schemes = []

        for scheme in matched_schemes:
            if scheme.id not in seen:
                seen.add(scheme.id)
                unique_schemes.append(scheme)

        # Fallback suggestions
        if not unique_schemes:
            unique_schemes = all_schemes[:3]

        suggested_summaries = []
        source_links = []

        for s in unique_schemes[:3]:

            name = s.name.get(lang) or s.name.get("en", s.id)
            desc = s.description.get(lang) or s.description.get("en", "")

            suggested_summaries.append(
                SchemeSummary(
                    id=s.id,
                    category=s.category,
                    color=s.color,
                    icon=s.icon,
                    url=s.url,
                    sourceUrl=s.sourceUrl or s.url,
                    ministry=s.ministry,
                    name=name,
                    names=s.name,
                    tagline=(
                        s.tagline.get(lang)
                        if s.tagline else None
                    ),
                    description=desc,
                    descriptions=s.description,
                    benefit=(
                        s.benefit.get(lang)
                        if s.benefit else None
                    )
                )
            )

            source_links.append({
                "title": name,
                "url": s.url
            })

        reply = cls._generate_localized_reply(
            request.query,
            unique_schemes,
            lang
        )

        quick_actions = cls._get_quick_actions(lang)

        # Save conversation to Supabase
        try:
            supabase_admin.table("assistant_logs").insert(
                {
                    "session_id": request.session_id,
                    "user_query": request.query,
                    "response": reply,
                    "language": lang
                }
            ).execute()

        except Exception as error:
            print(f"Assistant logging error: {error}")

        return ChatResponse(
            reply=reply,
            language=lang,
            suggested_schemes=suggested_summaries,
            quick_actions=quick_actions,
            source_links=source_links
        )

    @staticmethod
    def _generate_localized_reply(
        query: str,
        schemes: list,
        lang: str
    ) -> str:

        primary = schemes[0] if schemes else None

        if lang == "kn":

            if not primary:
                return (
                    "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ನೇರ ಯೋಜನೆ ಸಿಗಲಿಲ್ಲ. "
                    "ದಯವಿಟ್ಟು ಕೃಷಿ, ಆರೋಗ್ಯ, ವಸತಿ, "
                    "ವಿದ್ಯಾರ್ಥಿವೇತನ ಅಥವಾ ಸಾಲದ ಕುರಿತು ಕೇಳಿ."
                )

            name = primary.name.get(
                "kn",
                primary.name.get("en")
            )

            benefit = (
                primary.benefit.get("kn", "")
                if primary.benefit else ""
            )

            docs = primary.documents.get("kn", [])
            doc_str = "\n• " + "\n• ".join(docs[:3]) if docs else ""

            return (
                f"ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ಸಂಬಂಧಿಸಿದ ಮುಖ್ಯ ಯೋಜನೆ: **{name}**.\n\n"
                f"**ಪ್ರಮುಖ ಪ್ರಯೋಜನ:** {benefit}\n\n"
                f"**ಅಗತ್ಯವಿರುವ ಮುಖ್ಯ ದಾಖಲೆಗಳು:**{doc_str}\n\n"
                f"ನೀವು ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ({primary.url}) "
                f"ನೇರವಾಗಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಬಹುದು ಅಥವಾ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಬಹುದು."
            )

        elif lang == "hi":

            if not primary:
                return (
                    "क्षमा करें, आपके प्रश्न से सीधे मेल खाती योजना नहीं मिली। "
                    "कृपया कृषि, स्वास्थ्य, आवास, छात्रवृत्ति या ऋण के बारे में पूछें।"
                )

            name = primary.name.get(
                "hi",
                primary.name.get("en")
            )

            benefit = (
                primary.benefit.get("hi", "")
                if primary.benefit else ""
            )

            docs = primary.documents.get("hi", [])
            doc_str = "\n• " + "\n• ".join(docs[:3]) if docs else ""

            return (
                f"आपके प्रश्न से संबंधित प्रमुख योजना: **{name}**।\n\n"
                f"**मुख्य लाभ:** {benefit}\n\n"
                f"**ज़रूरी दस्तावेज़:**{doc_str}\n\n"
                f"आप आधिकारिक पोर्टल ({primary.url}) "
                f"पर सीधे आवेदन या पात्रता की जांच कर सकते हैं।"
            )

        else:

            if not primary:
                return (
                    "I couldn't find a direct match. "
                    "Try asking about agriculture, housing, "
                    "health cover, scholarships, women empowerment, "
                    "or business loans."
                )

            name = primary.name.get("en", primary.id)

            benefit = (
                primary.benefit.get("en", "")
                if primary.benefit else ""
            )

            docs = primary.documents.get("en", [])
            doc_str = "\n• " + "\n• ".join(docs[:3]) if docs else ""

            return (
                f"Based on your query, the most relevant "
                f"government scheme is **{name}**.\n\n"
                f"**Key Benefit:** {benefit}\n\n"
                f"**Required Documents Checklist:**{doc_str}\n\n"
                f"You can check your status and apply directly "
                f"via the official portal at {primary.url}."
            )

    @staticmethod
    def _get_quick_actions(lang: str) -> list[str]:

        if lang == "kn":
            return [
                "ರೈತರಿಗೆ ಯಾವ ಯೋಜನೆಗಳಿವೆ?",
                "ಆಯುಷ್ಮಾನ್ ಕಾರ್ಡ್ ಹೇಗೆ ಪಡೆಯುವುದು?",
                "ಮಹಿಳೆಯರಿಗೆ ಇರುವ ಯೋಜನೆಗಳು",
                "ವಿದ್ಯಾರ್ಥಿವೇತನಕ್ಕೆ ಅರ್ಜಿ ಹಾಕುವುದು ಹೇಗೆ?"
            ]

        elif lang == "hi":
            return [
                "किसानों के लिए कौन सी योजनाएँ हैं?",
                "आयुष्मान कार्ड कैसे बनवाएं?",
                "महिलाओं के लिए प्रमुख योजनाएं",
                "छात्रवृत्ति के लिए कौन से दस्तावेज़ चाहिए?"
            ]

        else:
            return [
                "Schemes for farmers",
                "How to apply for Ayushman Card?",
                "Schemes for women & mothers",
                "Documents for PM Kisan"
            ]

    @staticmethod
    def get_faqs(lang: str = "en") -> list[FAQItem]:

        if lang == "kn":
            return [
                FAQItem(
                    question="ಸ್ಕೀಮ್‌ಸಾಥಿ ಎಂದರೇನು?",
                    answer=(
                        "ಸ್ಕೀಮ್‌ಸಾಥಿ ಭಾರತೀಯ ನಾಗರಿಕರಿಗೆ ಕೇಂದ್ರ ಹಾಗೂ ರಾಜ್ಯ "
                        "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಸರಳ ಭಾಷೆಯಲ್ಲಿ ಅರಿಯಲು, "
                        "ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಲು ಮತ್ತು ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್‌ಗಳಿಗೆ "
                        "ಮಾರ್ಗದರ್ಶನ ನೀಡುವ ಉಚಿತ ವೇದಿಕೆಯಾಗಿದೆ."
                    ),
                    category="general"
                ),
                FAQItem(
                    question="ನನ್ನ ವೈಯಕ್ತಿಕ ಮಾಹಿತಿ ಸುರಕ್ಷಿತವೇ?",
                    answer=(
                        "ನೀವು ಚಾಟ್‌ನಲ್ಲಿ ನಮೂದಿಸುವ ಪ್ರಶ್ನೆಗಳು ಮತ್ತು "
                        "ಉತ್ತರಗಳನ್ನು ಸೇವೆಯ ಸುಧಾರಣೆಗಾಗಿ ಡೇಟಾಬೇಸ್‌ನಲ್ಲಿ "
                        "ಸಂಗ್ರಹಿಸಬಹುದು. ದಯವಿಟ್ಟು ಆಧಾರ್ ಸಂಖ್ಯೆ ಅಥವಾ "
                        "ಇತರ ಸೂಕ್ಷ್ಮ ಮಾಹಿತಿಯನ್ನು ನಮೂದಿಸಬೇಡಿ."
                    ),
                    category="privacy"
                ),
                FAQItem(
                    question="ಅರ್ಜಿ ಸಲ್ಲಿಸಲು ಶುಲ್ಕವಿದೆಯೇ?",
                    answer=(
                        "ಇಲ್ಲ, ಸ್ಕೀಮ್‌ಸಾಥಿ ಸಂಪೂರ್ಣವಾಗಿ ಉಚಿತ. "
                        "ಸರ್ಕಾರಿ ಪೋರ್ಟಲ್‌ಗಳ ಲಿಂಕ್‌ಗಳು ಇಲ್ಲಿ ಲಭ್ಯವಿರುತ್ತವೆ."
                    ),
                    category="application"
                )
            ]

        elif lang == "hi":
            return [
                FAQItem(
                    question="स्कीमसाथी क्या है?",
                    answer=(
                        "स्कीमसाथी एक निःशुल्क नागरिक सहायक मंच है "
                        "जो सरकारी योजनाओं की जानकारी, पात्रता जांच, "
                        "आवश्यक दस्तावेज़ों की सूची और आवेदन लिंक प्रदान करता है।"
                    ),
                    category="general"
                ),
                FAQItem(
                    question="क्या मेरी व्यक्तिगत जानकारी सुरक्षित है?",
                    answer=(
                        "आपके चैट प्रश्न और उत्तर डेटाबेस में संग्रहीत "
                        "किए जा सकते हैं। कृपया आधार नंबर या अन्य "
                        "संवेदनशील जानकारी चैट में दर्ज न करें।"
                    ),
                    category="privacy"
                ),
                FAQItem(
                    question="क्या आवेदन करने के लिए कोई शुल्क लगता है?",
                    answer=(
                        "नहीं, स्कीमसाथी निःशुल्क है। "
                        "सरकारी पोर्टलों के आवेदन लिंक उपलब्ध हैं।"
                    ),
                    category="application"
                )
            ]

        else:
            return [
                FAQItem(
                    question="What is SchemeSaathi?",
                    answer=(
                        "SchemeSaathi helps citizens discover government "
                        "welfare schemes, check preliminary eligibility, "
                        "and prepare document checklists in their language."
                    ),
                    category="general"
                ),
                FAQItem(
                    question="Is my personal data private and secure?",
                    answer=(
                        "Chat questions and responses may be stored in "
                        "our database. Please do not enter Aadhaar numbers, "
                        "passwords, or other sensitive personal information. "
                        "The current prototype is intended for local testing."
                    ),
                    category="privacy"
                ),
                FAQItem(
                    question="Are official links verified?",
                    answer=(
                        "SchemeSaathi provides links to government scheme "
                        "portals. Please verify the destination and current "
                        "eligibility requirements on the official website "
                        "before applying."
                    ),
                    category="security"
                )
            ]
