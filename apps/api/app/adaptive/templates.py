"""Versioned localized templates for deterministic adaptive actions.

Supports:
- ta-IN (Tamil)
- hi-IN (Hindi)
- en-IN (Indian English)
"""

from typing import Dict
from app.adaptive.models import AdaptiveAction

TEMPLATES: Dict[AdaptiveAction, Dict[str, str]] = {
    AdaptiveAction.SAFETY_CHECK: {
        "en-IN": "Please stay calm. Are you in immediate danger right now?",
        "ta-IN": "அமைதியாக இருங்கள். உங்களுக்கு இப்போது ஏதேனும் உடனடி ஆபத்து உள்ளதா?",
        "hi-IN": "कृपया शांत रहें। क्या आप इस समय किसी तात्कालिक खतरे में हैं?",
    },
    AdaptiveAction.ASK_IMMEDIATE_DANGER: {
        "en-IN": "Are you or anyone nearby in immediate physical danger right now?",
        "ta-IN": "உங்களுக்கோ அல்லது அருகில் இருப்பவர்களுக்கோ இப்போது உடனடி ஆபத்து உள்ளதா?",
        "hi-IN": "क्या आप या आपके आसपास कोई व्यक्ति इस समय तात्कालिक खतरे में है?",
    },
    AdaptiveAction.ASK_SAFE_TO_CONTINUE: {
        "en-IN": "Is it safe for you to continue speaking with me privately?",
        "ta-IN": "நீங்கள் என்னிடம் தொடர்ந்து தனியாக பேசுவது இப்போது பாதுகாப்பானதா?",
        "hi-IN": "क्या आपके लिए इस समय मुझसे अकेले में बात करना सुरक्षित है?",
    },
    AdaptiveAction.ASK_LOCATION: {
        "en-IN": "Can you share which city or district you are calling from so we can assist?",
        "ta-IN": "உங்களுக்கு உதவ, நீங்கள் எந்த ஊர் அல்லது மாவட்டத்தில் இருந்து அழைக்கிறீர்கள் என்று கூற முடியுமா?",
        "hi-IN": "सहायता के लिए, क्या आप बता सकते हैं कि आप किस शहर या जिले से बोल रहे हैं?",
    },
    AdaptiveAction.ASK_SUPPORT: {
        "en-IN": "Is there a trusted family member, friend, or counselor nearby who can support you?",
        "ta-IN": "உங்களுக்கு உதவ அருகில் ஏதேனும் நம்பிக்கையான குடும்பத்தினர் அல்லது நண்பர் இருக்கிறார்களா?",
        "hi-IN": "क्या आपके पास कोई विश्वसनीय परिजन या मित्र है जो इस समय आपका साथ दे सके?",
    },
    AdaptiveAction.ASK_RECENCY: {
        "en-IN": "Did this happen very recently today, or has it been going on for some time?",
        "ta-IN": "இது இன்று அண்மையில் நடந்ததா, அல்லது சில காலமாக நடந்து வருகிறதா?",
        "hi-IN": "क्या यह आज हाल ही में हुआ है, या कुछ समय से चल रहा है?",
    },
    AdaptiveAction.ASK_PREFERENCE: {
        "en-IN": "Would you prefer guidance on de-addiction counseling, or speaking directly with an officer?",
        "ta-IN": "உங்களுக்கு ஆலோசனை தகவல்கள் வேண்டுமா, அல்லது அதிகாரியிடம் பேச விரும்புகிறீர்களா?",
        "hi-IN": "क्या आप नशामुक्ति परामर्श की जानकारी चाहते हैं, या किसी अधिकारी से बात करना पसंद करेंगे?",
    },
    AdaptiveAction.ASK_NEXT_STEP: {
        "en-IN": "What is the most helpful next step for you right now?",
        "ta-IN": "இப்போது உங்களுக்கு மிகவும் உதவிகரமான அடுத்த படி என்னவாக இருக்கும்?",
        "hi-IN": "इस समय आपके लिए सबसे मददगार अगला कदम क्या हो सकता है?",
    },
    AdaptiveAction.OFFER_OPTIONS: {
        "en-IN": "We can connect you with rehabilitation support, legal counseling, or medical guidance. Which helps most?",
        "ta-IN": "நாங்கள் மறுவாழ்வு உதவி, சட்ட ஆலோசனை அல்லது மருத்துவ வழிகாட்டலை வழங்க முடியும். எது உங்களுக்கு உதவும்?",
        "hi-IN": "हम आपको पुनर्वास केंद्र, कानूनी सलाह या चिकित्सीय मार्गदर्शन से जोड़ सकते हैं। आपके लिए क्या उपयुक्त रहेगा?",
    },
    AdaptiveAction.PROVIDE_BRIEF_GUIDANCE: {
        "en-IN": "The National Helpline 14566 provides free and confidential assistance across India.",
        "ta-IN": "தேசிய உதவி எண் 14566 இந்தியா முழுவதும் இலவச மற்றும் ரகசிய உதவியை வழங்குகிறது.",
        "hi-IN": "राष्ट्रीय हेल्पलाइन 14566 पूरे भारत में निःशुल्क और गोपनीय सहायता प्रदान करती है।",
    },
    AdaptiveAction.ALLOW_SILENCE: {
        "en-IN": "Take your time. I am right here listening whenever you are ready.",
        "ta-IN": "நிதானமாக இருங்கள். நீங்கள் தயாராக இருக்கும்போது பேசலாம், நான் கேட்டுக்கொண்டுதான் இருக்கிறேன்.",
        "hi-IN": "आप आराम से समय लें। जब भी आप तैयार हों, मैं यहीं सुन रहा हूँ।",
    },
    AdaptiveAction.CLARIFY_AUDIO: {
        "en-IN": "I could not hear you clearly due to line noise. Could you please repeat that?",
        "ta-IN": "இணைப்பு தெளிவின்மை காரணமாக உங்கள் குரல் சரியாக கேட்கவில்லை. தயவுசெய்து மீண்டும் கூற முடியுமா?",
        "hi-IN": "लाइन में आवाज़ साफ़ नहीं आ रही है। क्या आप कृपया अपनी बात दोहरा सकते हैं?",
    },
    AdaptiveAction.HUMAN_HANDOFF: {
        "en-IN": "I am connecting you with a human counselor who can assist you directly. Please hold on.",
        "ta-IN": "உங்களுக்கு நேரடியாக உதவ மனித ஆலோசகரை இணைக்கிறேன். தயவுசெய்து காத்திருங்கள்.",
        "hi-IN": "मैं आपको एक मानव परामर्शदाता से जोड़ रहा हूँ जो सीधे आपकी सहायता करेंगे। कृपया बने रहें।",
    },
    AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS: {
        "en-IN": "I understand. Let us pause for a moment. Please take your time.",
        "ta-IN": "நான் புரிந்துகொள்கிறேன். சிறிது நேரம் இடைவெளி எடுப்போம். நீங்கள் நிதானமாக இருக்கலாம்.",
        "hi-IN": "मैं समझता हूँ। आइए थोड़ा रुकते हैं। आप आराम से समय लें।",
    },
    AdaptiveAction.END_GRACEFULLY: {
        "en-IN": "Thank you for reaching out to NHAA 14566. Please call back anytime if you need help. Take care.",
        "ta-IN": "தேசிய உதவி எண் 14566-ஐ தொடர்பு கொண்டதற்கு நன்றி. உதவி தேவைப்பட்டால் எப்போது வேண்டுமானாலும் அழைக்கவும். கவனமாக இருங்கள்.",
        "hi-IN": "राष्ट्रीय हेल्पलाइन 14566 पर संपर्क करने के लिए धन्यवाद। आवश्यकता होने पर कभी भी पुनः कॉल करें। अपना ध्यान रखें।",
    },
    AdaptiveAction.ACKNOWLEDGE: {
        "en-IN": "I hear you, and I understand what you are going through.",
        "ta-IN": "நான் கேட்கிறேன், நீங்கள் எதிர்கொள்ளும் சூழ்நிலையை என்னால் புரிந்து கொள்ள முடிகிறது.",
        "hi-IN": "मैं आपकी बात सुन रहा हूँ, और आपकी स्थिति को समझ रहा हूँ।",
    },
    AdaptiveAction.CLARIFY: {
        "en-IN": "Could you tell me a little more about what is happening?",
        "ta-IN": "என்ன நடக்கிறது என்பதைப் பற்றி இன்னும் கொஞ்சம் விளக்கமாக கூற முடியுமா?",
        "hi-IN": "क्या आप थोड़ा और बता सकते हैं कि क्या हो रहा है?",
    },
}


def get_template(action: AdaptiveAction, language: str = "en-IN") -> str:
    """Returns the localized template for an adaptive action with en-IN fallback."""
    action_templates = TEMPLATES.get(action, TEMPLATES[AdaptiveAction.CLARIFY])
    norm_lang = "ta-IN" if language.startswith("ta") else ("hi-IN" if language.startswith("hi") else "en-IN")
    return action_templates.get(norm_lang, action_templates["en-IN"])
