from typing import Optional
from backend.models.profile import (
    UserProfile,
    CriterionCheck,
    SchemeEligibilityResult,
    EligibilityCheckResponse,
)
from backend.models.scheme import Scheme
from backend.services.scheme_service import SchemeService

class EligibilityEngine:
    MESSAGES = {
        "en": {
            "eligible": "High match based on your profile",
            "likely_eligible": "Likely eligible — confirm specific conditions",
            "check_criteria": "Worth exploring — check exclusion rules",
            "not_eligible": "May not match your current profile",
            "age_pass": "Age ({age} yrs) fits the scheme criteria ({min_age}-{max_age} yrs).",
            "age_fail": "Age ({age} yrs) is outside the eligible range ({min_age}-{max_age} yrs).",
            "gender_pass": "Gender aligns with targeted beneficiaries.",
            "gender_fail": "This scheme is targeted exclusively for {target} applicants.",
            "location_pass": "Residence area ({location}) satisfies scheme eligibility.",
            "location_fail": "This scheme requires {target} residence; you selected {user}.",
            "occupation_pass": "Occupation ({occupation}) directly matches the target beneficiary group.",
            "occupation_fail": "Scheme is specifically designed for {target}; you selected {user}.",
            "state_pass": "Applicable in your state ({state}).",
            "state_fail": "This scheme is specific to residents of {target}.",
            "income_pass": "Income bracket aligns with eligibility ceiling.",
            "income_fail": "Higher income tiers may be subject to exclusions or lower priority.",
            "relevance_farmer": "You selected Farmer. Check land record (RTC/7-12) & exclusion conditions on the official portal.",
            "relevance_rural": "You selected Rural area. Check the official housing survey and local Panchayat list.",
            "relevance_woman": "Women applicants are directly prioritized for this scheme.",
            "relevance_student": "Student profile detected. Check academic criteria and scholarship deadlines.",
            "relevance_worker": "Worker / self-employed profile detected. Collateral-free benefits may apply.",
            "relevance_default": "This scheme may be a helpful starting point based on public guidelines."
        },
        "kn": {
            "eligible": "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್‌ಗೆ ಸೂಕ್ತ ಹೊಂದಾಣಿಕೆ",
            "likely_eligible": "ಅರ್ಹರಾಗಿರುವ ಸಾಧ್ಯತೆಯಿದೆ — ನಿಬಂಧನೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ",
            "check_criteria": "ಪರಿಶೀಲಿಸಲು ಯೋಗ್ಯ — ವಿನಾಯಿತಿ ನಿಯಮಗಳನ್ನು ನೋಡಿ",
            "not_eligible": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ವಿವರಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗದಿರಬಹುದು",
            "age_pass": "ವಯಸ್ಸು ({age} ವರ್ಷ) ಯೋಜನೆಯ ಅರ್ಹತಾ ಮಿತಿಯಲ್ಲಿದೆ ({min_age}-{max_age} ವರ್ಷ).",
            "age_fail": "ವಯಸ್ಸು ({age} ವರ್ಷ) ನಿಗದಿತ ಅರ್ಹತಾ ಮಿತಿಯ ಹೊರಗಿದೆ ({min_age}-{max_age} ವರ್ಷ).",
            "gender_pass": "ಲಿಂಗವು ಯೋಜನೆಯ ಗುರಿ ಫಲಾನುಭವಿಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ.",
            "gender_fail": "ಈ ಯೋಜನೆಯು ನಿರ್ದಿಷ್ಟವಾಗಿ {target} ಅರ್ಜಿದಾರರಿಗೆ ಮಾತ್ರ ಅನ್ವಯಿಸುತ್ತದೆ.",
            "location_pass": "ವಾಸಸ್ಥಳ ({location}) ಯೋಜನೆಯ ಅರ್ಹತೆಯನ್ನು ಪೂರೈಸುತ್ತದೆ.",
            "location_fail": "ಈ ಯೋಜನೆಗೆ {target} ವಾಸಸ್ಥಳ ಅಗತ್ಯವಿದೆ; ನೀವು {user} ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ.",
            "occupation_pass": "ಉದ್ಯೋಗ ({occupation}) ಗುರಿ ಫಲಾನುಭವಿಗಳಿಗೆ ನೇರವಾಗಿ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ.",
            "occupation_fail": "ಈ ಯೋಜನೆಯು {target} ಗಾಗಿ ರೂಪಿಸಲಾಗಿದೆ; ನೀವು {user} ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ.",
            "state_pass": "ನಿಮ್ಮ ರಾಜ್ಯದಲ್ಲಿ ({state}) ಅನ್ವಯವಾಗುತ್ತದೆ.",
            "state_fail": "ಈ ಯೋಜನೆಯು ನಿರ್ದಿಷ್ಟವಾಗಿ {target} ನಿವಾಸಿಗಳಿಗೆ ಮಾತ್ರ ಸೀಮಿತವಾಗಿದೆ.",
            "income_pass": "ಆದಾಯದ ಮಿತಿಯು ಯೋಜನೆಯ ಷರತ್ತುಗಳನ್ನು ಪೂರೈಸುತ್ತದೆ.",
            "income_fail": "ಹೆಚ್ಚಿನ ಆದಾಯ ವರ್ಗದವರಿಗೆ ವಿನಾಯಿತಿಗಳು ಅಥವಾ ಪ್ರತ್ಯೇಕ ನಿಯಮಗಳು ಅನ್ವಯಿಸಬಹುದು.",
            "relevance_farmer": "ನೀವು ರೈತ ಎಂದು ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ. ಜಮೀನು ಪಹಣಿ ಮತ್ತು ವಿನಾಯಿತಿ ನಿಯಮಗಳನ್ನು ಅಧಿಕೃತ ತಾಣದಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.",
            "relevance_rural": "ನೀವು ಗ್ರಾಮೀಣ ಪ್ರದೇಶ ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ. ಅಧಿಕೃತ ವಸತಿ ಸಮೀಕ್ಷೆ ಪಟ್ಟಿ ಮತ್ತು ನಿಯಮಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
            "relevance_woman": "ಮಹಿಳಾ ಅರ್ಜಿದಾರರಿಗೆ ಈ ಯೋಜನೆಯಲ್ಲಿ ಆದ್ಯತೆ ನೀಡಲಾಗುತ್ತದೆ.",
            "relevance_student": "ವಿದ್ಯಾರ್ಥಿ ಪ್ರೊಫೈಲ್. ಶೈಕ್ಷಣಿಕ ಅಂಕಗಳು ಮತ್ತು ಕೊನೆಯ ದಿನಾಂಕವನ್ನು ಪರಿಶೀಲಿಸಿ.",
            "relevance_worker": "ಕಾರ್ಮಿಕ / ಸ್ವಯಂ ಉದ್ಯೋಗಿ ಪ್ರೊಫೈಲ್. ಜಾಮೀನು ರಹಿತ ಸೌಲಭ್ಯಗಳು ಲಭ್ಯವಿರಬಹುದು.",
            "relevance_default": "ಸಾರ್ವಜನಿಕ ಮಾರ್ಗಸೂಚಿಗಳ ಪ್ರಕಾರ ಈ ಯೋಜನೆ ಪರಿಶೀಲಿಸಲು ಉತ್ತಮ ಆರಂಭ."
        },
        "hi": {
            "eligible": "आपकी प्रोफ़ाइल के अनुसार उच्च मिलान",
            "likely_eligible": "संभावित पात्र — विशिष्ट शर्तें जांचें",
            "check_criteria": "देखने लायक — अपात्रता नियम अवश्य जांचें",
            "not_eligible": "आपकी वर्तमान जानकारी से मेल नहीं खाता",
            "age_pass": "उम्र ({age} वर्ष) पात्रता सीमा ({min_age}-{max_age} वर्ष) के भीतर है।",
            "age_fail": "उम्र ({age} वर्ष) निर्धारित पात्रता सीमा ({min_age}-{max_age} वर्ष) से बाहर है।",
            "gender_pass": "लिंग लक्षित लाभार्थी समूह से मेल खाता है।",
            "gender_fail": "यह योजना विशेष रूप से {target} आवेदकों के लिए है।",
            "location_pass": "निवास क्षेत्र ({location}) योजना की पात्रता पूरी करता है।",
            "location_fail": "इस योजना के लिए {target} निवास आवश्यक है; आपने {user} चुना है।",
            "occupation_pass": "व्यवसाय ({occupation}) सीधे लक्षित समूह से मेल खाता है।",
            "occupation_fail": "यह योजना विशेष रूप से {target} के लिए है; आपने {user} चुना है।",
            "state_pass": "आपके राज्य ({state}) में लागू है।",
            "state_fail": "यह योजना विशेष रूप से {target} के निवासियों के लिए है।",
            "income_pass": "आय वर्ग पात्रता सीमा के अनुकूल है।",
            "income_fail": "उच्च आय वर्ग के लिए अपात्रता शर्तें लागू हो सकती हैं।",
            "relevance_farmer": "आपने किसान चुना है। खतौनी/भूलेख और अपात्रता नियम आधिकारिक साइट पर जांचें।",
            "relevance_rural": "आपने ग्रामीण क्षेत्र चुना है। आवास सर्वे सूची और ग्राम पंचायत रिकॉर्ड जांचें।",
            "relevance_woman": "महिला आवेदकों को इस योजना में प्रत्यक्ष प्राथमिकता दी जाती है।",
            "relevance_student": "विद्यार्थी प्रोफ़ाइल पहचानी गई। शैक्षणिक शर्तें और अंतिम तिथि जांचें।",
            "relevance_worker": "कामगार / स्वरोजगार प्रोफ़ाइल पहचानी गई। बिना गारंटी लाभ मिल सकते हैं।",
            "relevance_default": "यह योजना आधिकारिक दिशानिर्देशों के आधार पर देखने योग्य शुरुआत है।"
        }
    }

    @classmethod
    def evaluate_scheme(
        cls, scheme: Scheme, profile: UserProfile, language: str = "en"
    ) -> SchemeEligibilityResult:
        lang = language if language in ("en", "kn", "hi") else "en"
        msg = cls.MESSAGES[lang]

        score = 100.0
        breakdown: list[CriterionCheck] = []
        is_disqualified = False

        # 1. State Check
        if profile.state and profile.state.strip() and profile.state != "Other":
            scheme_states = [s.lower() for s in scheme.eligibility.states]
            if "all" not in scheme_states and profile.state.lower() not in scheme_states:
                score -= 40
                is_disqualified = True
                breakdown.append(CriterionCheck(
                    criterion="state",
                    passed=False,
                    details=msg["state_fail"].format(target=", ".join(scheme.eligibility.states))
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="state",
                    passed=True,
                    details=msg["state_pass"].format(state=profile.state)
                ))

        # 2. Age Check
        if profile.age is not None:
            min_a = scheme.eligibility.min_age or 0
            max_a = scheme.eligibility.max_age or 120
            if profile.age < min_a or profile.age > max_a:
                score -= 35
                is_disqualified = True
                breakdown.append(CriterionCheck(
                    criterion="age",
                    passed=False,
                    details=msg["age_fail"].format(age=profile.age, min_age=min_a, max_age=max_a)
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="age",
                    passed=True,
                    details=msg["age_pass"].format(age=profile.age, min_age=min_a, max_age=max_a)
                ))

        # 3. Gender Check
        if profile.gender and profile.gender.strip():
            target_genders = [g.lower() for g in scheme.eligibility.genders]
            if profile.gender.lower() not in target_genders:
                score -= 30
                is_disqualified = True
                breakdown.append(CriterionCheck(
                    criterion="gender",
                    passed=False,
                    details=msg["gender_fail"].format(target=", ".join(scheme.eligibility.genders))
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="gender",
                    passed=True,
                    details=msg["gender_pass"]
                ))

        # 4. Location Check (Rural / Urban)
        if profile.location and profile.location.strip():
            target_locs = [loc.lower() for loc in scheme.eligibility.locations]
            if profile.location.lower() not in target_locs:
                score -= 30
                is_disqualified = True
                breakdown.append(CriterionCheck(
                    criterion="location",
                    passed=False,
                    details=msg["location_fail"].format(target=", ".join(scheme.eligibility.locations), user=profile.location)
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="location",
                    passed=True,
                    details=msg["location_pass"].format(location=profile.location)
                ))

        # 5. Occupation Check
        if profile.occupation and profile.occupation.strip():
            target_occs = [occ.lower() for occ in scheme.eligibility.occupations]
            if "all" not in target_occs and profile.occupation.lower() not in target_occs:
                # If scheme targets a specific occupation (e.g. farmer or student) and user chose something else
                score -= 35
                is_disqualified = True
                breakdown.append(CriterionCheck(
                    criterion="occupation",
                    passed=False,
                    details=msg["occupation_fail"].format(target=", ".join(scheme.eligibility.occupations), user=profile.occupation)
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="occupation",
                    passed=True,
                    details=msg["occupation_pass"].format(occupation=profile.occupation)
                ))

        # 6. Income Check
        if profile.income and profile.income.strip():
            allowed_tiers = [t.lower() for t in scheme.eligibility.income_tiers]
            if profile.income.lower() not in allowed_tiers:
                score -= 20
                breakdown.append(CriterionCheck(
                    criterion="income",
                    passed=False,
                    details=msg["income_fail"]
                ))
            else:
                breakdown.append(CriterionCheck(
                    criterion="income",
                    passed=True,
                    details=msg["income_pass"]
                ))

        # Final Score clamping
        final_score = max(0.0, min(100.0, score))

        if is_disqualified or final_score < 40.0:
            status = "not_eligible"
        elif final_score >= 85.0:
            status = "eligible"
        elif final_score >= 65.0:
            status = "likely_eligible"
        else:
            status = "check_criteria"

        # Generate personalized relevance explanation
        relevance = cls._generate_relevance_reason(scheme, profile, lang)

        # Tailor document checklist
        docs = scheme.documents.get(lang) or scheme.documents.get("en", [])

        scheme_name = scheme.name.get(lang) or scheme.name.get("en", scheme.id)

        return SchemeEligibilityResult(
            scheme_id=scheme.id,
            scheme_name=scheme_name,
            category=scheme.category,
            match_status=status,
            match_score=final_score,
            relevance_reason=relevance,
            criteria_breakdown=breakdown,
            tailored_documents=docs,
            official_url=scheme.url,
        )

    @classmethod
    def _generate_relevance_reason(cls, scheme: Scheme, profile: UserProfile, lang: str) -> str:
        msg = cls.MESSAGES[lang]
        if not profile or (not profile.occupation and not profile.gender and not profile.location):
            return msg["relevance_default"]

        if scheme.id == "pm-kisan" and profile.occupation == "farmer":
            return msg["relevance_farmer"]
        if scheme.id == "pmay-g" and profile.location == "rural":
            return msg["relevance_rural"]
        if scheme.id in ("pm-ujjwala", "gruha-lakshmi", "sukanya-samriddhi") and profile.gender == "woman":
            return msg["relevance_woman"]
        if scheme.id == "national-scholarship" and profile.occupation == "student":
            return msg["relevance_student"]
        if scheme.id in ("pm-svanidhi", "atal-pension", "pm-mudra") and profile.occupation in ("worker", "self-employed"):
            return msg["relevance_worker"]

        if profile.occupation == "farmer" and "farmer" in scheme.eligibility.occupations:
            return msg["relevance_farmer"]
        if profile.location == "rural" and "rural" in scheme.eligibility.locations:
            return msg["relevance_rural"]
        if profile.gender == "woman" and "woman" in scheme.eligibility.genders:
            return msg["relevance_woman"]

        return msg["relevance_default"]

    @classmethod
    def evaluate_all(
        cls, profile: UserProfile, language: str = "en", scheme_id: Optional[str] = None
    ) -> EligibilityCheckResponse:
        all_schemes = SchemeService.get_all_schemes()
        results: list[SchemeEligibilityResult] = []

        for s in all_schemes:
            if scheme_id and s.id != scheme_id:
                continue
            res = cls.evaluate_scheme(s, profile, language)
            results.append(res)

        # Sort results: high match first, then by match_score descending
        order = {"eligible": 0, "likely_eligible": 1, "check_criteria": 2, "not_eligible": 3}
        results.sort(key=lambda r: (order.get(r.match_status, 4), -r.match_score))

        return EligibilityCheckResponse(
            total_evaluated=len(results),
            matching_schemes=results,
            user_profile=profile,
            language=language,
        )
