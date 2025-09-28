import React from 'react';
import PredictionPanel from './components/PredictionPanel';

export default function getPanelModule({ servicesManager, extensionManager }: any) {
    return [
        {
            name: 'predictionPanel',
            id: 'prediction-panel',
            side: 'right',
            iconName: 'brain-icon',
            iconLabel: 'AI Prediction',
            component: PredictionPanel,
        },
    ];
}