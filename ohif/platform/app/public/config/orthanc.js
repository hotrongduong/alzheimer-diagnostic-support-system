window.config = {
  routerBasename: '/',
  showStudyList: true,
  studyListFunctionsEnabled: true,

  // --- THÊM LẠI DÒNG BỊ THIẾU ---
  // Dòng này là bắt buộc, dù cho có để trống.
  extensions: [],
  // --- KẾT THÚC SỬA LỖI ---

  modes: ['@ohif/mode-longitudinal', '@ohif/mode-segmentation'],

  dataSources: [
    {
      friendlyName: 'Orthanc via Nginx Proxy',
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        name: 'Orthanc',
        qidoRoot: '/orthanc-proxy/dicom-web',
        wadoRoot: '/orthanc-proxy/dicom-web',
        qidoSupportsIncludeField: true,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: true,
        supportsWildcard: true,
        dicomUploadEnabled: true,
      },
    },
  ],
  defaultDataSourceName: 'dicomweb',
};