"""Tests del value object IfiScore."""
import pytest
from domain.value_objects.ifi_score import IfiScore

def test_ifi_score_green():
    score = IfiScore(90.0)
    assert score.label == "green"

def test_ifi_score_yellow():
    score = IfiScore(70.0)
    assert score.label == "yellow"

def test_ifi_score_red():
    score = IfiScore(40.0)
    assert score.label == "red"

def test_ifi_score_invalid():
    with pytest.raises(ValueError):
        IfiScore(150.0)
