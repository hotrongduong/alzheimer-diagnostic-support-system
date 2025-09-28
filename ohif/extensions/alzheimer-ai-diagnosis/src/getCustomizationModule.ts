export default function getCustomizationModule({ servicesManager }: any) {
    return [
        {
            // SỬA "id" THÀNH "name"
            name: 'alzheimerHangingProtocol',
            customizationType: 'hangingProtocol',
            hangingProtocolId: '@ohif/extension-default.hangingProtocolModule.default',
            content: {
                protocolMatchingRules: [
                    {
                        id: 'Modality OT',
                        weight: 100,
                        attribute: 'Modalities',
                        constraint: {
                            contains: ['OT'],
                        },
                    },
                ],
            },
        },
    ];
}