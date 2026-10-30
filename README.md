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
│   │   ├── auth.py                  # Login, registration, OTP, and authenticated-user models
│   │   ├── scheme.py                # Scheme, SchemeSummary, SchemeDetail models
│   │   ├── profile.py               # UserProfile, EligibilityCheck models
│   │   ├── bookmark.py              # Bookmark and ChecklistProgress models
│   │   └── chat.py                  # AI Assistant and FAQ models
│   ├── services/
│   │   ├── scheme_service.py        # Scheme querying, filtering, search
│   │   ├── eligibility_engine.py    # Multi-factor eligibility evaluation logic
│   │   ├── checklist_service.py     # Document checklist progress persistence
│   │   ├── bookmark_service.py      # Bookmarks management
│   │   ├── ai_assistant.py          # Multilingual AI citizen assistant
│   │   └── auth_service.py          # Password hashing, OTP delivery, JWTs, audit history
│   ├── routers/
│   │   ├── auth.py                 # Registration, login, OTP, logout, login history
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

Open the app using the Web App URL above so the page and API share the same
origin. If you open `index.html` directly as a file, the backend must still be
running at `http://127.0.0.1:8000`; the login screen will show a connection
message if it is not reachable.

### Configure authentication

Authentication accounts, OTPs, login history, rate limits, and revoked tokens
are stored in the project's SQLite database at `DATABASE_PATH`. The auth tables
are created automatically when the backend starts. Supabase remains responsible
for the schemes catalog and does not need a service-role key for local
registration or login.

Set `JWT_SECRET_KEY` to a unique random value (for example,
`python -c "import secrets; print(secrets.token_urlsafe(48))"`). For Gmail OTP
delivery, enable 2-Step Verification and create a Google App Password, then set
`SMTP_USER`, `SMTP_PASSWORD`, and optionally `SMTP_FROM`. The default SMTP
server is Gmail on port 587 with STARTTLS. The OTP mailer uses Python's SMTP
support because this project runs FastAPI; Nodemailer is for Node.js projects.
For local UI testing only, set `DEBUG=True`, `AUTH_DEV_OTP=True`, and a strong
`JWT_SECRET_KEY`; verification codes will be shown in the page only for
loopback requests. Keep both development settings off in production.

The page provides account registration, email verification, password login,
and OTP login. OTPs expire after five minutes, are stored as bcrypt hashes,
and are limited to five verification attempts. JWTs are held for the browser
tab session and logout revokes the token server-side.

### Private document vault

The signed-in **My documents** area accepts PDF and JPEG/JPG files up to 2 MB
each. Google Gemini classifies uploads as Aadhaar, PAN, bank passbook, 10th
marksheet, or disability certificate; files the model cannot confidently
identify are not saved. The full file is sent to Google's Gemini API for
classification. SchemeSaathi does not retain the AI request. Google's current
Gemini API policy says prompts and contextual information are retained for
55 days for abuse monitoring, and flagged content may be reviewed by
authorized staff; see the [Gemini API data policy](https://ai.google.dev/gemini-api/docs/usage-policies).
The page discloses this and requires consent before each upload. AI identifies
document type only; it does not verify authenticity or validity.
The default model is `gemini-3.5-flash`; if Gemini returns a temporary
service-unavailable response or times out, the classifier tries
`gemini-3.8-flash`.

After identification, the file is encrypted before it is stored in the
project's SQLite database under its sanitized original filename. The filename
metadata is encrypted at rest as well. The mutable upload buffer is overwritten
and AI request payload references
are discarded after classification and storage (or on a failed upload).
Python and HTTP libraries may make transient internal copies that cannot be
guaranteed to be securely erased. The encrypted saved copy remains available
until deleted by the user. Documents require a valid sign-in and are isolated
by account. They can be downloaded or deleted from the vault, and are also
available in each scheme's application details. Configure `GEMINI_API_KEY`
and a persistent `DOCUMENT_ENCRYPTION_KEY` in `.env`; generate the latter
once with:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep the encryption key secret, back it up separately from the database, and
do not rotate it without decrypting and re-encrypting existing documents.
Changing or losing the key makes stored documents unreadable. The development
server uses HTTP; deploy behind HTTPS before accepting documents from remote
users, and protect both `.env` and database backups.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Create an account and send an email-verification OTP |
| `POST` | `/api/auth/login` | Validate password and send a sign-in OTP |
| `POST` | `/api/auth/verify-otp` | Verify registration/login OTP; returns a JWT after login verification |
| `POST` | `/api/auth/logout` | Revoke the authenticated JWT |
| `GET` | `/api/auth/me` | Validate the current JWT and return the user |
| `GET` | `/api/auth/login-history/{userId}` | Return up to 100 login events for the authenticated user |
| `GET` | `/api/documents/status` | Check whether document AI and encrypted storage are configured |
| `GET` | `/api/documents` | List the signed-in user's saved document metadata |
| `POST` | `/api/documents` | Classify and encrypt a PDF/JPEG upload (maximum 2 MB) |
| `GET` | `/api/documents/{id}/file` | Download a saved document |
| `DELETE` | `/api/documents/{id}` | Delete a saved document |

Login history stores the request IP, browser user-agent, inferred device class,
and a nullable location (null because no location provider is configured).
SQLite rate limits are persistent and atomic across backend workers sharing the
same database file. Registration allows up to ten attempts per IP per hour and
five per email per hour to reduce lockouts for people sharing a network. When a
limit is reached, the response includes a `Retry-After` header and the page
shows the approximate wait.

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
