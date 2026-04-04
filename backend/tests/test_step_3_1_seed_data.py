"""Tests for Step 3.1: Seed data definitions."""

import json

import pytest

from app.knowledge_pack.seed_data import (
    CLIMATE,
    CROP_DISEASES,
    CROPS,
    DISEASES,
    TREATMENTS,
)

VALID_DISEASE_TYPES = {"viral", "bacterial", "fungal", "pest", "nutritional", "environmental"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_DROUGHT = {"low", "medium", "high"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_EFFECTIVENESS = {"low", "medium", "high"}
VALID_SUSCEPTIBILITY = {"low", "medium", "high"}
VALID_DROUGHT_RISK = {"low", "medium", "high", "severe"}


class TestCrops:

    def test_count(self):
        assert len(CROPS) == 5

    def test_no_duplicate_names(self):
        names = [c["name"] for c in CROPS]
        assert len(names) == len(set(names))

    def test_no_duplicate_ids(self):
        ids = [c["id"] for c in CROPS]
        assert len(ids) == len(set(ids))

    def test_required_keys(self):
        required = {"id", "name", "scientific_name", "family", "growing_season",
                     "water_needs_mm_per_week", "drought_tolerance",
                     "region_suitability", "planting_notes", "harvest_notes"}
        for crop in CROPS:
            assert required.issubset(crop.keys()), f"Missing keys in crop {crop['name']}"

    def test_drought_tolerance_valid(self):
        for crop in CROPS:
            assert crop["drought_tolerance"] in VALID_DROUGHT, f"Invalid drought_tolerance for {crop['name']}"

    def test_expected_crops_present(self):
        names = {c["name"] for c in CROPS}
        assert names == {"cassava", "rice", "maize", "groundnut", "tomato"}


class TestDiseases:

    def test_count(self):
        assert len(DISEASES) == 15

    def test_no_duplicate_names(self):
        names = [d["name"] for d in DISEASES]
        assert len(names) == len(set(names))

    def test_no_duplicate_ids(self):
        ids = [d["id"] for d in DISEASES]
        assert len(ids) == len(set(ids))

    def test_required_keys(self):
        required = {"id", "name", "type", "symptoms_text", "visual_markers", "severity_scale"}
        for disease in DISEASES:
            assert required.issubset(disease.keys()), f"Missing keys in disease {disease['name']}"

    def test_type_valid(self):
        for disease in DISEASES:
            assert disease["type"] in VALID_DISEASE_TYPES, f"Invalid type for {disease['name']}"

    def test_severity_valid(self):
        for disease in DISEASES:
            assert disease["severity_scale"] in VALID_SEVERITIES, f"Invalid severity for {disease['name']}"

    def test_common_names_valid_json(self):
        for disease in DISEASES:
            if disease.get("common_names"):
                names = json.loads(disease["common_names"])
                assert isinstance(names, list)
                assert len(names) >= 1

    def test_visual_markers_non_empty(self):
        for disease in DISEASES:
            assert len(disease["visual_markers"]) > 50, f"visual_markers too short for {disease['name']}"

    def test_disease_distribution(self):
        """Verify: cassava 4, rice 3, maize 3, groundnut 3, tomato 2."""
        crop_counts = {}
        for cd in CROP_DISEASES:
            crop_id = cd["crop_id"]
            crop_name = next(c["name"] for c in CROPS if c["id"] == crop_id)
            crop_counts[crop_name] = crop_counts.get(crop_name, 0) + 1
        assert crop_counts["cassava"] == 4
        assert crop_counts["rice"] == 3
        assert crop_counts["maize"] == 3
        assert crop_counts["groundnut"] == 3
        assert crop_counts["tomato"] == 2


class TestCropDiseases:

    def test_count(self):
        assert len(CROP_DISEASES) == 15

    def test_valid_crop_ids(self):
        crop_ids = {c["id"] for c in CROPS}
        for cd in CROP_DISEASES:
            assert cd["crop_id"] in crop_ids

    def test_valid_disease_ids(self):
        disease_ids = {d["id"] for d in DISEASES}
        for cd in CROP_DISEASES:
            assert cd["disease_id"] in disease_ids

    def test_valid_susceptibility(self):
        for cd in CROP_DISEASES:
            assert cd["susceptibility"] in VALID_SUSCEPTIBILITY


class TestTreatments:

    def test_min_count(self):
        assert len(TREATMENTS) >= 30

    def test_at_least_two_per_disease(self):
        disease_ids = {d["id"] for d in DISEASES}
        for d_id in disease_ids:
            count = sum(1 for t in TREATMENTS if t["disease_id"] == d_id)
            disease_name = next(d["name"] for d in DISEASES if d["id"] == d_id)
            assert count >= 2, f"Disease '{disease_name}' has only {count} treatments"

    def test_valid_disease_ids(self):
        disease_ids = {d["id"] for d in DISEASES}
        for t in TREATMENTS:
            assert t["disease_id"] in disease_ids

    def test_difficulty_valid(self):
        for t in TREATMENTS:
            assert t["difficulty"] in VALID_DIFFICULTY, f"Invalid difficulty for treatment {t['id']}"

    def test_effectiveness_valid(self):
        for t in TREATMENTS:
            assert t["effectiveness"] in VALID_EFFECTIVENESS, f"Invalid effectiveness for treatment {t['id']}"

    def test_materials_needed_valid_json(self):
        for t in TREATMENTS:
            if t.get("materials_needed"):
                materials = json.loads(t["materials_needed"])
                assert isinstance(materials, list)
                assert len(materials) >= 1

    def test_no_duplicate_ids(self):
        ids = [t["id"] for t in TREATMENTS]
        assert len(ids) == len(set(ids))

    def test_has_organic_options(self):
        organic_count = sum(1 for t in TREATMENTS if t.get("is_organic"))
        assert organic_count >= 15, "Need substantial organic treatment options"


class TestClimate:

    def test_twelve_months(self):
        assert len(CLIMATE) == 12

    def test_all_months_present(self):
        months = {c["month"] for c in CLIMATE}
        assert months == set(range(1, 13))

    def test_region_is_casamance(self):
        for c in CLIMATE:
            assert c["region"] == "Casamance"

    def test_drought_risk_valid(self):
        for c in CLIMATE:
            assert c["drought_risk"] in VALID_DROUGHT_RISK

    def test_rainy_season_pattern(self):
        """June-October should have the most rainfall."""
        rainy = [c for c in CLIMATE if c["month"] in (7, 8, 9)]
        dry = [c for c in CLIMATE if c["month"] in (1, 2, 3)]
        assert all(r["rainfall_mm"] > 100 for r in rainy)
        assert all(d["rainfall_mm"] < 5 for d in dry)
