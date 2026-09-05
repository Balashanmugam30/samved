"""Unit tests for Phase 14 ASR WER/CER metrics and Indic text normalization."""

import pytest
from app.simulation.metrics import (
    calculate_wer_cer,
    compute_levenshtein_alignment,
    normalize_indic_text,
    simulate_noise_distortion,
)
from app.simulation.models import NoiseProfile


def test_normalize_indic_text():
    # Western punctuation and Indic danda stripping
    raw = "नमस्ते! मुझे सहायता चाहिए। क्या आप सुन रहे हैं?"
    norm = normalize_indic_text(raw)
    assert "!" not in norm
    assert "।" not in norm
    assert "?" not in norm
    assert "नमस्ते मुझे सहायता चाहिए क्या आप सुन रहे हैं" == norm

    # Unicode NFC normalization for Tamil
    tamil_raw = "வணக்கம், எனக்கு பயமாக இருக்கிறது..."
    tamil_norm = normalize_indic_text(tamil_raw)
    assert "," not in tamil_norm
    assert "..." not in tamil_norm
    assert "வணக்கம் எனக்கு பயமாக இருக்கிறது" == tamil_norm

    # Zero-width non-joiner stripping
    zwnj_text = "அ\u200Cவள்"
    assert normalize_indic_text(zwnj_text) == "அவள்"


def test_wer_cer_exact_match():
    ref = "Hello I need immediate assistance"
    hyp = "Hello I need immediate assistance"
    res = calculate_wer_cer(ref, hyp)

    assert res.wer == 0.0
    assert res.cer == 0.0
    assert res.hits == 5
    assert res.substitutions == 0
    assert res.deletions == 0
    assert res.insertions == 0


def test_wer_cer_substitutions_and_deletions():
    ref = "namaste mujhe emergency madad chahiye"
    hyp = "namaste mujhe madad chahiye"  # 1 deletion: "emergency"
    res = calculate_wer_cer(ref, hyp)

    assert res.deletions == 1
    assert res.hits == 4
    assert res.reference_words == 5
    assert res.wer == round(1 / 5, 4)


def test_wer_cer_indic_devanagari():
    ref = "नमस्ते मुझे सहायता चाहिए"
    hyp = "नमस्ते सहायता चाहिए"  # dropped 1 word: "मुझे" out of 4 words
    res = calculate_wer_cer(ref, hyp)

    assert res.wer == round(1 / 4, 4)
    assert res.hits == 3
    assert res.deletions == 1


def test_wer_cer_empty_cases():
    res1 = calculate_wer_cer("", "")
    assert res1.wer == 0.0
    assert res1.cer == 0.0

    res2 = calculate_wer_cer("test text", "")
    assert res2.wer == 1.0
    assert res2.deletions == 2

    res3 = calculate_wer_cer("", "inserted text")
    assert res3.wer == 2.0
    assert res3.insertions == 2


def test_simulate_noise_distortion():
    clean_text = "I am calling because I feel unsafe outside"

    # Clean profile returns unchanged
    assert simulate_noise_distortion(clean_text, NoiseProfile.CLEAN) == clean_text

    # Telephony 8kHz transforms
    telephony = simulate_noise_distortion(clean_text, NoiseProfile.TELEPHONY_8KHZ)
    assert isinstance(telephony, str)

    # Packet loss burst truncates trailing token if long
    packet_loss = simulate_noise_distortion(clean_text, NoiseProfile.PACKET_LOSS_BURST)
    assert len(packet_loss.split()) <= len(clean_text.split())
