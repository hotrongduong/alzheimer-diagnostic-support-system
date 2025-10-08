import { id } from './id';
import toolbarButtons from './toolbarButtons';
import initToolGroups from './initToolGroups';

const ohif = {
  layout: '@ohif/extension-default.layoutTemplateModule.viewerLayout',
  sopClassHandler: '@ohif/extension-default.sopClassHandlerModule.stack',
  hangingProtocol: '@ohif/extension-default.hangingProtocolModule.default',
  leftPanel: '@ohif/extension-default.panelModule.seriesList',
};

const cornerstone = {
  viewport: '@ohif/extension-cornerstone.viewportModule.cornerstone',
  panelTool: '@ohif/extension-cornerstone.panelModule.panelSegmentationWithTools',
  measurements: '@ohif/extension-cornerstone.panelModule.panelMeasurement',
};

const segmentation = {
  sopClassHandler: '@ohif/extension-cornerstone-dicom-seg.sopClassHandlerModule.dicom-seg',
  viewport: '@ohif/extension-cornerstone-dicom-seg.viewportModule.dicom-seg',
};

const dicomRT = {
  viewport: '@ohif/extension-cornerstone-dicom-rt.viewportModule.dicom-rt',
  sopClassHandler: '@ohif/extension-cornerstone-dicom-rt.sopClassHandlerModule.dicom-rt',
};

// 1. Thêm tham chiếu đến panel AI
const alzheimerPrediction = {
  panel: '@ohif/extension-alzheimer-prediction.panelModule.aiDiagnosis',
};

const extensionDependencies = {
  '@ohif/extension-default': '^3.0.0',
  '@ohif/extension-cornerstone': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-seg': '^3.0.0',
  '@ohif/extension-cornerstone-dicom-rt': '^3.0.0',
  // 2. Thêm extension AI làm phụ thuộc
  '@ohif/extension-alzheimer-prediction': '1.0.0',
};

function modeFactory({ modeConfiguration }) {
  return {
    id,
    routeName: 'segmentation',
    displayName: 'Segmentation',
    onModeEnter: ({ servicesManager, extensionManager, commandsManager }: withAppTypes) => {
      const {
        measurementService,
        toolbarService,
        toolGroupService,
        panelService, // 3. Thêm PanelService
      } = servicesManager.services;

      measurementService.clearMeasurements();
      initToolGroups(extensionManager, toolGroupService, commandsManager);
      toolbarService.register(toolbarButtons);
      // Giữ nguyên toàn bộ phần cấu hình toolbar gốc
      toolbarService.updateSection(toolbarService.sections.primary, ['WindowLevel', 'Pan', 'Zoom', 'TrackballRotate', 'Capture', 'Layout', 'Crosshairs', 'MoreTools']);
      toolbarService.updateSection(toolbarService.sections.viewportActionMenu.topLeft, ['orientationMenu', 'dataOverlayMenu']);
      toolbarService.updateSection(toolbarService.sections.viewportActionMenu.bottomMiddle, ['AdvancedRenderingControls']);
      toolbarService.updateSection('AdvancedRenderingControls', ['windowLevelMenuEmbedded', 'voiManualControlMenu', 'Colorbar', 'opacityMenu', 'thresholdMenu']);
      toolbarService.updateSection(toolbarService.sections.viewportActionMenu.topRight, ['modalityLoadBadge', 'trackingStatus', 'navigationComponent']);
      toolbarService.updateSection(toolbarService.sections.viewportActionMenu.bottomLeft, ['windowLevelMenu']);
      toolbarService.updateSection('MoreTools', ['Reset', 'rotate-right', 'flipHorizontal', 'ReferenceLines', 'ImageOverlayViewer', 'StackScroll', 'invert', 'Cine', 'Magnify', 'TagBrowser']);
      toolbarService.updateSection(toolbarService.sections.segmentationToolbox, ['SegmentationUtilities', 'SegmentationTools']);
      toolbarService.updateSection('SegmentationUtilities', ['LabelmapSlicePropagation', 'InterpolateLabelmap', 'SegmentBidirectional', 'SegmentLabelTool']);
      toolbarService.updateSection('SegmentationTools', ['BrushTools', 'MarkerLabelmap', 'RegionSegmentPlus', 'Shapes']);
      toolbarService.updateSection('BrushTools', ['Brush', 'Eraser', 'Threshold']);

      // 4. SỬA LẠI TÊN HÀM CHO ĐÚNG
      panelService.activatePanel('aiDiagnosis');
    },
    onModeExit: ({ servicesManager }: withAppTypes) => {
      const { toolGroupService, syncGroupService, segmentationService, cornerstoneViewportService, uiDialogService, uiModalService } = servicesManager.services;
      uiDialogService.hideAll();
      uiModalService.hide();
      toolGroupService.destroy();
      syncGroupService.destroy();
      segmentationService.destroy();
      cornerstoneViewportService.destroy();
    },
    isValidMode: ({ modalities }) => {
      const modalitiesArray = modalities.split('\\');
      return {
        valid: modalitiesArray.length === 1 ? !['SM', 'ECG', 'OT', 'DOC'].includes(modalitiesArray[0]) : true,
      };
    },
    routes: [
      {
        // 5. XÓA 'path' ĐỂ ROUTE NÀY ÁP DỤNG CHO URL GỐC CỦA MODE
        // path: 'template',
        layoutTemplate: ({ location, servicesManager }) => {
          return {
            id: ohif.layout,
            props: {
              leftPanels: [ohif.leftPanel],
              leftPanelResizable: true,
              // 6. Thêm panel AI vào sidebar
              rightPanels: [alzheimerPrediction.panel, cornerstone.panelTool],
              rightPanelResizable: true,
              viewports: [
                { namespace: cornerstone.viewport, displaySetsToDisplay: [ohif.sopClassHandler] },
                { namespace: segmentation.viewport, displaySetsToDisplay: [segmentation.sopClassHandler] },
                { namespace: dicomRT.viewport, displaySetsToDisplay: [dicomRT.sopClassHandler] },
              ],
            },
          };
        },
      },
    ],
    extensions: extensionDependencies,
    hangingProtocol: ['@ohif/mnGrid'],
    sopClassHandlers: [ohif.sopClassHandler, segmentation.sopClassHandler, dicomRT.sopClassHandler],
  };
}

const mode = {
  id,
  modeFactory,
  extensionDependencies,
};

export default mode;