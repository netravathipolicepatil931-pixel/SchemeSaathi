import pytest
from backend.database import init_db
from backend.routers.assistant import chat_with_assistant, get_faqs
from backend.routers.translations import get_translations, get_supported_languages
from backend.models.chat import ChatRequest

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_assistant_english_query():
    req = ChatRequest(
        query="How do I apply for PM Kisan and what documents are needed?",
        language="en",
        session_id="test_chat_session",
    )
    res = chat_with_assistant(req)
    assert res.language == "en"
    assert "pm-kisan" in [s.id for s in res.suggested_schemes]
    assert len(res.reply) > 20
    assert len(res.source_links) > 0

def test_assistant_kannada_query():
    req = ChatRequest(
        query="ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಆರೋಗ್ಯ ಕಾರ್ಡ್ ಹೇಗೆ ಪಡೆಯುವುದು?",
        language="kn",
        session_id="test_chat_session",
    )
    res = chat_with_assistant(req)
    assert res.language == "kn"
    assert len(res.suggested_schemes) > 0

def test_assistant_hindi_query():
    req = ChatRequest(
        query="पीएम आवास योजना ग्रामीण के लिए क्या पात्रता है?",
        language="hi",
        session_id="test_chat_session",
    )
    res = chat_with_assistant(req)
    assert res.language == "hi"
    assert len(res.suggested_schemes) > 0

def test_assistant_faqs():
    faqs = get_faqs(language="en")
    assert len(faqs) >= 2
    assert "SchemeSaathi" in faqs[0].question or "SchemeSaathi" in faqs[0].answer

def test_translations():
    tr = get_translations(language="kn")
    assert tr["language"] == "kn"
    assert "navHome" in tr["strings"]

    langs = get_supported_languages()
    assert len(langs) == 3
    assert any(l["code"] == "kn" for l in langs)
