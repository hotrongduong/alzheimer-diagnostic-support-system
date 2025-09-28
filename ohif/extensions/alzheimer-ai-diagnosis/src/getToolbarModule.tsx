import React from 'react';
import BrainIcon from './components/BrainIcon';

export default function getToolbarModule({ servicesManager }: any) {
    const { iconService } = servicesManager.services;
    if (iconService && !iconService.getIcon('brain-icon')) {
        iconService.add('brain-icon', <BrainIcon />);
    }

    return [
        {
            id: 'alzheimer-prediction-toolbar',
            definitions: [
                {
                    id: 'runAlzheimerPredictionAction',
                    label: 'AI Prediction',
                    icon: 'brain-icon',
                    tooltip: 'Run Alzheimer Prediction',
                    type: 'action',
                    commandName: 'runAlzheimerPrediction',
                },
            ],
            defaultContext: 'ACTIVE_VIEWPORT::CORNERSTONE',
        },
    ];
}