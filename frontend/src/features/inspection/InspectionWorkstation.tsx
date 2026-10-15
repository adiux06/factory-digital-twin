import React, { useState, useEffect } from 'react';
import type { InspectionResult, EvaluationMetrics, SamplePart } from '../../types';
import { api } from '../../services/api';
import { Microscope, Upload, CheckCircle2, AlertOctagon, HelpCircle, Cpu, RefreshCw } from 'lucide-react';

export const InspectionWorkstation: React.FC = () => {
  const [samples, setSamples] = useState<SamplePart[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>('DEF-CRACK-01');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [inspectionResult, setInspectionResult] = useState<InspectionResult | null>(null);
  const [evaluationMetrics, setEvaluationMetrics] = useState<EvaluationMetrics | null>(null);
  const [recentHistory, setRecentHistory] = useState<any[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'station' | 'evaluation' | 'history'>('station');

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [sampleData, metricsData, historyData] = await Promise.all([
        api.getInspectionSamples(),
        api.getInspectionMetrics(),
        api.getInspectionResults(10),
      ]);
      setSamples(sampleData);
      setEvaluationMetrics(metricsData);
      setRecentHistory(historyData.items || []);

      if (sampleData.length > 0) {
        const initialSample = sampleData.find((s: any) => s.id === 'DEF-CRACK-01') || sampleData[0];
        setSelectedSampleId(initialSample.id);
        const res = await api.analyzeInspection(initialSample.id);
        setInspectionResult(res);
      }
    } catch (err) {
      console.error('Failed to load initial inspection data', err);
    }
  };

  const handleSelectSample = async (sampleId: string) => {
    setSelectedSampleId(sampleId);
    setUploadedFile(null);
    setPreviewUrl(null);
    runAnalysis(sampleId, undefined);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadedFile(file);
      setSelectedSampleId('');
      setPreviewUrl(URL.createObjectURL(file));
      runAnalysis(undefined, file);
    }
  };

  const runAnalysis = async (sampleId?: string, file?: File) => {
    setIsAnalyzing(true);
    try {
      const targetSample = sampleId || (uploadedFile ? undefined : selectedSampleId);
      const targetFile = file || uploadedFile || undefined;
      const result = await api.analyzeInspection(targetSample, targetFile);
      setInspectionResult(result);

      const [historyData, metricsData] = await Promise.all([
        api.getInspectionResults(10),
        api.getInspectionMetrics(),
      ]);
      setRecentHistory(historyData.items || []);
      setEvaluationMetrics(metricsData);
    } catch (err) {
      console.error('Inspection analysis failed', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getPredictionBadge = (prediction: string) => {
    switch (prediction) {
      case 'ACCEPTABLE':
        return (
          <div className="flex items-center space-x-2 bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 px-3 py-1.5 rounded-lg">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="font-bold tracking-wide">ACCEPTABLE (PASS)</span>
          </div>
        );
      case 'SUSPECTED DEFECT':
        return (
          <div className="flex items-center space-x-2 bg-rose-500/20 border border-rose-500/50 text-rose-300 px-3 py-1.5 rounded-lg animate-pulse">
            <AlertOctagon className="w-5 h-5 text-rose-400" />
            <span className="font-bold tracking-wide">SUSPECTED DEFECT (FAIL)</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-2 bg-amber-500/20 border border-amber-500/50 text-amber-300 px-3 py-1.5 rounded-lg">
            <HelpCircle className="w-5 h-5 text-amber-400" />
            <span className="font-bold tracking-wide">INCONCLUSIVE</span>
          </div>
        );
    }
  };

  return (
    <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-5 shadow-2xl">
      {/* Header & Sub-Navigation */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-purple-500/20 border border-purple-500/40 rounded-lg text-purple-400">
            <Microscope className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">
              AI Visual Inspection Workstation
            </h2>
            <p className="text-xs text-slate-400">
              Automated Optical Inspection (AOI) differential contour defect segmentation
            </p>
          </div>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-lg text-xs space-x-1">
          <button
            onClick={() => setActiveTab('station')}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              activeTab === 'station'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Live Inspection
          </button>
          <button
            onClick={() => setActiveTab('evaluation')}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              activeTab === 'evaluation'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Model Evaluation
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Inspection History
          </button>
        </div>
      </div>

      {activeTab === 'station' && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-3.5">
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Select Calibrated Test Specimen
              </label>
              <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                {samples.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSample(s.id)}
                    className={`p-2 rounded border cursor-pointer transition-all flex items-center justify-between text-xs ${
                      selectedSampleId === s.id && !uploadedFile
                        ? 'bg-purple-950/40 border-purple-500 text-purple-200 font-medium'
                        : 'bg-slate-850/50 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <span className="font-mono font-bold text-slate-200 block text-[11px]">{s.id}</span>
                      <span className="text-[10px] text-slate-400">{s.defect_type}</span>
                    </div>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                        s.ground_truth === 'ACCEPTABLE'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {s.ground_truth}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-3.5">
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Upload Custom Component Image
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-700 hover:border-purple-500/80 rounded-lg p-4 cursor-pointer transition-colors bg-slate-850/30">
                <Upload className="w-5 h-5 text-slate-400 mb-1" />
                <span className="text-[11px] text-slate-300">Click to upload JPEG or PNG</span>
                <span className="text-[10px] text-slate-500">(Max size 5 MB)</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
              {uploadedFile && (
                <div className="mt-2 text-[11px] text-purple-300 font-mono truncate">
                  Loaded: {uploadedFile.name}
                </div>
              )}
            </div>

            <button
              onClick={() => runAnalysis()}
              disabled={isAnalyzing}
              className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-800 text-white font-semibold text-xs rounded-lg shadow-lg shadow-purple-600/20 flex items-center justify-center space-x-2 transition-all"
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Executing Computer Vision Model...</span>
                </>
              ) : (
                <>
                  <Cpu className="w-4 h-4" />
                  <span>Execute Optical Inspection</span>
                </>
              )}
            </button>
          </div>

          <div className="lg:col-span-8 space-y-4">
            {inspectionResult ? (
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
                  {getPredictionBadge(inspectionResult.prediction)}
                  <div className="flex items-center space-x-4 text-xs font-mono text-slate-400">
                    <div>
                      <span className="text-slate-500">Latency: </span>
                      <span className="text-cyan-400 font-bold">{inspectionResult.inference_time_ms} ms</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Model: </span>
                      <span className="text-slate-300">{inspectionResult.model_name}</span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-850/60 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Anomaly Defect Score</span>
                      <span className="font-mono font-bold text-slate-100">
                        {inspectionResult.anomaly_score.toFixed(3)}
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          inspectionResult.anomaly_score > 0.35 ? 'bg-rose-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, inspectionResult.anomaly_score * 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                      <span>0.0 (Nominal)</span>
                      <span>Threshold: 0.35</span>
                      <span>1.0 (Critical)</span>
                    </div>
                  </div>

                  <div className="bg-slate-850/60 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Model Decision Confidence</span>
                      <span className="font-mono font-bold text-cyan-400">
                        {(inspectionResult.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-cyan-500 h-full transition-all duration-500"
                        style={{ width: `${inspectionResult.confidence * 100}%` }}
                      ></div>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Classification: {inspectionResult.defect_type || 'None'}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div className="text-center">
                    <span className="block text-xs font-mono text-slate-400 mb-1.5">
                      1. Inspected Flange Component
                    </span>
                    <div className="border border-slate-800 rounded-lg overflow-hidden bg-black/40 flex items-center justify-center p-2">
                      <img
                        src={
                          previewUrl ||
                          `/static/samples/${
                            samples.find((s) => s.id === selectedSampleId)?.filename || 'sample_normal_01.png'
                          }`
                        }
                        alt="Raw component"
                        className="w-56 h-56 object-contain rounded shadow"
                      />
                    </div>
                  </div>

                  <div className="text-center">
                    <span className="block text-xs font-mono text-purple-400 mb-1.5">
                      2. AOI Defect Segmentation Overlay
                    </span>
                    <div className="border border-purple-900/60 rounded-lg overflow-hidden bg-black/40 flex items-center justify-center p-2">
                      {inspectionResult.annotated_image_b64 ? (
                        <img
                          src={inspectionResult.annotated_image_b64}
                          alt="Annotated defect heatmap"
                          className="w-56 h-56 object-contain rounded shadow"
                        />
                      ) : (
                        <div className="w-56 h-56 flex items-center justify-center text-slate-500 text-xs">
                          No annotation produced
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs bg-slate-850/40 p-2.5 rounded border border-slate-800/60">
                  <div>
                    <span className="block text-[10px] text-slate-500">Defect Contours</span>
                    <span className="font-mono font-bold text-slate-200">
                      {inspectionResult.defect_count} detected
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">Max Defect Area</span>
                    <span className="font-mono font-bold text-slate-200">
                      {inspectionResult.max_defect_area_px} px
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">Inspection Station</span>
                    <span className="font-mono font-bold text-purple-400">QC_INSPECTION_1</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center text-slate-500 text-xs bg-slate-900/40 rounded-lg border border-slate-800">
                Select a specimen or upload an image and click "Execute Optical Inspection".
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'evaluation' && evaluationMetrics && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
              <span className="text-[11px] text-slate-400 block">Precision</span>
              <span className="text-xl font-bold font-mono text-cyan-400">
                {(evaluationMetrics.precision * 100).toFixed(1)}%
              </span>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
              <span className="text-[11px] text-slate-400 block">Recall</span>
              <span className="text-xl font-bold font-mono text-emerald-400">
                {(evaluationMetrics.recall * 100).toFixed(1)}%
              </span>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
              <span className="text-[11px] text-slate-400 block">F1-Score</span>
              <span className="text-xl font-bold font-mono text-purple-400">
                {(evaluationMetrics.f1_score * 100).toFixed(1)}%
              </span>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
              <span className="text-[11px] text-slate-400 block">Mean Latency</span>
              <span className="text-xl font-bold font-mono text-amber-400">
                {evaluationMetrics.mean_inference_time_ms} ms
              </span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-slate-300 mb-3">
              Ground-Truth Confusion Matrix (Held-out Test Split)
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-center border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="p-2 text-left">Ground Truth \ Predicted</th>
                    <th className="p-2 text-rose-400 font-semibold">Predicted DEFECT</th>
                    <th className="p-2 text-emerald-400 font-semibold">Predicted ACCEPTABLE</th>
                  </tr>
                </thead>
                <tbody className="font-mono divide-y divide-slate-800/60">
                  <tr>
                    <td className="p-2 text-left text-slate-300 font-sans font-medium">Actual DEFECTIVE</td>
                    <td className="p-2 bg-purple-950/30 text-purple-300 font-bold">
                      {evaluationMetrics.true_positives} (True Positive)
                    </td>
                    <td className="p-2 text-slate-400">
                      {evaluationMetrics.false_negatives} (False Negative)
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 text-left text-slate-300 font-sans font-medium">Actual ACCEPTABLE</td>
                    <td className="p-2 text-slate-400">
                      {evaluationMetrics.false_positives} (False Positive)
                    </td>
                    <td className="p-2 bg-emerald-950/30 text-emerald-300 font-bold">
                      {evaluationMetrics.true_negatives} (True Negative)
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="mt-3 text-[11px] text-slate-500">
              Evaluated across {evaluationMetrics.total_evaluated} rigorously split test samples. Accuracy: {(evaluationMetrics.accuracy * 100).toFixed(1)}%.
            </div>
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs text-left divide-y divide-slate-800">
            <thead className="bg-slate-900/60 text-slate-400">
              <tr>
                <th className="p-2.5">Record ID</th>
                <th className="p-2.5">Sample / Specimen</th>
                <th className="p-2.5">Prediction</th>
                <th className="p-2.5">Confidence</th>
                <th className="p-2.5">Anomaly Score</th>
                <th className="p-2.5">Defect Classification</th>
                <th className="p-2.5">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {recentHistory.map((rec) => (
                <tr key={rec.id} className="hover:bg-slate-850/40">
                  <td className="p-2.5 text-slate-300">{rec.id}</td>
                  <td className="p-2.5 text-slate-400 font-sans">{rec.sample_id}</td>
                  <td className="p-2.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        rec.prediction === 'ACCEPTABLE'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {rec.prediction}
                    </span>
                  </td>
                  <td className="p-2.5 text-cyan-400">{(rec.confidence * 100).toFixed(0)}%</td>
                  <td className="p-2.5 text-slate-300">{rec.anomaly_score.toFixed(3)}</td>
                  <td className="p-2.5 text-slate-400 font-sans">{rec.defect_type || 'None'}</td>
                  <td className="p-2.5 text-slate-400">{rec.inference_time_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
