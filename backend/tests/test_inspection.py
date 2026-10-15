from pathlib import Path
import pytest
from app.inspection.dataset import create_industrial_inspection_dataset
from app.inspection.pipeline import VisionInspectionEngine, InspectionPrediction


@pytest.fixture(scope="session")
def inspection_data(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("inspection_data")
    dataset = create_industrial_inspection_dataset(tmp_dir)
    return dataset


def test_inspection_acceptable_part(inspection_data):
    engine = VisionInspectionEngine()
    normal_samples = [s for s in inspection_data["manifest"] if s["ground_truth"] == "ACCEPTABLE"]
    assert len(normal_samples) > 0

    first_normal = normal_samples[0]
    result = engine.analyze_file(first_normal["filepath"])

    assert result.prediction == InspectionPrediction.ACCEPTABLE
    assert result.anomaly_score < 0.35
    assert result.confidence > 0.60
    assert result.defect_count == 0
    assert result.annotated_image_b64 is not None
    assert result.annotated_image_b64.startswith("data:image/jpeg;base64,")


def test_inspection_defective_crack(inspection_data):
    engine = VisionInspectionEngine()
    crack_samples = [s for s in inspection_data["manifest"] if s["defect_type"] == "Surface Crack"]
    assert len(crack_samples) > 0

    first_crack = crack_samples[0]
    result = engine.analyze_file(first_crack["filepath"])

    assert result.prediction == InspectionPrediction.SUSPECTED_DEFECT
    assert result.anomaly_score >= 0.40
    assert result.defect_count >= 1
    assert result.max_defect_area_px > 10.0


def test_inspection_evaluation_metrics(inspection_data):
    engine = VisionInspectionEngine()
    metrics = engine.evaluate_test_set(inspection_data["manifest"])

    assert metrics.total_evaluated > 0
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1_score <= 1.0
    assert metrics.true_positives + metrics.true_negatives + metrics.false_positives + metrics.false_negatives == metrics.total_evaluated
    assert metrics.mean_inference_time_ms > 0.0


def test_corrupted_image_handling():
    engine = VisionInspectionEngine()
    corrupt_bytes = b"Not a valid jpeg or png image header"
    with pytest.raises(ValueError, match="Failed to decode image"):
        engine.analyze_image_bytes(corrupt_bytes)
