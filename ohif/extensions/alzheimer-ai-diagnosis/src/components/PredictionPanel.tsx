import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Button } from '@ohif/ui';

export interface PredictionPanelProps {
    prediction: any;
    heatmap: string;
    activeViewportId: string;
}

const lightStyle = {
    height: '15px', width: '15px', borderRadius: '50%',
    display: 'inline-block', marginRight: '10px', backgroundColor: '#555',
    transition: 'all 0.3s ease', border: '1px solid #777',
};
const activeLightStyle = { ...lightStyle, boxShadow: '0 0 10px 2px' };
const lightColors = {
    "Non_Dementia": "#28a745", "Very_mild_Dementia": "#ffc107",
    "Mild_Dementia": "#fd7e14", "Moderate_Dementia": "#dc3545",
};

const PredictionPanel: React.FC<PredictionPanelProps> = ({ prediction, heatmap, activeViewportId }) => {
    const [showHeatmap, setShowHeatmap] = useState(false);

    if (!prediction) {
        return <div className="p-4 text-gray-400">Không có dữ liệu dự đoán.</div>;
    }

    const { class_name: predictedClass, confidence } = prediction;

    return (
        <div className="p-4 text-white bg-black h-full flex flex-col">
            <h4 className="pb-2 mb-4 border-b border-gray-600">Alzheimer Prediction</h4>
            <div className="flex-grow">
                <p><strong>Kết quả:</strong> {predictedClass.replace('_', ' ')}</p>
                <p><strong>Độ tin cậy:</strong> {(confidence * 100).toFixed(2)}%</p>
                <div className="pt-4 mt-4 border-t border-gray-600">
                    <div className="flex items-center justify-between">
                        <label htmlFor="heatmapToggle">Hiển thị Heatmap</label>
                        <input type="checkbox" id="heatmapToggle" checked={showHeatmap} onChange={() => setShowHeatmap(!showHeatmap)} />
                    </div>
                </div>
            </div>
        </div>
    );
};

PredictionPanel.propTypes = {
    prediction: PropTypes.object,
    heatmap: PropTypes.string,
    activeViewportId: PropTypes.string,
};

export default PredictionPanel;