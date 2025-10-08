import React from 'react';
import PanelAIDiagnosis from './panels/PanelAIDiagnosis';

function getPanelModule({ servicesManager, commandsManager }) {
    const WrappedPanelAIDiagnosis = () => {
        // Truyền servicesManager xuống làm prop
        return <PanelAIDiagnosis servicesManager={servicesManager} />;
    };

    return [
        {
            name: 'aiDiagnosis',
            iconName: 'tab-studies',
            iconLabel: 'AI',
            label: 'AI Diagnosis',
            component: WrappedPanelAIDiagnosis,
        },
    ];
}

export default getPanelModule;