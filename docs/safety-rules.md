# SAMVED — Deterministic Safety Rules Catalog (v1.0.0)

This document specifies the six versioned safety rules active in the SAMVED Safety Engine under `apps/api/app/safety_rules/v1/`.

---

## 1. RULE_THREAT_001 — Active Physical Violence & Assault
- **Rule ID**: `RULE_THREAT_001`
- **Version**: `v1.0.0`
- **Category**: `PHYSICAL_VIOLENCE`
- **Default Severity**: `HIGH`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Target Indicators**:
  - `en-IN`: "hitting me", "beating me", "trying to kill me", "breaking into my house", "choking me", "strangling me", "attacking me"
  - `ta-IN`: "அடிக்கிறார்", "அடிக்கிறான்", "கொல்ல பார்க்கிறார்", "வீட்டை உடைக்கிறார்", "கழுத்தை நெரிக்கிறார்", "தாக்குகிறார்"
  - `hi-IN`: "मार रहा है", "पीट रहा है", "जान से मारने की धमकी", "घर तोड़ रहा है", "गला दबा रहा है", "हमला कर रहा है"
- **Negative / False-Positive Safeguards**:
  - "I saw an action movie yesterday where they were hitting each other"
  - "My computer is crashing and breaking my workflow"
- **Human-in-the-loop Mandate**: Yes. Enforces supervisor review.

---

## 2. RULE_WEAPON_002 — Lethal Weapon Presence & Brandishing
- **Rule ID**: `RULE_WEAPON_002`
- **Version**: `v1.0.0`
- **Category**: `WEAPONS`
- **Default Severity**: `CRITICAL`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Compound Escalation**:
  - Requires co-occurrence of weapon keywords (`knife`, `gun`, `blade`, `sword`, `चाकू`, `बंदूक`, `கத்தி`, `துப்பாக்கி`) with active threat or possession verbs (`holding`, `threatening`, `breaking`, `मार डालेगा`, `பயமுறுத்துகிறார்`).
- **Negative / False-Positive Safeguards**:
  - "I am chopping onions with a kitchen knife"
  - "We bought a toy gun for Diwali"
  - "The doctor used a surgical blade"
- **Human-in-the-loop Mandate**: Yes. Operator intervention recommended.

---

## 3. RULE_SELF_HARM_003 — Imminent Suicide & Self-Harm Crisis
- **Rule ID**: `RULE_SELF_HARM_003`
- **Version**: `v1.0.0`
- **Category**: `SELF_HARM`
- **Default Severity**: `CRITICAL`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Target Indicators**:
  - `en-IN`: "end my life", "kill myself", "commit suicide", "swallow pills to die", "hang myself", "jump off the building"
  - `ta-IN`: "தற்கொலை", "உயிரை மாய்த்துக் கொள்ள", "செத்துப் போக போகிறேன்", "விஷம் குடிக்க", "தூக்கு போட்டு"
  - `hi-IN`: "आत्महत्या", "जान दे दूंगा", "मर जाना चाहता हूँ", "जहर खा लूंगा", "फांसी लगा लूंगा"
- **Negative / False-Positive Safeguards**:
  - "This assignment is killing me"
  - "I was reading an article about suicide prevention hotline"
- **Human-in-the-loop Mandate**: Yes. Immediate crisis de-escalation protocol.

---

## 4. RULE_CONFINEMENT_004 — Forced Confinement & Restraint
- **Rule ID**: `RULE_CONFINEMENT_004`
- **Version**: `v1.0.0`
- **Category**: `CONFINEMENT`
- **Default Severity**: `HIGH`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Target Indicators**:
  - `en-IN`: "locked me inside", "won't let me leave", "tied me up", "trapped in the room", "confining me"
  - `ta-IN`: "பூட்டி வைத்திருக்கிறார்கள்", "வெளியே விட மாட்டேன் என்கிறார்கள்", "கட்டி போட்டு வைத்திருக்கிறார்கள்"
  - `hi-IN`: "कमरे में बंद कर दिया", "बाहर नहीं जाने दे रहे", "बांध कर रखा है"
- **Negative / False-Positive Safeguards**:
  - "I accidentally locked myself out of my apartment"
  - "I am tied up with office meetings all day"
- **Human-in-the-loop Mandate**: Yes.

---

## 5. RULE_MEDICAL_005 — Acute Medical Emergency
- **Rule ID**: `RULE_MEDICAL_005`
- **Version**: `v1.0.0`
- **Category**: `MEDICAL`
- **Default Severity**: `HIGH`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Target Indicators**:
  - `en-IN`: "severe bleeding", "unconscious", "not breathing", "heart attack", "overdosed on drugs", "severe seizure"
  - `ta-IN`: "அதிக ரத்தப்போக்கு", "மயக்கம் அடைந்துவிட்டார்", "மூச்சு விட முடியவில்லை", "மாரடைப்பு"
  - `hi-IN`: "बहुत खून बह रहा है", "बेहोश हो गया", "सांस नहीं ले पा रहा", "दिल का दौरा", "ओवरडोज"
- **Negative / False-Positive Safeguards**:
  - "My heart skipped a beat when I heard the news"
  - "I got a minor paper cut with a little bleeding"
- **Human-in-the-loop Mandate**: Yes.

---

## 6. RULE_COERCION_006 — Blackmail, Coercion & Intimidation
- **Rule ID**: `RULE_COERCION_006`
- **Version**: `v1.0.0`
- **Category**: `COERCION`
- **Default Severity**: `ELEVATED`
- **Supported Languages**: `en-IN`, `ta-IN`, `hi-IN`
- **Target Indicators**:
  - `en-IN`: "threatening to ruin my family", "blackmailing me", "extorting money", "threatening to leak my photos"
  - `ta-IN`: "மிரட்டுகிறார்", "பணம் கேட்டு மிரட்டுகிறார்", "புகைப்படங்களை வெளியிடுவேன் என்று மிரட்டுகிறார்"
  - `hi-IN`: "धमका रहा है", "ब्लैकमेल कर रहा है", "पैसे मांग रहा है", "फोटो लीक करने की धमकी"
- **Human-in-the-loop Mandate**: Yes.
