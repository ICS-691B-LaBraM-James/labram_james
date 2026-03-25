from schemas import EEGFindings, BandPower


def assemble_findings(cognitive: dict, neurological: dict) -> EEGFindings:
    band = neurological.get("band_power", {})
    return EEGFindings(
        cognitive_state=cognitive.get("cognitive_state", "unknown"),
        emotional_state=cognitive.get("emotional_state", "unknown"),
        dominant_frequency_shift=neurological.get("dominant_frequency_shift", "none"),
        band_power=BandPower(
            delta=band.get("delta", "normal"),
            theta=band.get("theta", "normal"),
            alpha=band.get("alpha", "normal"),
            beta=band.get("beta", "normal"),
            gamma=band.get("gamma", "normal"),
        ),
        ad_risk_score=neurological.get("ad_risk_score", 0.0),
        seizure_risk=neurological.get("seizure_risk", "unknown"),
        confidence=cognitive.get("confidence", 0.0),
        notable_patterns=[
            f"Cognitive state: {cognitive.get('cognitive_state', 'N/A')}",
            f"Alertness score: {cognitive.get('alertness_score', 'N/A')}",
            f"Coherence: {neurological.get('coherence', 'N/A')}",
        ],
    )


def findings_to_text(findings: EEGFindings) -> str:
    bp = findings.band_power
    return (
        f"EEG analysis reveals {findings.dominant_frequency_shift} with "
        f"cognitive state assessed as {findings.cognitive_state} and "
        f"emotional state as {findings.emotional_state}. "
        f"Band power: delta={bp.delta}, theta={bp.theta}, alpha={bp.alpha}, "
        f"beta={bp.beta}, gamma={bp.gamma}. "
        f"Alzheimer's disease risk score is {findings.ad_risk_score:.2f} "
        f"with seizure risk rated as {findings.seizure_risk}. "
        f"Classification confidence: {findings.confidence:.0%}. "
        f"Notable patterns: {'; '.join(findings.notable_patterns)}."
    )
