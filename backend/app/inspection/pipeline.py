from __future__ import annotations
import base64
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from pydantic import BaseModel, Field


class InspectionPrediction(str):
    ACCEPTABLE = "ACCEPTABLE"
    SUSPECTED_DEFECT = "SUSPECTED DEFECT"
    INCONCLUSIVE = "INCONCLUSIVE"


class InspectionResult(BaseModel):
    prediction: str
    confidence: float
    anomaly_score: float
    inference_time_ms: float
    defect_type: Optional[str] = None
    defect_count: int = 0
    max_defect_area_px: float = 0.0
    annotated_image_b64: Optional[str] = None
    model_name: str = "FactoryTwin-AOI-VisionEngine-v1"
    timestamp: float = Field(default_factory=time.time)


class EvaluationMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    mean_inference_time_ms: float
    total_evaluated: int


class VisionInspectionEngine:
    """
    Industrial Automated Optical Inspection (AOI) vision engine.
    Uses calibrated Golden Template Differential Analysis and morphological contour defect
    segmentation to reliably detect surface fractures, porosities, and edge defects.
    """

    def __init__(self, anomaly_threshold: float = 0.35, golden_template: Optional[np.ndarray] = None):
        self.anomaly_threshold = anomaly_threshold
        self.model_name = "FactoryTwin-AOI-VisionEngine-v1"
        self.golden_template = golden_template
        if self.golden_template is None:
            self._generate_default_golden_template()

    def _generate_default_golden_template(self) -> None:
        """Generates the nominal CAD reference flange image (256x256 grayscale)."""
        from PIL import Image, ImageDraw
        size = 256
        img = Image.new("L", (size, size), color=35)
        draw = ImageDraw.Draw(img)
        # Outer rim
        draw.ellipse([28, 28, 228, 228], fill=165, outline=215, width=4)
        # Inner groove
        draw.ellipse([50, 50, 206, 206], fill=135, outline=105, width=3)
        # Central bore
        draw.ellipse([100, 100, 156, 156], fill=22, outline=75, width=3)
        # Bolt holes
        bolt_coords = [(60, 128), (196, 128), (128, 60), (128, 196)]
        for bx, by in bolt_coords:
            draw.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=22, outline=95, width=2)

        self.golden_template = np.array(img).astype(np.uint8)

    def analyze_image_bytes(self, image_bytes: bytes) -> InspectionResult:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Failed to decode image. Unsupported or corrupted file format.")
        return self.inspect_image(img_bgr)

    def analyze_file(self, file_path: str | Path) -> InspectionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File {path} not found")
        img_bgr = cv2.imread(str(path))
        if img_bgr is None:
            raise ValueError(f"Failed to load image from {path}")
        return self.inspect_image(img_bgr)

    def inspect_image(self, img_bgr: np.ndarray) -> InspectionResult:
        t0 = time.perf_counter()
        resized = cv2.resize(img_bgr, (256, 256))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        annotated = resized.copy()

        # 1. Differential analysis against Golden CAD Template
        diff = cv2.absdiff(gray, self.golden_template)
        diff_blur = cv2.GaussianBlur(diff, (5, 5), 0)

        # 2. Defect thresholding
        _, anomaly_mask = cv2.threshold(diff_blur, 16, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(anomaly_mask, cv2.MORPH_OPEN, kernel)

        # 3. Defect contour segmentation and measurement
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_defects = []
        max_defect_area = 0.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 18.0:
                valid_defects.append(cnt)
                if area > max_defect_area:
                    max_defect_area = area

                # Draw localization bounding box and contour
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(annotated, (x - 2, y - 2), (x + w + 2, y + h + 2), (0, 0, 255), 2)
                cv2.drawContours(annotated, [cnt], -1, (0, 230, 255), 1)
                cv2.putText(
                    annotated,
                    f"DEFECT {area:.0f}px",
                    (x, max(12, y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,
                    (0, 0, 255),
                    1,
                )

        defect_count = len(valid_defects)
        total_defect_area = sum(cv2.contourArea(c) for c in valid_defects)

        # 4. Calibrated anomaly score
        if defect_count == 0:
            anomaly_score = 0.08  # Baseline nominal sensor variance
            prediction = InspectionPrediction.ACCEPTABLE
            confidence = 0.95
            defect_type = "None (Pristine Component)"
        else:
            # Score scales with area and defect count
            area_weight = min(1.0, total_defect_area / 200.0)
            anomaly_score = float(np.clip(0.40 + (area_weight * 0.55), 0.0, 1.0))

            if anomaly_score >= self.anomaly_threshold:
                prediction = InspectionPrediction.SUSPECTED_DEFECT
                confidence = round(float(np.clip(0.80 + (anomaly_score - 0.35) * 0.25, 0.80, 0.99)), 3)
                if max_defect_area > 180.0:
                    defect_type = "Gas Porosity / Slag Inclusion"
                elif max_defect_area > 100.0:
                    defect_type = "Surface Fracture / Stress Crack"
                else:
                    defect_type = "Perimeter Chip / Burr"
            else:
                prediction = InspectionPrediction.INCONCLUSIVE
                confidence = 0.50
                defect_type = "Minor Tool Mark"

        inference_time_ms = float((time.perf_counter() - t0) * 1000.0)

        # Draw status banner on annotated image
        status_color = (0, 200, 0) if prediction == InspectionPrediction.ACCEPTABLE else (0, 0, 220)
        cv2.rectangle(annotated, (0, 0), (256, 22), (20, 20, 30), -1)
        cv2.putText(
            annotated,
            f"{prediction} | Conf: {confidence:.2f} | Score: {anomaly_score:.2f}",
            (6, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            status_color,
            1,
        )

        # Convert annotated image to base64 for API visualization
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        return InspectionResult(
            prediction=prediction,
            confidence=round(confidence, 3),
            anomaly_score=round(anomaly_score, 3),
            inference_time_ms=round(inference_time_ms, 2),
            defect_type=defect_type,
            defect_count=defect_count,
            max_defect_area_px=round(max_defect_area, 1),
            annotated_image_b64=annotated_b64,
            model_name=self.model_name,
        )

    def evaluate_test_set(self, manifest: List[dict]) -> EvaluationMetrics:
        test_samples = [s for s in manifest if s.get("split") == "test"]
        if not test_samples:
            test_samples = manifest

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        latencies = []

        for sample in test_samples:
            result = self.analyze_file(sample["filepath"])
            latencies.append(result.inference_time_ms)
            is_gt_defective = sample["ground_truth"] == "DEFECTIVE"
            is_pred_defective = result.prediction == InspectionPrediction.SUSPECTED_DEFECT

            if is_gt_defective and is_pred_defective:
                tp += 1
            elif not is_gt_defective and not is_pred_defective:
                tn += 1
            elif not is_gt_defective and is_pred_defective:
                fp += 1
            elif is_gt_defective and not is_pred_defective:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(test_samples) if test_samples else 1.0
        mean_latency = float(np.mean(latencies)) if latencies else 0.0

        return EvaluationMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            accuracy=round(accuracy, 4),
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            mean_inference_time_ms=round(mean_latency, 2),
            total_evaluated=len(test_samples),
        )
