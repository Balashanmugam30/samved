"""ASR quality metrics, Indic text normalization, and noise profile simulation.

Implements Wagner-Fischer dynamic programming for exact Word Error Rate (WER)
and Character Error Rate (CER), along with Unicode NFC normalization for Indic scripts.
"""

import re
import unicodedata
from typing import List, Tuple
from app.simulation.models import (
    NoiseProfile,
    TokenAlignmentOp,
    WERMetricResult,
)


def normalize_indic_text(text: str) -> str:
    """Normalizes Indic and multilingual text for fair ASR evaluation.

    1. Unicode NFC composition (unifies decomposed matras/nuktas/viramas)
    2. Strips Western punctuation and Indic Danda (।, ॥)
    3. Removes zero-width joiners/non-joiners (\u200c, \u200d)
    4. Collapses whitespace and applies case-folding
    """
    if not text:
        return ""

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)

    # 2. Strip Zero-Width Joiner (ZWJ) and Zero-Width Non-Joiner (ZWNJ)
    normalized = normalized.replace("\u200c", "").replace("\u200d", "")

    # 3. Strip Indic Danda / Double Danda
    normalized = normalized.replace("।", " ").replace("॥", " ")

    # 4. Strip Western punctuation and symbols
    normalized = re.sub(r"[\.,!?:;\"'()\[\]{}<>/\\|@#$%^&*~`_+=—–\-]", " ", normalized)

    # 5. Case-fold (effective for English and transliterated Indic tokens)
    normalized = normalized.lower()

    # 6. Collapse multi-spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def compute_levenshtein_alignment(
    ref_tokens: List[str], hyp_tokens: List[str]
) -> Tuple[int, int, int, int, List[TokenAlignmentOp]]:
    """Calculates S, D, I, H and detailed token alignment via Wagner-Fischer DP.

    Returns:
        (substitutions, deletions, insertions, hits, alignment_ops)
    """
    n = len(ref_tokens)
    m = len(hyp_tokens)

    # dp[i][j] = min cost to transform ref_tokens[:i] to hyp_tokens[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i  # Deletions
    for j in range(m + 1):
        dp[0][j] = j  # Insertions

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                sub_cost = dp[i - 1][j - 1] + 1
                del_cost = dp[i - 1][j] + 1
                ins_cost = dp[i][j - 1] + 1
                dp[i][j] = min(sub_cost, del_cost, ins_cost)

    # Backtracking to reconstruct alignment operations
    i, j = n, m
    rev_ops: List[TokenAlignmentOp] = []
    substitutions = 0
    deletions = 0
    insertions = 0
    hits = 0

    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_tokens[i - 1] == hyp_tokens[j - 1]:
            rev_ops.append(
                TokenAlignmentOp(
                    ref_token=ref_tokens[i - 1],
                    hyp_token=hyp_tokens[j - 1],
                    op="match",
                )
            )
            hits += 1
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            rev_ops.append(
                TokenAlignmentOp(
                    ref_token=ref_tokens[i - 1],
                    hyp_token=hyp_tokens[j - 1],
                    op="sub",
                )
            )
            substitutions += 1
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            rev_ops.append(
                TokenAlignmentOp(
                    ref_token=ref_tokens[i - 1],
                    hyp_token="<eps>",
                    op="del",
                )
            )
            deletions += 1
            i -= 1
        else:
            rev_ops.append(
                TokenAlignmentOp(
                    ref_token="<eps>",
                    hyp_token=hyp_tokens[j - 1],
                    op="ins",
                )
            )
            insertions += 1
            j -= 1

    rev_ops.reverse()
    return substitutions, deletions, insertions, hits, rev_ops


def calculate_wer_cer(
    reference: str, hypothesis: str
) -> WERMetricResult:
    """Computes normalized Word Error Rate (WER) and Character Error Rate (CER).

    WER = (S + D + I) / N_ref
    CER = (S_c + D_c + I_c) / N_ref_c
    """
    norm_ref = normalize_indic_text(reference)
    norm_hyp = normalize_indic_text(hypothesis)

    ref_words = norm_ref.split() if norm_ref else []
    hyp_words = norm_hyp.split() if norm_hyp else []

    # 1. Word Error Rate calculation
    if not ref_words:
        # Edge case: empty reference
        if not hyp_words:
            wer = 0.0
            subs, dels, inss, hits, ops = 0, 0, 0, 0, []
        else:
            wer = float(len(hyp_words))
            subs, dels, inss, hits = 0, 0, len(hyp_words), 0
            ops = [TokenAlignmentOp(ref_token="<eps>", hyp_token=w, op="ins") for w in hyp_words]
    else:
        subs, dels, inss, hits, ops = compute_levenshtein_alignment(ref_words, hyp_words)
        wer = round((subs + dels + inss) / len(ref_words), 4)

    # 2. Character Error Rate calculation
    ref_chars = [c for c in norm_ref if not c.isspace()]
    hyp_chars = [c for c in norm_hyp if not c.isspace()]

    if not ref_chars:
        cer = 0.0 if not hyp_chars else float(len(hyp_chars))
        c_subs, c_dels, c_inss, c_hits = 0, 0, len(hyp_chars), 0
    else:
        c_subs, c_dels, c_inss, c_hits, _ = compute_levenshtein_alignment(ref_chars, hyp_chars)
        cer = round((c_subs + c_dels + c_inss) / len(ref_chars), 4)

    return WERMetricResult(
        wer=wer,
        cer=cer,
        substitutions=subs,
        deletions=dels,
        insertions=inss,
        hits=hits,
        reference_words=len(ref_words),
        hypothesis_words=len(hyp_words),
        reference_chars=len(ref_chars),
        hypothesis_chars=len(hyp_chars),
        normalized_reference=norm_ref,
        normalized_hypothesis=norm_hyp,
        alignment=ops,
    )


def simulate_noise_distortion(
    text: str, profile: NoiseProfile = NoiseProfile.CLEAN
) -> str:
    """Simulates realistic telephony and acoustic noise distortions on transcripts.

    Used by the simulation engine to test downstream safety and reasoning
    resilience against imperfect ASR transcripts.
    """
    if profile == NoiseProfile.CLEAN or not text:
        return text

    words = text.split()
    if not words:
        return text

    if profile == NoiseProfile.TELEPHONY_8KHZ:
        # Subtle consonant / bandpass acoustic confusion (e.g. s -> sh, n -> m)
        distorted = []
        for w in words:
            if len(w) > 4 and w.endswith("ing"):
                distorted.append(w[:-3] + "in")
            elif "sh" in w:
                distorted.append(w.replace("sh", "s", 1))
            else:
                distorted.append(w)
        return " ".join(distorted)

    elif profile == NoiseProfile.LOW_SNR_STREET:
        # Occasional dropped short tokens or ambient background filler
        distorted = []
        for idx, w in enumerate(words):
            # Drop very short unstressed words at low SNR
            if w.lower() in {"a", "an", "the", "ki", "ka"} and idx % 3 == 0:
                continue
            distorted.append(w)
        return " ".join(distorted)

    elif profile == NoiseProfile.PACKET_LOSS_BURST:
        # Simulates 5-10% packet drop: missing trailing word in longer sentences
        if len(words) > 5:
            return " ".join(words[:-1])
        return " ".join(words)

    return text
