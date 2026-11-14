"""Tests for the Quick Start data layer.

The precomputed Quick Start result must stay consistent with the four
demonstration scenarios advertised on the landing page. These tests read the
generated artefacts, so they skip when the build scripts have not been run.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from src import quickstart

requires_quickstart = pytest.mark.skipif(
    not quickstart.available(), reason="quickstart analysis not built"
)
requires_templates = pytest.mark.skipif(
    not quickstart.template_path("template_specification.pdf").exists(),
    reason="templates not built",
)


@requires_quickstart
def test_precomputed_result_is_a_demo_with_two_manufacturers():
    result = quickstart.load_result()
    assert result.demo is True
    assert len(result.manufacturers) == 2
    assert {m.name for m in result.manufacturers} == {"Marmara Çelik", "Karadeniz Boru"}


@requires_quickstart
def test_marmara_is_compliant_on_every_criterion():
    result = quickstart.load_result()
    marmara = result.manufacturer("Marmara Çelik")
    assert marmara is not None
    assert marmara.counts.compliant == 5
    assert marmara.counts.non_compliant == 0
    assert marmara.counts.unverified == 0


@requires_quickstart
def test_karadeniz_shows_deviations_and_a_missing_standard():
    result = quickstart.load_result()
    karadeniz = result.manufacturer("Karadeniz Boru")
    assert karadeniz is not None
    assert karadeniz.counts.compliant == 1
    assert karadeniz.counts.non_compliant == 3
    assert karadeniz.counts.unverified == 1
    standard = karadeniz.criterion("standard")
    assert standard is not None
    assert standard.status.value == "unverified"


@requires_quickstart
def test_scenarios_cover_all_four_cases():
    result = quickstart.load_result()
    marmara = result.manufacturer("Marmara Çelik")
    karadeniz = result.manufacturer("Karadeniz Boru")
    assert marmara is not None and karadeniz is not None

    # Exact match: identical dimensions.
    assert marmara.criterion("dimensions").status.value == "compliant"
    # Semantic match: same grade written differently.
    grade = marmara.criterion("material_grade")
    assert grade.status.value == "compliant"
    assert grade.spec_display != grade.offer_display
    # Over-spec: offered wall is thicker than the minimum required.
    thickness = marmara.criterion("wall_thickness")
    assert thickness.status.value == "compliant"
    assert "3.2" in (thickness.offer_display or "")
    # Critical deviation: thinner nominal wall stated against a minimum.
    assert karadeniz.criterion("wall_thickness").status.value == "non_compliant"
    assert karadeniz.criterion("galvanizing").status.value == "non_compliant"
    assert karadeniz.criterion("material_grade").status.value == "non_compliant"


@requires_quickstart
def test_no_validation_issues_in_the_demo_result():
    assert quickstart.load_result().validation_issues == []


def test_quickstart_documents_are_declared():
    names = [name for _role, name, _desc in quickstart.QUICKSTART_DOCUMENTS]
    assert names == [
        "quickstart_specification.pdf",
        "quickstart_manufacturer_a.pdf",
        "quickstart_manufacturer_b.pdf",
    ]


@requires_templates
def test_templates_archive_contains_three_files():
    payload = quickstart.templates_archive()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = sorted(archive.namelist())
    assert names == [
        "field_guide.csv",
        "template_manufacturer.pdf",
        "template_specification.pdf",
    ]


@requires_quickstart
def test_dataset_archive_contains_pdfs_and_readme():
    payload = quickstart.dataset_archive()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = sorted(archive.namelist())
        readme = archive.read("README.txt").decode("utf-8")
    assert names == [
        "README.txt",
        "quickstart_manufacturer_a.pdf",
        "quickstart_manufacturer_b.pdf",
        "quickstart_specification.pdf",
    ]
    assert "SYNTHETIC DEMO DATA" in readme
    assert "no numeric matching score" in readme.lower() or "No numeric" in readme


def test_missing_files_raise_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(quickstart, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(quickstart.QuickStartUnavailable) as excinfo:
        quickstart.templates_archive()
    assert "build_templates.py" in str(excinfo.value)
