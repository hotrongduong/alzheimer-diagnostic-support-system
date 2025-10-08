import React, { useState, useEffect, useRef } from 'react';
import { getEnabledElement, eventTarget } from '@cornerstonejs/core';

// --- Components ---
const Button: React.FC<{ children: React.ReactNode; onClick?: () => void; className?: string; disabled?: boolean; }> = ({ children, onClick, className = '', disabled = false }) => (
    <button
        onClick={onClick}
        disabled={disabled}
        className={`flex items-center justify-center w-full px-4 py-2 font-bold text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black ${className} ${disabled ? 'bg-gray-500 cursor-not-allowed' : ''}`}
    >
        {children}
    </button>
);

const BrainIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 512 512">
        <path
            fill="currentColor"
            d="M184 0c30.9 0 56 25.1 56 56v400c0 30.9-25.1 56-56 56c-28.9 0-52.7-21.9-55.7-50.1c-5.2 1.4-10.7 2.1-16.3 2.1c-35.3 0-64-28.7-64-64c0-7.4 1.3-14.6 3.6-21.2C21.4 367.4 0 338.2 0 304c0-31.9 18.7-59.5 45.8-72.3C37.1 220.8 32 207 32 192c0-30.7 21.6-56.3 50.4-62.6C80.8 123.9 80 118 80 112c0-29.9 20.6-55.1 48.3-62.1c3-28 26.8-49.9 55.7-49.9zm144 0c28.9 0 52.6 21.9 55.7 49.9C411.5 56.9 432 82 432 112c0 6-.8 11.9-2.4 17.4c28.8 6.2 50.4 31.9 50.4 62.6c0 15-5.1 28.8-13.8 39.7c27.1 12.8 45.8 40.4 45.8 72.3c0 34.2-21.4 63.4-51.6 74.8c2.3 6.6 3.6 13.8 3.6 21.2c0 35.3-28.7 64-64 64c-5.6 0-11.1-.7-16.3-2.1c-3 28.2-26.8 50.1-55.7 50.1c-30.9 0-56-25.1-56-56V56c0-30.9 25.1-56 56-56z"
        />
    </svg>
);

const PanelAIDiagnosis: React.FC<{ servicesManager: any }> = ({ servicesManager }) => {
    const { displaySetService } = servicesManager.services;
    const [models, setModels] = useState<any[]>([]);
    const [selectedModelId, setSelectedModelId] = useState<string>('');
    const [prediction, setPrediction] = useState<any>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string>('');
    const [review, setReview] = useState<{ status: string; comments: string }>({ status: '', comments: '' });
    const [isHeatmapVisible, setHeatmapVisible] = useState<boolean>(false);
    const [heatmapOpacity, setHeatmapOpacity] = useState<number>(50); // slider %
    const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);
    const [currentReportId, setCurrentReportId] = useState<string | null>(null);
    const overlayRef = useRef<HTMLImageElement | null>(null);

    useEffect(() => {
        const fetchModels = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/ai/models/');
                if (!res.ok) throw new Error(`Server responded with ${res.status}`);
                const data = await res.json();
                setModels(data || []);
                if (data && data.length > 0) setSelectedModelId(data[0].model_id);
            } catch (e: any) {
                console.error('[AI] fetchModels error', e);
                setError(e.message || 'Could not load models');
            }
        };
        fetchModels();
    }, []);

    // update overlay transform whenever pan/zoom changes
    useEffect(() => {
        if (!isHeatmapVisible || !overlayRef.current) return;

        const canvas = document.querySelector('canvas.cornerstone-canvas') as HTMLCanvasElement;
        if (!canvas?.parentElement) return;
        const element = canvas.parentElement;
        const enabledElement = getEnabledElement(element);

        if (!enabledElement) return;

        const updateOverlay = () => {
            const { viewport, image } = enabledElement;
            const overlay = overlayRef.current;
            if (!overlay || !viewport) return;

            overlay.style.width = `${image.width}px`;
            overlay.style.height = `${image.height}px`;
            overlay.style.left = '0px';
            overlay.style.top = '0px';

            let transform = `scale(${viewport.scale}) translate(${viewport.translation.x}px, ${viewport.translation.y}px)`;
            if (viewport.hflip) transform += ' scaleX(-1)';
            if (viewport.vflip) transform += ' scaleY(-1)';

            overlay.style.transformOrigin = 'top left';
            overlay.style.transform = transform;
        };

        // update immediately and attach listeners
        updateOverlay();
        element.addEventListener('cornerstoneimagerendered', updateOverlay);

        return () => {
            element.removeEventListener('cornerstoneimagerendered', updateOverlay);
        };
    }, [isHeatmapVisible]);

    const runPrediction = async () => {
        if (!selectedModelId) {
            setError('Please select an AI model.');
            return;
        }
        setIsLoading(true);
        setPrediction(null);
        setError('');
        setCurrentReportId(null);
        setReview({ status: '', comments: '' });
        removeHeatmapOverlay();

        try {
            const activeDisplaySets = displaySetService.getActiveDisplaySets?.() || [];
            const displaySet = activeDisplaySets[0];
            if (!displaySet) throw new Error('No active display set found.');
            const { StudyInstanceUID } = displaySet;

            const canvas = document.querySelector('canvas.cornerstone-canvas') as HTMLCanvasElement | null;
            if (!canvas) throw new Error('Viewport canvas element not found.');

            const imageData = canvas.toDataURL('image/png');
            const body = { imageData, studyInstanceUID: StudyInstanceUID, modelId: selectedModelId };

            const res = await fetch('http://localhost:8000/api/ai/predict-frame/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                let errText = `Server responded with ${res.status}`;
                try {
                    const errJson = await res.json();
                    errText = errJson.details || errJson.error || errText;
                } catch (e) { /* ignore */ }
                throw new Error(errText);
            }

            const data = await res.json();
            setPrediction({
                result: data.prediction_result?.class_name,
                confidence: `${(data.prediction_result?.confidence * 100 || 0).toFixed(0)}%`,
                heatmapUrl: data.heatmap_url,
                imageW: data.image_width,
                imageH: data.image_height,
            });
            setCurrentReportId(data.report_id);
            setError('');
        } catch (e: any) {
            console.error('[AI] Prediction error', e);
            setError(e?.message || String(e));
        } finally {
            setIsLoading(false);
        }
    };

    const removeHeatmapOverlay = () => {
        if (overlayRef.current) {
            overlayRef.current.remove();
            overlayRef.current = null;
        }
        setHeatmapVisible(false);
    };

    const toggleHeatmap = () => {
        if (isHeatmapVisible) {
            removeHeatmapOverlay();
            return;
        }
        if (!prediction?.heatmapUrl) {
            setError('No heatmap available.');
            return;
        }

        const canvas = document.querySelector('canvas.cornerstone-canvas') as HTMLCanvasElement;
        if (!canvas || !canvas.parentElement) {
            setError('Canvas not found to attach heatmap overlay.');
            return;
        }

        removeHeatmapOverlay();
        const parent = canvas.parentElement;

        const overlay = document.createElement('img');
        overlay.className = 'ai-heatmap-overlay';
        overlay.src = prediction.heatmapUrl;
        overlay.style.position = 'absolute';
        overlay.style.opacity = String(heatmapOpacity / 100);
        overlay.style.pointerEvents = 'none';
        overlay.style.zIndex = '10';
        overlay.style.transformOrigin = 'top left';

        overlay.onload = () => setHeatmapVisible(true);
        overlay.onerror = () => setError('Failed to load heatmap image.');

        parent.appendChild(overlay);
        overlayRef.current = overlay;
    };

    const submitReview = async () => {
        if (!review.status) {
            setError('Please select a review status.');
            return;
        }
        if (!currentReportId) {
            setError('No report available to review.');
            return;
        }

        setIsSubmittingReview(true);
        setError('');

        try {
            const body = {
                report: currentReportId,
                reviewer_status: review.status,
                reviewer_comments: review.comments,
            };

            const res = await fetch('http://localhost:8000/api/ai/save-review/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                let errText = `Server responded with ${res.status}`;
                try {
                    const errJson = await res.json();
                    errText = errJson.detail || errJson.error || JSON.stringify(errJson);
                } catch (e) { /* ignore */ }
                throw new Error(errText);
            }

            const data = await res.json();
            console.log('[AI] Review saved successfully:', data);

            alert('Review submitted successfully!');
            setReview({ status: '', comments: '' });
        } catch (e: any) {
            console.error('[AI] Submit review error', e);
            setError(e?.message || String(e));
        } finally {
            setIsSubmittingReview(false);
        }
    };

    const labels = [
        { name: 'Non_Dementia', color: 'bg-green-500' },
        { name: 'Very_mild_Dementia', color: 'bg-yellow-500' },
        { name: 'Mild_Dementia', color: 'bg-orange-500' },
        { name: 'Moderate_Dementia', color: 'bg-red-500' },
    ];

    return (
        <div className="text-white bg-secondary-dark p-3 flex flex-col h-full overflow-y-auto relative">
            <h2 className="text-xl font-bold border-b border-gray-700 pb-2 mb-4 text-primary-light">Alzheimer Prediction</h2>

            {/* Model Selector */}
            <div className="mb-4">
                <label htmlFor="model-select" className="block text-sm font-medium text-gray-400 mb-1">Select AI Model</label>
                <select
                    id="model-select"
                    value={selectedModelId}
                    onChange={(e) => setSelectedModelId(e.target.value)}
                    className="w-full p-2 bg-black text-white border border-gray-600 rounded-md text-sm"
                >
                    {models.length === 0 && <option>{error ? 'Error loading' : 'Loading models...'}</option>}
                    {models.map((m) => (
                        <option key={m.model_id} value={m.model_id}>
                            {m.model_name} (v{m.model_version})
                        </option>
                    ))}
                </select>
            </div>

            {/* Classification */}
            <div className="p-3 bg-primary-dark rounded-lg mb-4">
                <h3 className="text-base font-semibold text-gray-400 mb-3">Classification</h3>
                <div className="space-y-2">
                    {labels.map((label) => (
                        <div key={label.name} className="flex items-center">
                            <span className={`h-4 w-4 rounded-full mr-3 ${label.color} ${prediction?.result === label.name ? 'opacity-100' : 'opacity-25'}`} />
                            <span className={`${prediction?.result === label.name ? 'text-white font-bold' : 'text-gray-400'}`}>
                                {label.name.replace('_', ' ')}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Confidence */}
            {prediction && !isLoading && (
                <div className="p-3 bg-primary-dark rounded-lg mb-4">
                    <h3 className="text-base font-semibold text-gray-400 mb-2">Confidence</h3>
                    <p className="text-2xl font-bold text-aqua-400">{prediction.confidence}</p>
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="p-3 bg-red-800 text-red-200 rounded-lg mb-4 text-sm">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Action Buttons */}
            <div className="mb-4">
                <Button onClick={runPrediction} disabled={isLoading || models.length === 0} className="bg-green-600 hover:bg-green-700">
                    <BrainIcon />
                    <span className="ml-2">{isLoading ? 'Predicting...' : 'Run Prediction'}</span>
                </Button>
            </div>

            {prediction && (
                <div className="mb-4">
                    <Button onClick={toggleHeatmap} className="bg-blue-600 hover:bg-blue-800">
                        {isHeatmapVisible ? 'Hide Heatmap' : 'Show Heatmap'}
                    </Button>
                    {isHeatmapVisible && (
                        <div className="mt-2">
                            <label className="block text-xs mb-1">Opacity: {heatmapOpacity}%</label>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={heatmapOpacity}
                                onChange={(e) => {
                                    setHeatmapOpacity(Number(e.target.value));
                                    if (overlayRef.current) {
                                        overlayRef.current.style.opacity = String(Number(e.target.value) / 100);
                                    }
                                }}
                                className="w-full"
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Doctor's Review */}
            {prediction && (
                <div className="mt-auto pt-4 border-t border-gray-700">
                    <h3 className="text-base font-semibold text-gray-400 mb-3">Doctor's Review</h3>
                    <div className="space-y-3">
                        <div className="flex justify-between">
                            {['CORRECT', 'INCORRECT', 'IRRELEVANT'].map((status) => (
                                <button
                                    key={status}
                                    onClick={() => setReview((prev) => ({ ...prev, status }))}
                                    className={`px-3 py-1 text-xs rounded-full border ${review.status === status
                                        ? 'bg-primary-light text-black border-primary-light'
                                        : 'border-gray-600 text-gray-300 hover:bg-gray-700'
                                        }`}
                                >
                                    {status.charAt(0) + status.slice(1).toLowerCase()}
                                </button>
                            ))}
                        </div>
                        <textarea
                            name="comments"
                            value={review.comments}
                            onChange={(e) => setReview((prev) => ({ ...prev, comments: e.target.value }))}
                            placeholder="Reviewer comments..."
                            className="w-full p-2 bg-black text-white border border-gray-600 rounded-md h-20 text-sm"
                        />
                        <Button
                            onClick={submitReview}
                            disabled={!review.status || isSubmittingReview}
                            className="bg-sky-700 hover:bg-sky-900"
                        >
                            {isSubmittingReview ? 'Submitting...' : 'Submit Review'}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PanelAIDiagnosis;