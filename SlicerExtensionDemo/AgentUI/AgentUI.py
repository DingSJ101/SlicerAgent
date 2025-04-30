import logging
import os
import sys

import slicer
from qt import QTextCursor
from slicer import vtkMRMLScalarVolumeNode
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

module_dir = os.path.dirname(os.path.abspath(__file__))
extension_dir = os.path.dirname(module_dir)
project_dir = os.path.dirname(extension_dir)
sys.path.append(project_dir)

try:
    from app.slicer.process import SlicerAgentProcess
except ImportError as e:
    print(f"Error importing SlicerAgent: {e}")


#
# AgentUI
#


class AgentUI(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("AgentUI")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Agent")]
        self.parent.dependencies = []
        self.parent.contributors = ["Shijie Ding"]
        self.parent.helpText = _("""This is an demo extension for SlicerAgent.""")
        self.parent.acknowledgementText = _("")


#
# AgentUIWidget
#


class AgentUIWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self.agent_process = SlicerAgentProcess()

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/AgentUI.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = AgentUILogic()

        # Connections

        # Buttons
        # self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)
        self.ui.submitButton.clicked.connect(self.onSubmitClicked)
        self.ui.inputLine.returnPressed.connect(self.onSubmitClicked)
        self.ui.clearButton.clicked.connect(self.onNewChatButtonClicked)
        self.agent_process.streaming_output.connect(self.onStreamingOutput)
        self.agent_process.start_toolcall.connect(self.onStartToolcall)
        self.agent_process.finish_toolcall.connect(self.onFinishToolcall)
        self.agent_process.response_finish.connect(self.onResponseFinish)
        self.agent_process.start_agent()

        self.ui.chatDisplay.append(f"<b>User:</b>")

    def onStartToolcall(self, content: str):
        print("start toolcall:", content)
        if content == "create_chat_completion":
            content = "generating ..."
        self.ui.inputLine.setText(content)

    def onFinishToolcall(self, content):
        print("finish toolcall:", content)

    def onSubmitClicked(self):
        """处理用户输入"""
        user_input = self.ui.inputLine.text.strip()
        if not user_input:
            return

        self.ui.chatDisplay.append(f"{user_input}<br><b>Assistant:</b> ")
        self.ui.inputLine.clear()

        self.ui.inputLine.setEnabled(False)
        self.ui.submitButton.setEnabled(False)

        self.agent_process.send_messages(user_input)

    def onNewChatButtonClicked(self):
        self.agent_process.send_command("clear")
        self.ui.chatDisplay.clear()
        self.ui.chatDisplay.append(f"<b>User:</b>")

    def onResponseFinish(self):
        self.ui.inputLine.clear()
        self.ui.chatDisplay.append(f"<b>User:</b> ")
        self.ui.inputLine.setEnabled(True)
        self.ui.submitButton.setEnabled(True)

    def onStreamingOutput(self, s):
        """显示流式输出"""
        self.ui.chatDisplay.moveCursor(QTextCursor.End)
        self.ui.chatDisplay.insertPlainText(s)
        self.ui.chatDisplay.ensureCursorVisible()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        # Disconnect all observers
        self.agent_process.streaming_output.disconnect(self.onStreamingOutput)
        self.agent_process.close()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        ...

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        ...


#
# AgentUILogic
#


class AgentUILogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def process(
        self,
        inputVolume: vtkMRMLScalarVolumeNode,
        outputVolume: vtkMRMLScalarVolumeNode,
        imageThreshold: float,
        invert: bool = False,
        showResult: bool = True,
    ) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info("Processing started")

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            "InputVolume": inputVolume.GetID(),
            "OutputVolume": outputVolume.GetID(),
            "ThresholdValue": imageThreshold,
            "ThresholdType": "Above" if invert else "Below",
        }
        cliNode = slicer.cli.run(
            slicer.modules.thresholdscalarvolume,
            None,
            cliParams,
            wait_for_completion=True,
            update_display=showResult,
        )
        # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime - startTime:.2f} seconds")


#
# AgentUITest
#


class AgentUITest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_AgentUI1()

    def test_AgentUI1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("AgentUI1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = AgentUILogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
