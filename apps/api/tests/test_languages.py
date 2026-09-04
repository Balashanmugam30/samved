from app.schemas.languages import LanguageCode, get_language_info


def test_language_code_parsing():
    assert LanguageCode.from_str("ta-IN") == LanguageCode.TA
    assert LanguageCode.from_str("tamil") == LanguageCode.TA
    assert LanguageCode.from_str("Tamil") == LanguageCode.TA
    assert LanguageCode.from_str("hi-IN") == LanguageCode.HI
    assert LanguageCode.from_str("hindi") == LanguageCode.HI
    assert LanguageCode.from_str("en-IN") == LanguageCode.EN
    assert LanguageCode.from_str("English") == LanguageCode.EN
    assert LanguageCode.from_str("unknown") == LanguageCode.UNKNOWN
    assert LanguageCode.from_str(None) == LanguageCode.UNKNOWN


def test_language_registry_metadata():
    info_ta = get_language_info(LanguageCode.TA)
    assert info_ta.name == "Tamil"
    assert info_ta.native_name == "தமிழ்"
    assert info_ta.sarvam_code == "ta-IN"

    info_hi = get_language_info(LanguageCode.HI)
    assert info_hi.name == "Hindi"
    assert info_hi.native_name == "हिन्दी"
    assert info_hi.sarvam_code == "hi-IN"

    info_en = get_language_info(LanguageCode.EN)
    assert info_en.name == "Indian English"
    assert info_en.sarvam_code == "en-IN"