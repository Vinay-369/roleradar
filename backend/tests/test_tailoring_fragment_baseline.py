"""
Regression coverage for the whole-document Truth Guard fragment scan.

The finalization failure
    '"Convolutional Neural Network (CNN) image...": Bullet has lost its leading
     action verb and degraded to an incomplete fragment'
was produced by validate_source_evidence_ledger, which scanned every final
delivery bullet with an EMPTY baseline. With an empty baseline the validator
assumes the source bullet carried a leading action verb, so any legitimate
source bullet that starts with a noun phrase (for example
"Convolutional Neural Network (CNN) image classification model ...") was
reported as having lost its verb.

These tests lock in the corrected behaviour:
- a source bullet that never had a leading action verb is not reported as
  having lost one;
- a bullet that genuinely lost the source bullet's leading action verb is
  still rejected.
"""
from __future__ import annotations

from app.modules.resume.models import CandidateProfile
from app.modules.resume.parsing.structurer import structure_resume_text
from app.modules.tailoring.validation import (
    detect_sentence_fragments_and_truncation,
    validate_source_evidence_ledger,
)

CNN_NOUN_PHRASE_BULLET = (
    "Convolutional Neural Network (CNN) image classification model trained on "
    "50,000 labeled images to reach 94% validation accuracy."
)

CNN_ACTION_BULLET = (
    "Built a Convolutional Neural Network (CNN) image classification model trained "
    "on 50,000 labeled images to reach 94% validation accuracy."
)


def _profile_with_project_bullet(bullet: str) -> CandidateProfile:
    source_text = (
        "Jordan Lee\n"
        "PROJECTS\n"
        "Vision Research\n"
        "Technologies: Python, TensorFlow\n"
        f"{bullet}\n"
    )
    return CandidateProfile.from_parsed_dict(
        structure_resume_text(source_text), source_text
    )


def test_noun_phrase_source_bullet_is_not_reported_as_losing_its_verb():
    """A source bullet that starts with a noun phrase must pass the ledger scan."""
    profile = _profile_with_project_bullet(CNN_NOUN_PHRASE_BULLET)
    final_parsed = {
        "projects_raw": [
            {
                "title": "Vision Research",
                "bullets": [CNN_NOUN_PHRASE_BULLET],
            }
        ]
    }

    report = validate_source_evidence_ledger(profile, final_parsed)

    assert report.fragment_violations == []
    assert report.is_valid
    assert report.accidental_loss_count == 0


def test_bullet_that_actually_lost_its_leading_verb_is_still_rejected():
    """Removing the source bullet's leading action verb must still fail."""
    profile = _profile_with_project_bullet(CNN_ACTION_BULLET)
    final_parsed = {
        "projects_raw": [
            {
                "title": "Vision Research",
                "bullets": [CNN_NOUN_PHRASE_BULLET],
            }
        ]
    }

    report = validate_source_evidence_ledger(profile, final_parsed)

    assert report.fragment_violations
    assert any(
        "lost its leading action verb" in violation
        for violation in report.fragment_violations
    )
    assert not report.is_valid


def test_fragment_detector_still_rejects_a_standalone_headless_fragment():
    """The direct detector must keep rejecting genuinely headless bullets."""
    violations = detect_sentence_fragments_and_truncation(
        CNN_ACTION_BULLET, CNN_NOUN_PHRASE_BULLET
    )

    assert any("lost its leading action verb" in item for item in violations)


def test_fragment_detector_accepts_a_verb_led_rewrite():
    """A verb-preserving rewrite must remain valid."""
    violations = detect_sentence_fragments_and_truncation(
        CNN_ACTION_BULLET,
        "Developed a CNN image classification model trained on 50,000 labeled "
        "images to reach 94% validation accuracy.",
    )

    assert violations == []
