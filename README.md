# SchemeSaathi 🏛️🇮🇳

> **AI-powered citizen platform helping people discover government schemes, check eligibility, get personalized document checklists, and access multilingual application guidance with verified official links.**

---

## 🌟 Highlights & Features

- **⚡ Production-Grade FastAPI Backend**: Built with high performance, strict type validation (Pydantic v2), clean layered architecture, and SQLite persistence.
- **🔍 Schemes Discovery Engine**: Filter by category (`farmer`, `housing`, `health`, `women`, `education`, `worker`, `self-employed`), state, search keywords, and language.
- **🧠 Smart Multi-Criteria Eligibility Engine**: Evaluates citizen demographics (state, age, gender, occupation, location, income tier) against scheme rules to return match status, percentage score, criteria breakdown, and tailored guidance.
- **📋 Personalized Document Checklist & Progress**: Generates exact document requirements based on applicant profile and tracks/persists checklist item completion in SQLite across sessions.
- **💬 Multilingual AI Citizen Assistant**: Handles conversational inquiries in **English**, **Kannada (ಕನ್ನಡ)**, and **Hindi (हिन्दी)** with verified answers, suggested schemes, and official `.gov.in` / `.nic.in` portal links.
- **⭐ Bookmarks Persistence**: Save and manage bookmarked schemes per device or session.
- **🌐 Progressive Frontend Integration**: Connects dynamically to the backend API while maintaining 100% offline fallback compatibility.

---

## 🏗️ Project Architecture

```
SchemeSaathi/
├── backend/
│   ├── data/
│   │   ├── schemes_seed.json        # Verified dataset of Central & State schemes
│   │   └── translations_seed.json   # Multilingual UI localization strings (en, kn, hi)
│   ├── models/
│   │   ├── scheme.py                # Scheme, SchemeSummary, SchemeDetail models
│   │   ├── profile.py               # UserProfile, EligibilityCheck models
│   │   ├── bookmark.py              # Bookmark and ChecklistProgress models
│   │   └── chat.py                  # AI Assistant and FAQ models
│   ├── services/
│   │   ├── scheme_service.py        # Scheme querying, filtering, search
│   │   ├── eligibility_engine.py    # Multi-factor eligibility evaluation logic
│   │   ├── checklist_service.py     # Document checklist progress persistence
│   │   ├── bookmark_service.py      # Bookmarks management
│   │   └── ai_assistant.py          # Multilingual AI citizen assistant
│   ├── routers/
│   │   ├── schemes.py               # /api/schemes endpoints
│   │   ├── bookmarks.py             # /api/bookmarks endpoints
│   │   ├── checklist.py             # /api/checklist endpoints
│   │   ├── assistant.py             # /api/assistant endpoints
│   │   └── translations.py          # /api/translations endpoints
│   ├── tests/
│   │   ├── test_schemes.py          # Schemes catalog & filtering tests
│   │   ├── test_eligibility.py      # Eligibility engine & recommendation tests
│   │   ├── test_bookmarks.py        # Bookmarks & checklist progress tests
│   │   └── test_assistant.py        # AI chat & FAQ tests
│   ├── config.py                    # Environment and app configuration
│   ├── database.py                  # SQLite database connection & migrations
│   └── main.py                      # FastAPI application setup & static frontend mounting
├── index.html                       # Frontend application (connected to backend API)
├── run_backend.py                   # One-click server launcher script
├── requirements.txt                 # Python dependencies
└── README.md                        # Documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Bundled virtual environment `.venv` is included)

### 2. Run the Backend Server
Run the entrypoint script:
```powershell
.\.venv\Scripts\python.exe run_backend.py
```
Or with Uvicorn:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload
```

The server will start at:
- **Web App**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 REST API Reference

### 1. Schemes API
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/schemes` | List schemes with optional `category`, `query`, `state`, `language` filters |
| `GET` | `/api/schemes/{id}` | Get full scheme details including documents, application steps, and portals |
| `GET` | `/api/schemes/categories` | Get localized list of scheme categories |
| `POST` | `/api/schemes/check-eligibility` | Evaluate applicant demographics against scheme criteria |
| `POST` | `/api/schemes/recommend` | Get ranked, tailored recommendations for a citizen profile |

### 2. Bookmarks & Saved Schemes
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/bookmarks` | List all saved schemes for `session_id` |
| `POST` | `/api/bookmarks` | Save / bookmark a scheme |
| `DELETE` | `/api/bookmarks/{id}` | Remove a scheme from saved bookmarks |
| `GET` | `/api/bookmarks/status/{id}` | Check if scheme is bookmarked in this session |

### 3. Document Checklist & Progress
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/checklist/progress` | Get checked document indices & completion percentage for a scheme |
| `POST` | `/api/checklist/progress` | Save / update checked document indices |

### 4. AI Citizen Assistant
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/assistant/chat` | Multilingual citizen question answering (en, kn, hi) |
| `GET` | `/api/assistant/faq` | Frequently asked questions & verified answers |

### 5. Localization & Translations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/translations` | UI localization strings for specified language (`en`, `kn`, `hi`) |
| `GET` | `/api/translations/languages` | Supported languages and native labels |

### 6. System Health
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check reporting DB status, scheme count, and version |

---

## 🧪 Running Automated Tests

A comprehensive test suite with 17 automated tests covers all routers, models, eligibility rules, and services:

```powershell
.\.venv\Scripts\pytest.exe backend\tests -v
```

All 17 tests run and pass in ~1.0 second.

---

## 🛡️ Verified Official Portals Included

1. **PM-KISAN** — [pmkisan.gov.in](https://pmkisan.gov.in/)
2. **Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)** — [pmayg.nic.in](https://pmayg.nic.in/)
3. **Ayushman Bharat PM-JAY** — [beneficiary.nha.gov.in](https://beneficiary.nha.gov.in/)
4. **Pradhan Mantri Ujjwala Yojana (PMUY)** — [pmuy.gov.in](https://www.pmuy.gov.in/)
5. **National Scholarship Portal (NSP)** — [scholarships.gov.in](https://scholarships.gov.in/)
6. **PM SVANidhi (Street Vendor Microcredit)** — [pmsvanidhi.mohua.gov.in](https://pmsvanidhi.mohua.gov.in/)
7. **Sukanya Samriddhi Yojana (SSY)** — [indiapost.gov.in](https://www.indiapost.gov.in/)
8. **Atal Pension Yojana (APY)** — [pfrda.org.in](https://www.pfrda.org.in/)
9. **Pradhan Mantri MUDRA Yojana (PMMY)** — [mudra.org.in](https://www.mudra.org.in/)
10. **Gruha Lakshmi Scheme (Karnataka)** — [sevasindhugs.karnataka.gov.in](https://sevasindhugs.karnataka.gov.in/)
