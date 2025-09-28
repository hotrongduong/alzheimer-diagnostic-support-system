import servicesManager from '@ohif/core';

const MOCK_DATA = {
    prediction: {
        class_name: 'Mild_Dementia',
        confidence: 0.89,
    },
    heatmap: '',
};

const actions = {
    runAlzheimerPrediction: ({ viewports }: any) => {
        const { panelService } = servicesManager.services;
        const { activeViewportId } = viewports;

        panelService.open('prediction-panel', {
            ...MOCK_DATA,
            activeViewportId
        });
    },
};

const definitions = {
    runAlzheimerPrediction: {
        commandFn: actions.runAlzheimerPrediction,
        storeContexts: ['viewports'],
        options: {},
    },
};

export default function getCommandsModule({ servicesManager, extensionManager }: any) {
    return {
        actions,
        definitions,
        defaultContext: 'ACTIVE_VIEWPORT::CORNERSTONE',
    };
}