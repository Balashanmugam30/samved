# SAMVED SVI Scoring Rules & Weights Specification (v1.0.0)

## Overview

The Stress Vulnerability Index (SVI) evaluates conversational utterances through versioned, deterministic rule sets.
Version configuration file: `apps/api/app/svi_rules/v1/weights.json`

## Category Definitions & Scoring Parameters

### 1. Immediate Safety (`immediate_safety`)
- **Max Category Weight**: 40 points
- **Description**: Active threats of physical violence, weapons, life endangerment, or acute physical assault.
- **Source**: Directly mapped from Phase 4 Deterministic Safety Signals or active keyword cues.
- **Critical Trigger**: Any CRITICAL safety signal activates the Critical Floor Override (`min SVI = 76`).
- **High Trigger**: Any HIGH safety signal activates the High Safety Floor (`min SVI = 51`).
- **Keywords (Multilingual)**:
  - English: `kill`, `knife`, `weapon`, `gun`, `beat me`, `hitting me`, `strangling`, `stab`, `attacked`, `die`, `bleeding`
  - Tamil: `கொன்னுடுவேன்`, `கத்தி`, `அடிக்கிறாங்க`, `துப்பாக்கி`, `வெட்டுவேன்`, `இரத்தம்`
  - Hindi: `मार डालेगा`, `चाकू`, `हथियार`, `बंदूक`, `पीट रहा`, `खून`

### 2. Coercion & Control (`coercion_control`)
- **Max Category Weight**: 25 points
- **Description**: Confinement, surveillance, movement restriction, forced financial dependency, communication blockage.
- **Keywords (Multilingual)**:
  - English: `locked me`, `took my phone`, `tracking me`, `won't let me leave`, `controls my money`, `threatened to take children`, `holds my passport`
  - Tamil: `பூட்டி வச்சுருக்காங்க`, `போன் புடிங்கிட்டாங்க`, `வெளியே விட மாட்டாங்க`, `பணம் தர மாட்டாங்க`
  - Hindi: `कमरे में बंद`, `फोन छीन लिया`, `बाहर नहीं जाने देता`, `पैसे नहीं देता`

### 3. Isolation & Support (`isolation_support`)
- **Max Category Weight**: 15 points
- **Description**: Complete absence of trusted support network, remote/isolated location, abandonment.
- **Keywords (Multilingual)**:
  - English: `no one to help`, `alone`, `nobody here`, `family abandoned`, `no friends`, `cut off`
  - Tamil: `யாரும் இல்ல`, `தனியா இருக்கேன்`, `உதவிக்கு ஆள் இல்ல`
  - Hindi: `कोई नहीं है`, `अकेली हूँ`, `मदद करने वाला कोई नहीं`

### 4. Distress & Overwhelm (`distress_overwhelm`)
- **Max Category Weight**: 20 points
- **Description**: Explicit expression of panic, hyperventilation, inability to cope, acute terror.
- **Keywords (Multilingual)**:
  - English: `panicking`, `can't breathe`, `extremely scared`, `terrified`, `crying uncontrollably`, `losing my mind`
  - Tamil: `ரொம்ப பயமா இருக்கு`, `மூச்சு விட முடியல`, `அழுதுட்டே இருக்கேன்`
  - Hindi: `बहुत डर लग रहा`, `सांस नहीं आ रही`, `घबराहट हो रही`

### 5. Help Barriers (`help_barriers`)
- **Max Category Weight**: 15 points
- **Description**: Practical barriers to reaching safety, including lack of transport, monitored communication, rural isolation.
- **Keywords (Multilingual)**:
  - English: `no money to travel`, `no transport`, `nowhere to go`, `phone is dying`, `watching my phone`, `cannot speak loudly`
  - Tamil: `போக இடம் இல்ல`, `காசு இல்ல`, `பேச முடியாது`
  - Hindi: `जाने की जगह नहीं`, `पैसे नहीं हैं`, `जोर से नहीं बोल सकती`

### 6. Protective Factors (`protective_factors`)
- **Max Category Weight**: Bounded reduction of up to -15 points
- **Description**: Verified safety factors (safe location, supportive ally present, police arriving).
- **Rule**: Protective factors CANNOT reduce SVI below the critical/high safety floors established by active safety signals.
- **Keywords (Multilingual)**:
  - English: `in a safe place`, `mother is with me`, `friend is here`, `police arrived`, `locked myself safely`, `at the hospital`
  - Tamil: `பாதுகாப்பா இருக்கேன்`, `அம்மா கூட இருக்காங்க`, `போலீஸ் வந்துட்டாங்க`
  - Hindi: `सुरक्षित जगह पर हूँ`, `माँ साथ में हैं`, `पुलिस आ गई`

## Temporal Recency Multipliers

| Context | Window | Weight |
|---------|--------|--------|
| `PRESENT` | Ongoing now / within call | 1.00 |
| `RECENT` | Today / few hours ago | 0.75 |
| `HISTORICAL` | Past months / past year | 0.35 |

## Negation Patterns
When an utterance contains negation modifiers before a keyword (e.g., `not`, `didn't`, `never`, `இல்லை`, `नहीं`), the match is invalidated to prevent false positives.
