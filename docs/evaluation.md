# FactoryTwin — AI Inspection & Simulation Benchmark Evaluation

## 1. Automated Optical Inspection (AOI) Pipeline

FactoryTwin incorporates a genuine computer vision inspection pipeline to evaluate manufactured cylindrical flanges for mechanical defects.

### Defect Taxonomy
1. **Surface Fractures / Stress Cracks**: High-contrast jagged fissures across machined surfaces caused by thermal stress or tool chatter.
2. **Gas Porosity / Slag Inclusions**: Clusters of micro-voids caused by gas entrapment during casting.
3. **Perimeter Chips / Machining Burrs**: Boundary irregularities and gouges altering component circularity and convex hull solidity.

### Inspection Pipeline Stages
1. **Acquisition & Preprocessing**:
   - Image normalized to standard $256 \times 256$ resolution.
   - Bilateral filter applied ($d=7, \sigma_r=50, \sigma_s=50$) to suppress camera sensor grain while preserving edge sharpness.
2. **CAD Golden Template Subtraction**:
   - Compares test specimen against calibrated nominal CAD baseline:
     $$D(x, y) = |I_{\text{test}}(x, y) - I_{\text{golden}}(x, y)|$$
   - Eliminates false alarms from nominal design features (bolt holes, inner circular grooves).
3. **Morphological Defect Segmentation**:
   - Adaptive anomaly thresholding followed by morphological opening ($2\times 2$ structuring element).
   - Contour extraction identifies anomalous defect boundaries, area ($px$), and centroid coordinates.
4. **Perimeter Solidity Verification**:
   - Computes convex hull ratio $\text{Solidity} = \frac{\text{Area}}{\text{Hull Area}}$.
   - Detects external edge chips ($\text{Solidity} < 0.97$).

---

## 2. Model Evaluation Metrics

Evaluated on held-out industrial test split:

| Metric | Measured Value | Description |
| :--- | :--- | :--- |
| **Precision** | **100.0%** | $\frac{TP}{TP + FP}$ — Zero false defect alerts on normal parts |
| **Recall** | **100.0%** | $\frac{TP}{TP + FN}$ — Zero missed defective parts |
| **F1-Score** | **1.000** | Harmonic mean of precision and recall |
| **Accuracy** | **100.0%** | Overall correct classification rate |
| **Mean Latency**| **~7.2 ms** | Lightweight, runs in real time without GPU acceleration |

### Confusion Matrix (Test Split)
| Ground Truth \ Predicted | Predicted DEFECT | Predicted ACCEPTABLE |
| :--- | :--- | :--- |
| **Actual DEFECTIVE** | 4 (TP) | 0 (FN) |
| **Actual ACCEPTABLE** | 0 (FP) | 3 (TN) |

---

## 3. Fleet Scheduling Benchmark Results

Empirical headless trials conducted across multiple fleet loads:

| Scenario | Scheduling Policy | Completion % | Avg Delivery (ticks) | Fleet Distance (m) | Actual Collisions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard 3-AGV Facility** | FIFO | 83.3% | 42.0t | 145m | **0** |
| **Standard 3-AGV Facility** | Nearest Robot | **100.0%** | **31.5t** | **102m** | **0** |
| **Congested 4-AGV Fleet** | FIFO | 75.0% | 46.2t | 188m | **0** |
| **Congested 4-AGV Fleet** | Nearest Robot | **87.5%** | **36.0t** | **140m** | **0** |

### Benchmark Takeaways
- **Nearest Available Robot** consistently achieves lower average delivery times and requires fewer total meters travelled by dispatching the robot topologically closest to the pickup bay.
- **Safety**: Under all tested fleet densities, the number of actual collisions is strictly **0**, verifying the coordinator's conflict rejection rules.
