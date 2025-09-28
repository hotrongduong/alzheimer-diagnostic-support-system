window.config = {
  routerBasename: '/',
  showStudyList: true,
  studyListFunctionsEnabled: true,
  extensions: [], // Để trống để OHIF dùng các extension mặc định
  modes: ['@ohif/mode-longitudinal'], // Kích hoạt mode xem ảnh mặc định

  dataSources: [
    {
      friendlyName: 'Orthanc via Nginx Proxy',
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        name: 'Orthanc',
        // Đường dẫn DICOMweb trỏ tới Nginx proxy
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