from System import *
from System.Collections.Specialized import *
from System.IO import *
from System.Text import *
from System.Text.RegularExpressions import *

from Deadline.Scripting import *
from System.IO import File
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
import re
import os
import time

# For Draft Integration
import imp
imp.load_source( 'DraftIntegration', os.path.join( RepositoryUtils.GetRootDirectory(), "submission", "Draft", "Main", "DraftIntegration.py" ) )
from DraftIntegration import *

########################################################################
## Globals
########################################################################
scriptDialog = None
settings = None
shotgunSettings = {}
fTrackSettings = {}
IntegrationOptions = ["Shotgun","FTrack"]

########################################################################
## Main Function Called By Deadline
########################################################################
def __main__():
    global scriptDialog
    global settings
    
    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle( "Submit Houdini Job To Deadline" )
    scriptDialog.SetIcon( Path.Combine( RepositoryUtils.GetRootDirectory(), "plugins/Houdini/Houdini.ico" ) )
    
    scriptDialog.AddTabControl("Tabs", 0, 0)
    
    scriptDialog.AddTabPage("Job Options")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator1", "SeparatorControl", "Job Description", 0, 0, colSpan=2 )
    
    scriptDialog.AddControlToGrid( "NameLabel", "LabelControl", "Job Name", 1, 0, "The name of your job. This is optional, and if left blank, it will default to 'Untitled'.", False )
    scriptDialog.AddControlToGrid( "NameBox", "TextControl", "Untitled", 1, 1 )

    scriptDialog.AddControlToGrid( "CommentLabel", "LabelControl", "Comment", 2, 0, "A simple description of your job. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "CommentBox", "TextControl", "", 2, 1 )

    scriptDialog.AddControlToGrid( "DepartmentLabel", "LabelControl", "Department", 3, 0, "The department you belong to. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "DepartmentBox", "TextControl", "", 3, 1 )
    scriptDialog.EndGrid()

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator2", "SeparatorControl", "Job Options", 0, 0, colSpan=3 )

    scriptDialog.AddControlToGrid( "PoolLabel", "LabelControl", "Pool", 1, 0, "The pool that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "PoolBox", "PoolComboControl", "none", 1, 1 )

    scriptDialog.AddControlToGrid( "SecondaryPoolLabel", "LabelControl", "Secondary Pool", 2, 0, "The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Slaves.", False )
    scriptDialog.AddControlToGrid( "SecondaryPoolBox", "SecondaryPoolComboControl", "", 2, 1 )

    scriptDialog.AddControlToGrid( "GroupLabel", "LabelControl", "Group", 3, 0, "The group that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "GroupBox", "GroupComboControl", "none", 3, 1 )

    scriptDialog.AddControlToGrid( "PriorityLabel", "LabelControl", "Priority", 4, 0, "A job can have a numeric priority ranging from 0 to 100, where 0 is the lowest priority and 100 is the highest priority.", False )
    scriptDialog.AddRangeControlToGrid( "PriorityBox", "RangeControl", RepositoryUtils.GetMaximumPriority() / 2, 0, RepositoryUtils.GetMaximumPriority(), 0, 1, 4, 1 )

    scriptDialog.AddControlToGrid( "TaskTimeoutLabel", "LabelControl", "Task Timeout", 5, 0, "The number of minutes a slave has to render a task for this job before it requeues it. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "TaskTimeoutBox", "RangeControl", 0, 0, 1000000, 0, 1, 5, 1 )
    scriptDialog.AddSelectionControlToGrid( "AutoTimeoutBox", "CheckBoxControl", False, "Enable Auto Task Timeout", 5, 2, "If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job. " )

    scriptDialog.AddControlToGrid( "ConcurrentTasksLabel", "LabelControl", "Concurrent Tasks", 6, 0, "The number of tasks that can render concurrently on a single slave. This is useful if the rendering application only uses one thread to render and your slaves have multiple CPUs.", False )
    scriptDialog.AddRangeControlToGrid( "ConcurrentTasksBox", "RangeControl", 1, 1, 16, 0, 1, 6, 1 )
    scriptDialog.AddSelectionControlToGrid( "LimitConcurrentTasksBox", "CheckBoxControl", True, "Limit Tasks To Slave's Task Limit", 6, 2, "If you limit the tasks to a slave's task limit, then by default, the slave won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual slaves by an administrator." )

    scriptDialog.AddControlToGrid( "MachineLimitLabel", "LabelControl", "Machine Limit", 7, 0, "", False )
    scriptDialog.AddRangeControlToGrid( "MachineLimitBox", "RangeControl", 0, 0, 1000000, 0, 1, 7, 1 )
    scriptDialog.AddSelectionControlToGrid( "IsBlacklistBox", "CheckBoxControl", False, "Machine List Is A Blacklist", 7, 2, "" )

    scriptDialog.AddControlToGrid( "MachineListLabel", "LabelControl", "Machine List", 8, 0, "Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.", False )
    scriptDialog.AddControlToGrid( "MachineListBox", "MachineListControl", "", 8, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "LimitGroupLabel", "LabelControl", "Limits", 9, 0, "The Limits that your job requires.", False )
    scriptDialog.AddControlToGrid( "LimitGroupBox", "LimitGroupControl", "", 9, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "DependencyLabel", "LabelControl", "Dependencies", 10, 0, "Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering. ", False )
    scriptDialog.AddControlToGrid( "DependencyBox", "DependencyControl", "", 10, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "OnJobCompleteLabel", "LabelControl", "On Job Complete", 11, 0, "If desired, you can automatically archive or delete the job when it completes. ", False )
    scriptDialog.AddControlToGrid( "OnJobCompleteBox", "OnJobCompleteControl", "Nothing", 11, 1 )
    scriptDialog.AddSelectionControlToGrid( "SubmitSuspendedBox", "CheckBoxControl", False, "Submit Job As Suspended", 11, 2, "If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render. " )
    scriptDialog.EndGrid()
    
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator3", "SeparatorControl", "Houdini Options", 0, 0, colSpan=4 )

    scriptDialog.AddControlToGrid( "SceneLabel", "LabelControl", "Houdini File", 1, 0, "The scene file to be rendered.", False )
    scriptDialog.AddSelectionControlToGrid( "SceneBox", "FileBrowserControl", "", "Houdini Files (*.hip *.hipnc)", 1, 1, colSpan=3 )

    outputBox = scriptDialog.AddSelectionControlToGrid("OutputLabel","CheckBoxControl",False,"Override Output", 2, 0, "Enable this option to override the output path in the scene file.", False)
    outputBox.ValueModified.connect(OutputChanged)
    scriptDialog.AddSelectionControlToGrid("OutputBox","FileSaverControl","", "Bitmap (*.bmp);;JPG (*.jpg);;PNG (*.png);;Targa (*.tga);;TIFF (*.tif);;All Files (*)", 2, 1, colSpan=3)

    scriptDialog.AddControlToGrid("RendererLabel","LabelControl","Render Node", 3, 0, "You must manually enter a renderer (output driver) to use. Note that the full node path must be specified, so if your output driver is 'mantra1', it's likely that the full node path would be '/out/mantra1'. ", False)
    scriptDialog.AddControlToGrid("RendererBox","TextControl","", 3, 1)

    scriptDialog.AddControlToGrid( "FramesLabel", "LabelControl", "Frame List", 4, 0, "The list of frames to render.", False )
    scriptDialog.AddControlToGrid( "FramesBox", "TextControl", "", 4, 1 )
    scriptDialog.AddControlToGrid( "ChunkSizeLabel", "LabelControl", "Frames Per Task", 4, 2, "This is the number of frames that will be rendered at a time for each job task. ", False )
    scriptDialog.AddRangeControlToGrid( "ChunkSizeBox", "RangeControl", 1, 1, 1000000, 0, 1, 4, 3 )

    scriptDialog.AddControlToGrid("VersionLabel","LabelControl","Version", 5, 0, "The version of Houdini to render with.", False)
    scriptDialog.AddComboControlToGrid("VersionBox","ComboControl","14",("9","10","11","12","13","14","15"), 5, 1)
    scriptDialog.AddControlToGrid("BuildLabel","LabelControl","Build to Force", 5, 2, "You can force 32 or 64 bit rendering with this option.", False)
    scriptDialog.AddComboControlToGrid("BuildBox","ComboControl","None",("None","32bit","64bit"), 5, 3)

    scriptDialog.AddSelectionControlToGrid("IgnoreInputsBox","CheckBoxControl",False,"Ignore Inputs", 6, 0, "If enabled, only the specified ROP will be rendered (does not render any of its dependencies).")
    scriptDialog.AddSelectionControlToGrid("SubmitSceneBox","CheckBoxControl",False,"Submit Houdini Scene",6, 2, "If this option is enabled, the scene file will be submitted with the job, and then copied locally to the slave machine during rendering.")
    
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()

    scriptDialog.AddTabPage("Mantra")
    scriptDialog.AddGrid()

    ifdBox = scriptDialog.AddSelectionControlToGrid("IFDLabel","CheckBoxControl",False,"Override Export IFD", 0, 0, "Enable this option to export IFD files from the Houdini scene file. Specify the path to the output IFD files here.", False)
    ifdBox.ValueModified.connect(IfdChanged)
    scriptDialog.AddSelectionControlToGrid("IFDBox","FileSaverControl","", "IFD (*.ifd);;All Files (*)",0, 1, colSpan=2)

    scriptDialog.AddControlToGrid( "Separator4", "SeparatorControl", "", 1, 0, colSpan=3 )

    mantraBox = scriptDialog.AddSelectionControlToGrid("MantraBox","CheckBoxControl",False,"Submit Dependent Mantra Standalone Job", 2, 0, "Enable this option to submit a dependent Mantra standalone job that will render the resulting IFD files.", colSpan=3)
    mantraBox.ValueModified.connect(MantraChanged)

    scriptDialog.AddControlToGrid( "MantraPoolLabel", "LabelControl", "Pool", 3, 0, "The pool that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "MantraPoolBox", "PoolComboControl", "none", 3, 1 )
    
    scriptDialog.AddControlToGrid( "MantraSecondaryPoolLabel", "LabelControl", "Secondary Pool", 4, 0, "The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Slaves.", False )
    scriptDialog.AddControlToGrid( "MantraSecondaryPoolBox", "SecondaryPoolComboControl", "", 4, 1 )

    scriptDialog.AddControlToGrid( "MantraGroupLabel", "LabelControl", "Group", 5, 0, "The group that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "MantraGroupBox", "GroupComboControl", "none", 5, 1 )

    scriptDialog.AddControlToGrid( "MantraPriorityLabel", "LabelControl", "Priority", 6, 0, "A job can have a numeric priority ranging from 0 to 100, where 0 is the lowest priority and 100 is the highest priority.", False )
    scriptDialog.AddRangeControlToGrid( "MantraPriorityBox", "RangeControl", RepositoryUtils.GetMaximumPriority() / 2, 0, RepositoryUtils.GetMaximumPriority(), 0, 1, 6, 1 )

    scriptDialog.AddControlToGrid( "MantraTaskTimeoutLabel", "LabelControl", "Task Timeout", 7, 0, "The number of minutes a slave has to render a task for this job before it requeues it. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "MantraTaskTimeoutBox", "RangeControl", 0, 0, 1000000, 0, 1, 7, 1 )
    scriptDialog.AddSelectionControlToGrid( "MantraAutoTimeoutBox", "CheckBoxControl", False, "Enable Auto Task Timeout", 7, 2, "If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job." )

    scriptDialog.AddControlToGrid( "MantraConcurrentTasksLabel", "LabelControl", "Concurrent Tasks", 8, 0, "The number of tasks that can render concurrently on a single slave. This is useful if the rendering application only uses one thread to render and your slaves have multiple CPUs.", False )
    scriptDialog.AddRangeControlToGrid( "MantraConcurrentTasksBox", "RangeControl", 1, 1, 16, 0, 1, 8, 1 )
    scriptDialog.AddSelectionControlToGrid( "MantraLimitConcurrentTasksBox", "CheckBoxControl", True, "Limit Tasks To Slave's Task Limit", 8, 2, "If you limit the tasks to a slave's task limit, then by default, the slave won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual slaves by an administrator." )

    scriptDialog.AddControlToGrid( "MantraMachineLimitLabel", "LabelControl", "Machine Limit", 9, 0, "Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "MantraMachineLimitBox", "RangeControl", 0, 0, 1000000, 0, 1, 9, 1 )
    scriptDialog.AddSelectionControlToGrid( "MantraIsBlacklistBox", "CheckBoxControl", False, "Machine List Is A Blacklist", 9, 2, "You can force the job to render on specific machines by using a whitelist, or you can avoid specific machines by using a blacklist." )

    scriptDialog.AddControlToGrid( "MantraMachineListLabel", "LabelControl", "Machine List", 10, 0, "The whitelisted or blacklisted list of machines.", False )
    scriptDialog.AddControlToGrid( "MantraMachineListBox", "MachineListControl", "", 10, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "MantraLimitGroupLabel", "LabelControl", "Limits", 11, 0, "The Limits that your job requires.", False )
    scriptDialog.AddControlToGrid( "MantraLimitGroupBox", "LimitGroupControl", "", 11, 1, colSpan=2 )

    scriptDialog.AddControlToGrid("ThreadsLabel","LabelControl","Mantra Threads", 12, 0, "The number of threads to use for the Mantra stanadlone job.", False)
    scriptDialog.AddRangeControlToGrid("ThreadsBox","RangeControl",0,0,256,0,1, 12, 1)
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    
    scriptDialog.AddTabPage("Region Rendering")
    scriptDialog.AddGrid()
    
    scriptDialog.AddControlToGrid( "Separator9", "SeparatorControl", "Tile Rendering", 0, 0, colSpan=4 )
    enableTilesBox = scriptDialog.AddSelectionControlToGrid("EnableTilesCheck","CheckBoxControl",False,"Enable Tile Rendering", 1, 0, "Enable to tile render the output.", False)
    enableTilesBox.ValueModified.connect(TilesChanged)
    
    scriptDialog.AddControlToGrid( "XTilesLabel", "LabelControl", "Tiles in X", 2, 0, "The number of tiles in the X direction.", False )
    scriptDialog.AddRangeControlToGrid( "XTilesBox", "RangeControl", 2, 1, 100, 0, 1, 2, 1 )
    scriptDialog.AddControlToGrid( "YTilesLabel", "LabelControl", "Tiles in Y", 2, 2, "The number of tiles in the Y direction.", False )
    scriptDialog.AddRangeControlToGrid( "YTilesBox", "RangeControl", 2, 1, 100, 0, 1, 2, 3 )
    
    singleFrameEnabledBox = scriptDialog.AddSelectionControlToGrid("SingleFrameEnabledCheck","CheckBoxControl",False,"Single Frame Tile Job Enabled", 3, 0, "Enable to submit all tiles in a single job.", False,1,2)
    singleFrameEnabledBox.ValueModified.connect(SingleFrameChanged)
    scriptDialog.AddControlToGrid( "SingleJobFrameLabel", "LabelControl", "Single Job Frame", 3, 2, "Which Frame to Render if Single Frame is enabled.", False )
    scriptDialog.AddRangeControlToGrid( "SingleJobFrameBox", "RangeControl", 1, 1, 100000, 0, 1, 3, 3 )
    
    SubmitDependentBox = scriptDialog.AddSelectionControlToGrid( "SubmitDependentCheck", "CheckBoxControl", True, "Submit Dependent Assembly Job", 4, 0, "If enabled, a dependent assembly job will be submitted.", False, 1, 2 )
    SubmitDependentBox.ValueModified.connect(SubmitDependentChanged)
    scriptDialog.AddSelectionControlToGrid( "CleanupTilesCheck", "CheckBoxControl", True, "Cleanup Tiles After Assembly", 4, 2, "If enabled, all tiles will be cleaned up by the assembly job.", False, 1, 2 )
    
    scriptDialog.AddSelectionControlToGrid( "ErrorOnMissingCheck", "CheckBoxControl", True, "Error on Missing Tile", 5, 0, "If enabled, the assembly job will fail if any tiles are missing.", False, 1, 2 )
    scriptDialog.AddSelectionControlToGrid( "ErrorOnMissingBackgroundCheck", "CheckBoxControl", False, "Error on Missing Background", 5, 2, "If enabled, the assembly will fail if the background is missing.", False, 1, 2 )
    
    scriptDialog.AddControlToGrid("AssembleOverLabel","LabelControl","Assemble Over", 6, 0, "What the tiles should be assembled over.", False)
    assembleBox = scriptDialog.AddComboControlToGrid("AssembleOverBox","ComboControl","Blank Image",("Blank Image","Previous Output","Selected Image"), 6, 1)
    assembleBox.ValueModified.connect(AssembleOverChanged)
    
    scriptDialog.AddControlToGrid("BackgroundLabel","LabelControl","Background Image File", 7, 0, "The Background image to assemble over.", False)
    scriptDialog.AddSelectionControlToGrid("BackgroundBox","FileSaverControl","", "Bitmap (*.bmp);;JPG (*.jpg);;PNG (*.png);;Targa (*.tga);;TIFF (*.tif);;All Files (*)", 7, 1, colSpan=3)
    
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    
    scriptDialog.AddTabPage("Integration")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator7", "SeparatorControl", "Project Management", 0, 0, colSpan=4 )
    
    scriptDialog.AddControlToGrid( "IntegrationLabel", "LabelControl", "Project Management", 1, 0, "", False )
    IntegrationTypeBox = scriptDialog.AddComboControlToGrid( "IntegrationTypeBox", "ComboControl", "Shotgun", IntegrationOptions, 1, 1, expand=False )
    IntegrationTypeBox.ValueModified.connect(IntegrationTypeBoxChanged)
    connectButton = scriptDialog.AddControlToGrid( "IntegrationConnectButton", "ButtonControl", "Connect...", 1, 2, expand=False )
    connectButton.ValueModified.connect(ConnectButtonPressed)
    createVersionBox = scriptDialog.AddSelectionControlToGrid( "CreateVersionBox", "CheckBoxControl", False, "Create new version", 1, 3, "If enabled, Deadline will connect to Shotgun/FTrack and create a new version for this job." )
    createVersionBox.ValueModified.connect(SubmitShotgunChanged)
    scriptDialog.SetEnabled( "CreateVersionBox", False )
    
    scriptDialog.AddControlToGrid( "IntegrationVersionLabel", "LabelControl", "Version", 2, 0, "The Shotgun/FTrack version name.", False )
    scriptDialog.AddControlToGrid( "IntegrationVersionBox", "TextControl", "", 2, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "IntegrationDescriptionLabel", "LabelControl", "Description", 3, 0, "The Shotgun/FTrack version description.", False )
    scriptDialog.AddControlToGrid( "IntegrationDescriptionBox", "TextControl", "", 3, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "IntegrationEntityInfoLabel", "LabelControl", "Selected Entity", 4, 0, "Information about the Shotgun/FTrack entity that the version will be created for.", False )
    entityInfoBox = scriptDialog.AddControlToGrid( "IntegrationEntityInfoBox", "MultiLineTextControl", "", 4, 1, colSpan=3 )
    entityInfoBox.ReadOnly = True
    
    scriptDialog.AddSelectionControlToGrid( "IntegrationUploadMovieBox", "CheckBoxControl", False, "Create/Upload Movie", 5, 1, "If this option is enabled, the tiles will be deleted after the assembly job is completed." )
    scriptDialog.AddSelectionControlToGrid( "IntegrationUploadFilmStripBox", "CheckBoxControl", False, "Create/Upload Film Strip", 5, 2, "If this option is enabled, the assembly job will fail if it cannot find any of the tiles." )
    scriptDialog.EndGrid()
    
    # Add Draft UI
    AddDraftUI( scriptDialog )
    
    SubmitShotgunChanged( None )
    SubmitDraftChanged( None )
    scriptDialog.EndTabPage()
    
    scriptDialog.EndTabControl()
    
    scriptDialog.AddGrid()
    scriptDialog.AddHorizontalSpacerToGrid( "HSpacer1", 0, 0 )
    submitButton = scriptDialog.AddControlToGrid( "SubmitButton", "ButtonControl", "Submit", 0, 1, expand=False )
    submitButton.ValueModified.connect(SubmitButtonPressed)
    closeButton = scriptDialog.AddControlToGrid( "CloseButton", "ButtonControl", "Close", 0, 2, expand=False )
    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    scriptDialog.EndGrid()
    
    settings = ("DepartmentBox","CategoryBox","PoolBox","SecondaryPoolBox","GroupBox","PriorityBox","MachineLimitBox","IsBlacklistBox","MachineListBox","LimitGroupBox","SceneBox","OutputBox", "IFDLabel", "IFDBox","FramesBox","ChunkSizeBox","RendererBox","IgnoreInputsBox","SubmitSceneBox","BuildBox","VersionBox", "MantraPoolBox", "MantraSecondaryPoolBox", "MantraGroupBox", "MantraPriorityBox", "MantraTaskTimeoutBox", "MantraAutoTimeoutBox","MantraConcurrentTasksBox", "MantraLimitConcurrentTasksBox", "MantraMachineLimitBox", "MantraIsBlacklistBox", "MantraMachineListBox", "MantraLimitGroupBox","ThreadsBox", "DraftTemplateBox", "DraftUserBox", "DraftEntityBox", "DraftVersionBox")	
    scriptDialog.LoadSettings( GetSettingsFilename(), settings )
    scriptDialog.EnabledStickySaving( settings, GetSettingsFilename() )
    
    OutputChanged()
    IfdChanged()
    
    LoadIntegrationSettings()
    updateDisplay()
    scriptDialog.SetValue("CreateVersionBox",False)
    
    scriptDialog.ShowDialog( False )
    
def GetSettingsFilename():
    return Path.Combine( GetDeadlineSettingsPath(), "HoudiniSettings.ini" )

def ConnectButtonPressed( *args ):
    global scriptDialog
    script = ""
    settingsName = ""
    usingShotgun = (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun")
    
    if usingShotgun:
        script = Path.Combine( RepositoryUtils.GetRootDirectory(), "events/Shotgun/ShotgunUI.py" )
        settingsName = GetShotgunSettingsFilename()
    else:
        script = Path.Combine( RepositoryUtils.GetRootDirectory(), "submission/FTrack/Main/FTrackUI.py" )
        settingsName = GetFTrackSettingsFilename()
        
    args = ["-ExecuteScript", script, "HoudiniMonitor"]
    args += AdditionalArgs()
        
    output = ClientUtils.ExecuteCommandAndGetOutput( args )
    updated = ProcessLines( output.splitlines(), usingShotgun )
    if updated:
        File.WriteAllLines( settingsName, tuple(output.splitlines()) )
        updateDisplay()
        
def AdditionalArgs():
    usingShotgun = (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun")
    additionalArgs = []
    
    if usingShotgun:
        if 'UserName' in shotgunSettings:
            userName = shotgunSettings['UserName']
            if userName != None and len(userName) > 0:
                additionalArgs.append("UserName="+str(userName))
                
        if 'VersionName' in shotgunSettings:
            versionName = shotgunSettings['VersionName']
            if versionName != None and len(versionName) > 0:
                additionalArgs.append("VersionName="+str(versionName))
                
        if 'TaskName' in shotgunSettings:
            taskName = shotgunSettings['TaskName']
            if taskName != None and len(taskName) > 0:
                additionalArgs.append("TaskName="+str(taskName))
                
        if 'ProjectName' in shotgunSettings:
            projectName = shotgunSettings['ProjectName']
            if projectName != None and len(projectName) > 0:
                additionalArgs.append("ProjectName="+str(projectName))
                
        if 'EntityName' in shotgunSettings:
            entityName = shotgunSettings['EntityName']
            if entityName != None and len(entityName) > 0:
                additionalArgs.append("EntityName="+str(entityName))
                
        if 'EntityType' in shotgunSettings:
            entityType = shotgunSettings['EntityType']
            if entityType != None and len(entityType) > 0:
                additionalArgs.append("EntityType="+str(entityType))
                
    else:
        if 'FT_Username' in fTrackSettings:
            userName = fTrackSettings['FT_Username']
            if userName != None and len(userName) > 0:
                additionalArgs.append("UserName="+str(userName))
                
        if 'FT_TaskName' in fTrackSettings:
            taskName = fTrackSettings['FT_TaskName']
            if taskName != None and len(taskName) > 0:
                additionalArgs.append("TaskName="+str(taskName))
                
        if 'FT_ProjectName' in fTrackSettings:
            projectName = fTrackSettings['FT_ProjectName']
            if projectName != None and len(projectName) > 0:
                additionalArgs.append("ProjectName="+str(projectName))
                
        if 'FT_AssetName' in fTrackSettings:
            assetName = fTrackSettings['FT_AssetName']
            if assetName != None and len(assetName) > 0:
                additionalArgs.append("AssetName="+str(assetName))
        
                
    return additionalArgs
    
def ProcessLines( lines, shotgun ):
    global shotgunSettings
    global fTrackSettings
    
    tempKVPs = {}
    
    for line in lines:
        line = line.strip()
        tokens = line.split( '=', 1 )
        
        if len( tokens ) > 1:
            key = tokens[0]
            value = tokens[1]
            tempKVPs[key] = value
    if len(tempKVPs)>0:
        if shotgun:
            shotgunSettings = tempKVPs
        else:
            fTrackSettings = tempKVPs
        return True
    return False
                           
def updateDisplay():
    global fTrackSettings
    global shotgunSettings
    
    displayText = ""
    if scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun":
        if 'UserName' in shotgunSettings:
            displayText += "User Name: %s\n" % shotgunSettings[ 'UserName' ]
        if 'TaskName' in shotgunSettings:
            displayText += "Task Name: %s\n" % shotgunSettings[ 'TaskName' ]
        if 'ProjectName' in shotgunSettings:
            displayText += "Project Name: %s\n" % shotgunSettings[ 'ProjectName' ]
        if 'EntityName' in shotgunSettings:
            displayText += "Entity Name: %s\n" % shotgunSettings[ 'EntityName' ]	
        if 'EntityType' in shotgunSettings:
            displayText += "Entity Type: %s\n" % shotgunSettings[ 'EntityType' ]
        if 'DraftTemplate' in shotgunSettings:
            displayText += "Draft Template: %s\n" % shotgunSettings[ 'DraftTemplate' ]
    
        scriptDialog.SetValue( "IntegrationEntityInfoBox", displayText )
        scriptDialog.SetValue( "IntegrationVersionBox", shotgunSettings.get( 'VersionName', "" ) )
        scriptDialog.SetValue( "IntegrationDescriptionBox", shotgunSettings.get( 'Description', "" ) )
    else:
        if 'FT_Username' in fTrackSettings:
            displayText += "User Name: %s\n" % fTrackSettings[ 'FT_Username' ]
        if 'FT_TaskName' in fTrackSettings:
            displayText += "Task Name: %s\n" % fTrackSettings[ 'FT_TaskName' ]
        if 'FT_ProjectName' in fTrackSettings:
            displayText += "Project Name: %s\n" % fTrackSettings[ 'FT_ProjectName' ]
    
        scriptDialog.SetValue( "IntegrationEntityInfoBox", displayText )
        scriptDialog.SetValue( "IntegrationVersionBox", fTrackSettings.get( 'FT_AssetName', "" ) )
        scriptDialog.SetValue( "IntegrationDescriptionBox", fTrackSettings.get( 'FT_Description', "" ) )
        
    if len(displayText)>0:
        scriptDialog.SetEnabled("CreateVersionBox",True)
        scriptDialog.SetValue("CreateVersionBox",True)
        SubmitDraftChanged(None)
    else:
        scriptDialog.SetEnabled("CreateVersionBox",False)
        scriptDialog.SetValue("CreateVersionBox",False)

def LoadIntegrationSettings():
    global fTrackSettings
    global shotgunSettings
    fTrackSettings = {}
    shotgunSettings = {}
        
    settingsFile = GetShotgunSettingsFilename()
    if File.Exists( settingsFile ):
        ProcessLines( File.ReadAllLines( settingsFile ), True )
        
    settingsFile = GetFTrackSettingsFilename()
    if File.Exists( settingsFile ):
        ProcessLines( File.ReadAllLines( settingsFile ), False )

def IntegrationTypeBoxChanged():
    updateDisplay()
    
    shotgunEnabled = (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun") and scriptDialog.GetValue( "CreateVersionBox" )
    scriptDialog.SetEnabled( "IntegrationUploadFilmStripBox", shotgunEnabled )
    
def GetShotgunSettingsFilename():
    return Path.Combine( GetDeadlineSettingsPath(), "HoudiniMonitorSettingsShotgun.ini" )

def GetFTrackSettingsFilename():
    return Path.Combine( GetDeadlineSettingsPath(), "HoudiniMonitorSettingsFTrack.ini" )

def SubmitShotgunChanged( *args ):
    global scriptDialog
    
    integrationEnabled = scriptDialog.GetValue( "CreateVersionBox" )
    draftEnabled = scriptDialog.GetValue( "DraftSubmitBox" )
    draftCustomEnabled = scriptDialog.GetValue( "DraftCustomRadio" )
    draftCreatesMovie = IsMovieFromFormat( scriptDialog.GetValue( "DraftFormatBox" ) )
    shotgunEnabled = (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun")
    
    scriptDialog.SetEnabled( "IntegrationVersionLabel", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationVersionBox", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationDescriptionLabel", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationDescriptionBox", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationEntityInfoLabel", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationEntityInfoBox", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationUploadMovieBox", integrationEnabled )
    scriptDialog.SetEnabled( "IntegrationUploadFilmStripBox", integrationEnabled and shotgunEnabled )
    
    scriptDialog.SetEnabled( "DraftUploadShotgunBox", integrationEnabled and shotgunEnabled and draftEnabled and ( draftCreatesMovie or draftCustomEnabled ) )
    scriptDialog.SetEnabled( "DraftShotgunButton", integrationEnabled and shotgunEnabled and draftEnabled and draftCustomEnabled )

def OutputChanged(*args):
    global scriptDialog
    
    overrideOutput = scriptDialog.GetValue( "OutputLabel" )
    scriptDialog.SetEnabled( "OutputBox", overrideOutput )
    scriptDialog.SetEnabled( "EnableTilesCheck", overrideOutput )
    
    TilesChanged()
    
def TilesChanged(*args):
    global scriptDialog
    enableRegionRendering = ( scriptDialog.GetValue( "EnableTilesCheck" ) and scriptDialog.GetEnabled( "EnableTilesCheck" ) )
    
    scriptDialog.SetEnabled( "XTilesLabel", enableRegionRendering )
    scriptDialog.SetEnabled( "XTilesBox", enableRegionRendering )
    scriptDialog.SetEnabled( "YTilesLabel", enableRegionRendering )
    scriptDialog.SetEnabled( "YTilesBox", enableRegionRendering )
    scriptDialog.SetEnabled( "SingleFrameEnabledCheck", enableRegionRendering )
    scriptDialog.SetEnabled( "SubmitDependentCheck", enableRegionRendering )
    
    SingleFrameChanged()
    SubmitDependentChanged()

def SubmitDependentChanged(*args):
    global scriptDialog
    submitDependentEnabled = ( scriptDialog.GetValue( "SubmitDependentCheck" ) and scriptDialog.GetEnabled( "SubmitDependentCheck" ) )
    
    scriptDialog.SetEnabled( "CleanupTilesCheck", submitDependentEnabled )
    scriptDialog.SetEnabled( "ErrorOnMissingCheck", submitDependentEnabled )
    scriptDialog.SetEnabled( "ErrorOnMissingBackgroundCheck", submitDependentEnabled )
    scriptDialog.SetEnabled( "AssembleOverLabel", submitDependentEnabled )
    scriptDialog.SetEnabled( "AssembleOverBox", submitDependentEnabled )
    
    AssembleOverChanged()
    
def AssembleOverChanged(*args):
    global scriptDialog
    AssembleOverEnabled = ( (scriptDialog.GetValue( "AssembleOverBox" ) == "Selected Image") and scriptDialog.GetEnabled( "AssembleOverBox" ) )
    
    scriptDialog.SetEnabled( "BackgroundLabel", AssembleOverEnabled )
    scriptDialog.SetEnabled( "BackgroundBox", AssembleOverEnabled )
    
    
def SingleFrameChanged(*args):
    global scriptDialog
    enableSingleFrameRegion = ( scriptDialog.GetValue( "SingleFrameEnabledCheck" ) and scriptDialog.GetEnabled( "SingleFrameEnabledCheck" ) )
    
    scriptDialog.SetEnabled( "SingleJobFrameLabel", enableSingleFrameRegion )
    scriptDialog.SetEnabled( "SingleJobFrameBox", enableSingleFrameRegion )
    
def IfdChanged(*args):
    global scriptDialog
    
    overrideIfd = scriptDialog.GetValue( "IFDLabel" )
    mantraJob = scriptDialog.GetValue( "MantraBox" )
    scriptDialog.SetEnabled( "IFDBox", overrideIfd )
    scriptDialog.SetEnabled( "MantraBox", overrideIfd )
    scriptDialog.SetEnabled( "ThreadsLabel", overrideIfd and mantraJob )
    scriptDialog.SetEnabled( "ThreadsBox", overrideIfd and mantraJob )

def MantraChanged(*args):
    global scriptDialog
    
    overrideIfd = scriptDialog.GetValue( "IFDLabel" )
    mantraJob = scriptDialog.GetValue( "MantraBox" )
    scriptDialog.SetEnabled( "ThreadsLabel", overrideIfd and mantraJob )
    scriptDialog.SetEnabled( "ThreadsBox", overrideIfd and mantraJob )

def RightReplace( fullString, oldString, newString, occurences ):
    return newString.join( fullString.rsplit( oldString, occurences ) )

    
def SubmitButtonPressed(*args):
    global scriptDialog
    global shotgunSettings
    
    paddedNumberRegex = Regex( "\\$F([0-9]+)" )
    
    # Check if houdini files exist.
    sceneFile = scriptDialog.GetValue( "SceneBox" )
    if( not File.Exists( sceneFile ) ):
        scriptDialog.ShowMessageBox( "Houdini file %s does not exist" % sceneFile, "Error" )
        return
    elif (PathUtils.IsPathLocal(sceneFile) and not scriptDialog.GetValue("SubmitSceneBox")):
        result = scriptDialog.ShowMessageBox("Houdini file " + sceneFile + " is local.  Are you sure you want to continue?", "Warning",("Yes","No"))
        if(result=="No"):
            return
    
    # Check if a valid frame range has been specified.
    frames = scriptDialog.GetValue( "FramesBox" )
    if( not FrameUtils.FrameRangeValid( frames ) ):
        scriptDialog.ShowMessageBox( "Frame range %s is not valid" % frames, "Error" )
        return
    
    # Check the output file
    regionRendering = False
    singleRegionJob = False
    regionJobCount = 1
    tilesInX = 1
    tilesInY = 1
    outputFile = ""
    paddedOutputFile = ""
    if scriptDialog.GetValue("OutputLabel"):
        outputFile = scriptDialog.GetValue("OutputBox").strip()
        if outputFile == "":
            scriptDialog.ShowMessageBox( "Please specify an output file.", "Error" )
            return
        elif(not Directory.Exists(Path.GetDirectoryName(outputFile))):
            scriptDialog.ShowMessageBox( "The directory of the output file does not exist:\n" + Path.GetDirectoryName(outputFile), "Error" )
            return
        
        if paddedNumberRegex.IsMatch( outputFile ):
            paddingSize = int(paddedNumberRegex.Match( outputFile ).Groups[1].Value)
            padding = "#";
            while len(padding) < paddingSize:
                padding = padding + "#"
            paddedOutputFile = paddedNumberRegex.Replace( outputFile, padding )
        else:
            paddedOutputFile = outputFile.replace( "$F", "#" )
                
    if scriptDialog.GetValue( "DraftSubmitBox" ):
        if paddedOutputFile == "":
            scriptDialog.ShowMessageBox( "A Draft job can only be submitted if you override the Output File under the Houdini Options.", "Error" )
            return
        
        # Check for a Draft template in the case of a Custom Draft
        if( scriptDialog.GetValue( "DraftCustomRadio" ) and not IsValidDraftTemplate() ):
             return
            
    # Check the ifd file
    ifdFile = ""
    paddedIfdFile = ""
    if scriptDialog.GetValue("IFDLabel"):
        ifdFile = scriptDialog.GetValue("IFDBox").strip()
        if ifdFile == "":
            scriptDialog.ShowMessageBox( "Please specify an IFD file.", "Error" )
            return
        elif(not Directory.Exists(Path.GetDirectoryName(ifdFile))):
            scriptDialog.ShowMessageBox( "The directory of the ifd file does not exist:\n" + Path.GetDirectoryName(ifdFile), "Error" )
            return
        
        startFrame = FrameUtils.Parse( frames )[0]
        if paddedNumberRegex.IsMatch( ifdFile ):
            paddingSize = int(paddedNumberRegex.Match( ifdFile ).Groups[1].Value)
            padding = StringUtils.ToZeroPaddedString( startFrame, paddingSize, False )
            paddedIfdFile = paddedNumberRegex.Replace( ifdFile, padding )
        else:
            paddedIfdFile = ifdFile.replace( "$F", str(startFrame) )
    
    if scriptDialog.GetValue("OutputLabel"):
        if scriptDialog.GetValue("EnableTilesCheck"):
            regionRendering = True
            tilesInX = scriptDialog.GetValue("XTilesBox")
            tilesInY = scriptDialog.GetValue("YTilesBox")
            regionJobCount = tilesInX * tilesInY
            
            if scriptDialog.GetValue("SingleFrameEnabledCheck"):
                regionJobCount = 1
                singleRegionJob = True
                taskLimit = RepositoryUtils.GetJobTaskLimit()
                if tilesInX * tilesInY > taskLimit:
                    scriptDialog.ShowMessageBox("Unable to submit job with " + (str(tilesInX * tilesInY)) + " tasks.  Task Count exceeded Job Task Limit of "+str(taskLimit),"Error")
                    return
                
            if ifdFile != "" and scriptDialog.GetValue( "MantraBox" ):
                regionJobCount = 1
    
    # A renderer must be specified
    renderer = scriptDialog.GetValue("RendererBox")
    if(len(renderer)==0):
        scriptDialog.ShowMessageBox("No Render Node specified (for example, /out/mantra1).","Error")
        return
    
    jobIds = []
    jobCount = 0
    jobResult = ""
    
    for jobNum in range( 0, regionJobCount ):
        jobName = scriptDialog.GetValue( "NameBox" )
        
        modifiedName = jobName
        if regionRendering and not singleRegionJob and not( ifdFile != "" and scriptDialog.GetValue( "MantraBox" ) ):
            modifiedName = modifiedName + " - Region " + str(jobNum)
        
        batchName = jobName
        # Create job info file.
        jobInfoFilename = Path.Combine( GetDeadlineTempPath(), "houdini_job_info.job" )
        writer = StreamWriter( jobInfoFilename, False, Encoding.Unicode )
        writer.WriteLine( "Plugin=Houdini" )
        writer.WriteLine( "Name=%s" % modifiedName )
        
        writer.WriteLine( "Comment=%s" % scriptDialog.GetValue( "CommentBox" ) )
        writer.WriteLine( "Department=%s" % scriptDialog.GetValue( "DepartmentBox" ) )
        writer.WriteLine( "Pool=%s" % scriptDialog.GetValue( "PoolBox" ) )
        writer.WriteLine( "SecondaryPool=%s" % scriptDialog.GetValue( "SecondaryPoolBox" ) )
        writer.WriteLine( "Group=%s" % scriptDialog.GetValue( "GroupBox" ) )
        writer.WriteLine( "Priority=%s" % scriptDialog.GetValue( "PriorityBox" ) )
        writer.WriteLine( "TaskTimeoutMinutes=%s" % scriptDialog.GetValue( "TaskTimeoutBox" ) )
        writer.WriteLine( "EnableAutoTimeout=%s" % scriptDialog.GetValue( "AutoTimeoutBox" ) )
        writer.WriteLine( "ConcurrentTasks=%s" % scriptDialog.GetValue( "ConcurrentTasksBox" ) )
        writer.WriteLine( "LimitConcurrentTasksToNumberOfCpus=%s" % scriptDialog.GetValue( "LimitConcurrentTasksBox" ) )
        
        writer.WriteLine( "MachineLimit=%s" % scriptDialog.GetValue( "MachineLimitBox" ) )
        if( bool(scriptDialog.GetValue( "IsBlacklistBox" )) ):
            writer.WriteLine( "Blacklist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
        else:
            writer.WriteLine( "Whitelist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
        
        writer.WriteLine( "LimitGroups=%s" % scriptDialog.GetValue( "LimitGroupBox" ) )
        writer.WriteLine( "JobDependencies=%s" % scriptDialog.GetValue( "DependencyBox" ) )
        writer.WriteLine( "OnJobComplete=%s" % scriptDialog.GetValue( "OnJobCompleteBox" ) )
        
        if( bool(scriptDialog.GetValue( "SubmitSuspendedBox" )) ):
            writer.WriteLine( "InitialStatus=Suspended" )
        
        if singleRegionJob:
            if not( ifdFile != "" and scriptDialog.GetValue( "MantraBox" ) ):
                writer.WriteLine( "TileJob=True" )
                writer.WriteLine( "TileJobTilesInX=%s" % tilesInX )
                writer.WriteLine( "TileJobTilesInY=%s" % tilesInY )
                writer.WriteLine( "TileJobFrame=%s" % scriptDialog.GetValue( "SingleJobFrameBox" ) )
            else:
                writer.WriteLine( "Frames=%s" % scriptDialog.GetValue( "SingleJobFrameBox" ) ) 
        else:
            writer.WriteLine( "Frames=%s" % frames )
        
        if singleRegionJob:
            if ifdFile != "" and scriptDialog.GetValue( "MantraBox" ):
                writer.WriteLine( "ChunkSize=1" )
        else:
            writer.WriteLine( "ChunkSize=%s" %  scriptDialog.GetValue( "ChunkSizeBox" ) )
        
        doShotgun = False
        doDraft = False
        
        if singleRegionJob and not( ifdFile != "" and scriptDialog.GetValue( "MantraBox" ) ):
            tileName = paddedOutputFile
            paddingRegex = re.compile( "(#+)", re.IGNORECASE )
            matches = paddingRegex.findall( os.path.basename( tileName ) )
            if matches != None and len( matches ) > 0:
                paddingString = matches[ len( matches ) - 1 ]
                paddingSize = len( paddingString )
                padding = str(scriptDialog.GetValue( "SingleJobFrameBox" ))
                while len(padding) < paddingSize:
                    padding = "0" + padding
                
                padding = "_tile?_" + padding
                tileName = RightReplace( tileName, paddingString, padding, 1 )
            else:
                splitFilename = os.path.splitext(tileName)
                tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
            
            for currTile in range(0, tilesInX*tilesInY):
                regionOutputFileName = tileName.replace( "?", str(currTile) )
                writer.WriteLine( "OutputFilename0Tile%s=%s"%(currTile,regionOutputFileName) )

        elif ifdFile != "":
            writer.WriteLine( "OutputDirectory0=%s" % Path.GetDirectoryName(ifdFile) )
            if not scriptDialog.GetValue( "MantraBox" ):
                doShotgun = True
        elif paddedOutputFile != "":
            writer.WriteLine( "OutputFilename0=%s" % paddedOutputFile )
            doDraft = True
            doShotgun = True
            
        #Shotgun/Draft
        extraKVPIndex = 0
        groupBatch = False
        if scriptDialog.GetValue( "CreateVersionBox" ):
            if scriptDialog.GetValue( "IntegrationTypeBox" ) == "Shotgun":
                writer.WriteLine( "ExtraInfo0=%s" % shotgunSettings.get('TaskName', "") )
                writer.WriteLine( "ExtraInfo1=%s" % shotgunSettings.get('ProjectName', "") )
                writer.WriteLine( "ExtraInfo2=%s" % shotgunSettings.get('EntityName', "") )
                writer.WriteLine( "ExtraInfo3=%s" % scriptDialog.GetValue( "IntegrationVersionBox" ) )
                writer.WriteLine( "ExtraInfo4=%s" % scriptDialog.GetValue( "IntegrationDescriptionBox" ) )
                writer.WriteLine( "ExtraInfo5=%s" % shotgunSettings.get('UserName', "") )
                
                for key in shotgunSettings:
                    if key != 'DraftTemplate':
                        writer.WriteLine( "ExtraInfoKeyValue%d=%s=%s" % (extraKVPIndex, key, shotgunSettings[key]) )
                        extraKVPIndex += 1
                if scriptDialog.GetValue("IntegrationUploadMovieBox"):
                    writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True" % (extraKVPIndex) )
                    extraKVPIndex += 1
                    groupBatch = True
                if scriptDialog.GetValue("IntegrationUploadFilmStripBox"):
                    writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True" % (extraKVPIndex) )
                    extraKVPIndex += 1
                    groupBatch = True
            else:
                writer.WriteLine( "ExtraInfo0=%s" % fTrackSettings.get('FT_TaskName', "") )
                writer.WriteLine( "ExtraInfo1=%s" % fTrackSettings.get('FT_ProjectName', "") )
                writer.WriteLine( "ExtraInfo2=%s" % scriptDialog.GetValue( "IntegrationVersionBox" ) )
                writer.WriteLine( "ExtraInfo4=%s" % scriptDialog.GetValue( "IntegrationDescriptionBox" ) )
                writer.WriteLine( "ExtraInfo5=%s" % fTrackSettings.get('FT_Username', "") )
                for key in fTrackSettings:
                    writer.WriteLine( "ExtraInfoKeyValue%d=%s=%s" % (extraKVPIndex, key, fTrackSettings[key]) )
                    extraKVPIndex += 1
                if scriptDialog.GetValue("IntegrationUploadMovieBox"):
                    writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateFTMovie=True" % (extraKVPIndex) )
                    extraKVPIndex += 1
                    groupBatch = True
        if scriptDialog.GetValue( "DraftSubmitBox" ):
            extraKVPIndex =  WriteDraftJobInfo( writer, extraKVPIndex )
            groupBatch = True
            
        if ifdFile != "" and scriptDialog.GetValue( "MantraBox" ):
            groupBatch = True
            
        if regionRendering:
            groupBatch = True
            
        if groupBatch:
            writer.WriteLine( "BatchName=%s" % (jobName ) ) 
        writer.Close()
        
        # Create plugin info file.
        pluginInfoFilename = Path.Combine( GetDeadlineTempPath(), "houdini_plugin_info.job" )
        writer = StreamWriter( pluginInfoFilename, False, Encoding.Unicode )
        
        if(not scriptDialog.GetValue("SubmitSceneBox")):
            writer.WriteLine("SceneFile=" + sceneFile.replace("\\","/"))
        writer.WriteLine("Output=" + outputFile.replace("\\","/"))
        writer.WriteLine("IFD=" + ifdFile.replace("\\","/"))
        writer.WriteLine("OutputDriver=" + renderer)
        writer.WriteLine("IgnoreInputs=%s" % scriptDialog.GetValue("IgnoreInputsBox"))
        writer.WriteLine("Version=" + scriptDialog.GetValue("VersionBox"))
        writer.WriteLine("Build=" + scriptDialog.GetValue("BuildBox"))
        
        if regionRendering and not( ifdFile != "" and scriptDialog.GetValue( "MantraBox" ) ):
            writer.WriteLine( "RegionRendering=True" )
            
            if singleRegionJob:
                curRegion = 0
                for y in range(0, tilesInY):
                    for x in range(0, tilesInX):
                        
                        xstart = x * 1.0 / tilesInX
                        xend = ( x + 1.0 ) / tilesInX
                        ystart = y * 1.0 / tilesInY
                        yend = ( y + 1.0 ) / tilesInY
                        
                        writer.WriteLine( "RegionLeft%s=%s" % (curRegion, xstart) )
                        writer.WriteLine( "RegionRight%s=%s" % (curRegion, xend) )
                        writer.WriteLine( "RegionBottom%s=%s" % (curRegion, ystart) )
                        writer.WriteLine( "RegionTop%s=%s" % (curRegion,yend) )
                        curRegion += 1
            else:
                writer.WriteLine( "CurrentTile=%s" % jobNum )
                
                curY = 0
                curX = 0
                jobNumberFound = False
                tempJobNum = 0
                for y in range(0, tilesInY):
                    for x in range(0, tilesInX):
                        if tempJobNum == jobNum:
                            curY = y
                            curX = x
                            jobNumberFound = True
                            break
                        tempJobNum = tempJobNum + 1
                    if jobNumberFound:
                        break
                
                xstart = curX * 1.0 / tilesInX
                xend = ( curX + 1.0 ) / tilesInX
                ystart = curY * 1.0 / tilesInY
                yend = ( curY + 1.0 ) / tilesInY
            
                writer.WriteLine( "RegionLeft=%s" % xstart )
                writer.WriteLine( "RegionRight=%s" % xend )
                writer.WriteLine( "RegionBottom=%s" % ystart )
                writer.WriteLine( "RegionTop=%s" % yend )
        
        writer.Close()
        
        arguments = []
        arguments.append( jobInfoFilename )
        arguments.append( pluginInfoFilename )
        if scriptDialog.GetValue( "SubmitSceneBox" ):
            arguments.Add( sceneFile )
            
        jobResult = results = ClientUtils.ExecuteCommandAndGetOutput( arguments )
        jobId = "";
        resultArray = jobResult.split("\n")
        for line in resultArray:
            if line.startswith("JobID="):
                jobId = line.replace("JobID=","")
                jobId = jobId.strip()
                break
        
        jobIds.append(jobId)
        jobCount += 1
        
    if ifdFile != "" and scriptDialog.GetValue( "MantraBox" ):    
        mantraJobCount = 1
        if regionRendering and not singleRegionJob:
            mantraJobCount = tilesInX*tilesInY
        
        mantraJobDependencies = ",".join(jobIds)
        jobIds = []
        
        for mantraJobNum in range( 0, mantraJobCount ):
            mantraJobInfoFilename = Path.Combine( GetDeadlineTempPath(), "mantra_job_info.job" )
            mantraPluginInfoFilename = Path.Combine( GetDeadlineTempPath(), "mantra_plugin_info.job" )
            
            mantraJobName = jobName + " - Mantra Job"
            if regionRendering and not singleRegionJob:
                mantraJobName = mantraJobName + " - Region " + str(mantraJobNum)
            
            # Create mantra job and plugin info file if necessary
            writer = StreamWriter( mantraJobInfoFilename, False, Encoding.Unicode )
            writer.WriteLine( "Plugin=Mantra" )
            writer.WriteLine( "Name=%s" % mantraJobName )
            writer.WriteLine( "BatchName=%s" % batchName )
            writer.WriteLine( "Comment=%s" % scriptDialog.GetValue( "CommentBox" ) )
            writer.WriteLine( "Department=%s" % scriptDialog.GetValue( "DepartmentBox" ) )
            writer.WriteLine( "Pool=%s" % scriptDialog.GetValue( "MantraPoolBox" ) )
            writer.WriteLine( "SecondaryPool=%s" % scriptDialog.GetValue( "MantraSecondaryPoolBox" ) )
            writer.WriteLine( "Group=%s" % scriptDialog.GetValue( "MantraGroupBox" ) )
            writer.WriteLine( "Priority=%s" % scriptDialog.GetValue( "MantraPriorityBox" ) )
            writer.WriteLine( "TaskTimeoutMinutes=%s" % scriptDialog.GetValue( "MantraTaskTimeoutBox" ) )
            writer.WriteLine( "EnableAutoTimeout=%s" % scriptDialog.GetValue( "MantraAutoTimeoutBox" ) )
            writer.WriteLine( "ConcurrentTasks=%s" % scriptDialog.GetValue( "MantraConcurrentTasksBox" ) )
            writer.WriteLine( "LimitConcurrentTasksToNumberOfCpus=%s" % scriptDialog.GetValue( "MantraLimitConcurrentTasksBox" ) )
            writer.WriteLine( "JobDependencies=%s" % mantraJobDependencies )
            
            writer.WriteLine( "MachineLimit=%s" % scriptDialog.GetValue( "MantraMachineLimitBox" ) )
            if( bool(scriptDialog.GetValue( "MantraIsBlacklistBox" )) ):
                writer.WriteLine( "Blacklist=%s" % scriptDialog.GetValue( "MantraMachineListBox" ) )
            else:
                writer.WriteLine( "Whitelist=%s" % scriptDialog.GetValue( "MantraMachineListBox" ) )
            
            writer.WriteLine( "LimitGroups=%s" % scriptDialog.GetValue( "MantraLimitGroupBox" ) )
            writer.WriteLine( "OnJobComplete=%s" % scriptDialog.GetValue( "OnJobCompleteBox" ) )
            
            if( bool(scriptDialog.GetValue( "SubmitSuspendedBox" )) ):
                writer.WriteLine( "InitialStatus=Suspended" )
            
            if singleRegionJob:
                writer.WriteLine( "TileJob=True" )
                writer.WriteLine( "TileJobTilesInX=%s" % tilesInX )
                writer.WriteLine( "TileJobTilesInY=%s" % tilesInY )
                writer.WriteLine( "TileJobFrame=%s" % scriptDialog.GetValue( "SingleJobFrameBox" )  )
            else:
                writer.WriteLine( "Frames=%s" % frames )
                writer.WriteLine( "ChunkSize=1")
                writer.WriteLine( "IsFrameDependent=true" )
            
            if paddedOutputFile != "":
                if singleRegionJob:
                    tileName = paddedOutputFile
                    paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                    matches = paddingRegex.findall( os.path.basename( tileName ) )
                    if matches != None and len( matches ) > 0:
                        paddingString = matches[ len( matches ) - 1 ]
                        paddingSize = len( paddingString )
                        padding = str(scriptDialog.GetValue( "SingleJobFrameBox" ))
                        while len(padding) < paddingSize:
                            padding = "0" + padding
                        
                        padding = "_tile?_" + padding
                        tileName = RightReplace( tileName, paddingString, padding, 1 )
                    else:
                        splitFilename = os.path.splitext(tileName)
                        tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
                    
                    for currTile in range(0, tilesInX*tilesInY):
                        regionOutputFileName = tileName.replace( "?", str(currTile) )
                        writer.WriteLine( "OutputFilename0Tile%s=%s"%(currTile,regionOutputFileName) )
                        
                else:
                    writer.WriteLine( "OutputFilename0=%s" % paddedOutputFile )
                
                #Shotgun/Draft
                extraKVPIndex = 0
                if scriptDialog.GetValue( "CreateVersionBox" ):
                    if scriptDialog.GetValue( "IntegrationTypeBox" ):
                        writer.WriteLine( "ExtraInfo0=%s" % shotgunSettings.get('TaskName', "") )
                        writer.WriteLine( "ExtraInfo1=%s" % shotgunSettings.get('ProjectName', "") )
                        writer.WriteLine( "ExtraInfo2=%s" % shotgunSettings.get('EntityName', "") )
                        writer.WriteLine( "ExtraInfo3=%s" % scriptDialog.GetValue( "IntegrationVersionBox" ) )
                        writer.WriteLine( "ExtraInfo4=%s" % scriptDialog.GetValue( "IntegrationDescriptionBox" ) )
                        writer.WriteLine( "ExtraInfo5=%s" % shotgunSettings.get('UserName', "") )
                        
                        for key in shotgunSettings:
                            if key != 'DraftTemplate':
                                writer.WriteLine( "ExtraInfoKeyValue%d=%s=%s" % (extraKVPIndex, key, shotgunSettings[key]) )
                                extraKVPIndex += 1
                        if scriptDialog.GetValue("IntegrationUploadMovieBox"):
                            writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True" % (extraKVPIndex) )
                            extraKVPIndex += 1
                        if scriptDialog.GetValue("IntegrationUploadFilmStripBox"):
                            writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True" % (extraKVPIndex) )
                            extraKVPIndex += 1
                    else:
                        writer.WriteLine( "ExtraInfo0=%s" % fTrackSettings.get('FT_TaskName', "") )
                        writer.WriteLine( "ExtraInfo1=%s" % fTrackSettings.get('FT_ProjectName', "") )
                        writer.WriteLine( "ExtraInfo2=%s" % fTrackSettings.get('FT_AssetName', "") )
                        writer.WriteLine( "ExtraInfo4=%s" % fTrackSettings.get('FT_Description', "") )
                        writer.WriteLine( "ExtraInfo5=%s" % fTrackSettings.get('FT_Username', "") )
                        for key in fTrackSettings:
                            writer.WriteLine( "ExtraInfoKeyValue%d=%s=%s" % (extraKVPIndex, key, fTrackSettings[key]) )
                            extraKVPIndex += 1
                        if scriptDialog.GetValue("IntegrationUploadMovieBox"):
                            writer.WriteLine( "ExtraInfoKeyValue%s=Draft_CreateFTMovie=True" % (extraKVPIndex) )
                            extraKVPIndex += 1
                if scriptDialog.GetValue( "DraftSubmitBox" ):
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftTemplate=%s" % (extraKVPIndex, scriptDialog.GetValue( "DraftTemplateBox" ) ) )
                    extraKVPIndex += 1
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftUsername=%s" % (extraKVPIndex, scriptDialog.GetValue( "DraftUserBox" ) ) )
                    extraKVPIndex += 1
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftEntity=%s" % (extraKVPIndex, scriptDialog.GetValue( "DraftEntityBox" ) ) )
                    extraKVPIndex += 1
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftVersion=%s" % (extraKVPIndex, scriptDialog.GetValue( "DraftVersionBox" ) ) )
                    extraKVPIndex += 1
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s" % (extraKVPIndex, scriptDialog.GetValue( "DraftUploadShotgunBox" ) and scriptDialog.GetValue( "CreateVersionBox" ) and (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun") ) )
                    extraKVPIndex += 1
                    writer.WriteLine( "ExtraInfoKeyValue%d=DraftExtraArgs=%s" % (extraKVPIndex, scriptDialog.GetValue( "ArgsBox" ) ) )
                    extraKVPIndex += 1
            
            writer.Close()
            
            # Create plugin info file.
            writer = StreamWriter( mantraPluginInfoFilename, False, Encoding.Unicode )
            writer.WriteLine("SceneFile=" + paddedIfdFile)
            writer.WriteLine("Version=" + scriptDialog.GetValue("VersionBox"))
            writer.WriteLine("Threads=" + str(scriptDialog.GetValue("ThreadsBox")))
            writer.WriteLine("OutputFile=" + outputFile)
            writer.WriteLine("CommandLineOptions=")
            
            if regionRendering:
                writer.WriteLine( "RegionRendering=True" )
                if singleRegionJob:
                    curRegion = 0
                    for y in range(0, tilesInY):
                        for x in range(0, tilesInX):
                            
                            xstart = x * 1.0 / tilesInX
                            xend = ( x + 1.0 ) / tilesInX
                            ystart = y * 1.0 / tilesInY
                            yend = ( y + 1.0 ) / tilesInY
                            
                            writer.WriteLine( "RegionLeft%s=%s" % (curRegion, xstart) )
                            writer.WriteLine( "RegionRight%s=%s" % (curRegion, xend) )
                            writer.WriteLine( "RegionBottom%s=%s" % (curRegion, ystart) )
                            writer.WriteLine( "RegionTop%s=%s" % (curRegion,yend) )
                            curRegion += 1
                else:
                    writer.WriteLine( "CurrentTile=%s" % mantraJobNum )
                    
                    curY = 0
                    curX = 0
                    jobNumberFound = False
                    tempJobNum = 0
                    for y in range(0, tilesInY):
                        for x in range(0, tilesInX):
                            if tempJobNum == mantraJobNum:
                                curY = y
                                curX = x
                                jobNumberFound = True
                                break
                            tempJobNum = tempJobNum + 1
                        if jobNumberFound:
                            break
                    
                    xstart = curX * 1.0 / tilesInX
                    xend = ( curX + 1.0 ) / tilesInX
                    ystart = curY * 1.0 / tilesInY
                    yend = ( curY + 1.0 ) / tilesInY
                
                    writer.WriteLine( "RegionLeft=%s" % xstart )
                    writer.WriteLine( "RegionRight=%s" % xend )
                    writer.WriteLine( "RegionBottom=%s" % ystart )
                    writer.WriteLine( "RegionTop=%s" % yend )
            
            writer.Close()
            
            arguments = []
            arguments.append( mantraJobInfoFilename )
            arguments.append( mantraPluginInfoFilename )
                
            jobResult = ClientUtils.ExecuteCommandAndGetOutput( arguments )
            jobId = "";
            resultArray = jobResult.split("\n")
            for line in resultArray:
                if line.startswith("JobID="):
                    jobId = line.replace("JobID=","")
                    jobId = jobId.strip()
                    break
            
            jobIds.append(jobId)
            jobCount += 1
            
    if regionRendering and scriptDialog.GetValue("SubmitDependentCheck"):
        
        jobName = scriptDialog.GetValue( "NameBox" )
        jobName = "%s - Assembly"%(jobName)
        
        # Create submission info file
        jigsawJobInfoFilename = Path.Combine( GetDeadlineTempPath(), "jigsaw_submit_info.job" )
        jigsawPluginInfoFilename = Path.Combine( GetDeadlineTempPath(), "jigsaw_plugin_info.job" )        
        
        writer = StreamWriter( jigsawJobInfoFilename, False, Encoding.Unicode )
        writer.WriteLine( "Plugin=DraftTileAssembler" )
        writer.WriteLine( "Name=%s" % jobName )
        writer.WriteLine( "Comment=%s" % scriptDialog.GetValue( "CommentBox" ) )
        writer.WriteLine( "Department=%s" % scriptDialog.GetValue( "DepartmentBox" ) )
        writer.WriteLine( "Pool=%s" % scriptDialog.GetValue( "MantraPoolBox" ) )
        writer.WriteLine( "SecondaryPool=%s" % scriptDialog.GetValue( "MantraSecondaryPoolBox" ) )
        writer.WriteLine( "Group=%s" % scriptDialog.GetValue( "MantraGroupBox" ) )
        writer.WriteLine( "Priority=%s" % scriptDialog.GetValue( "MantraPriorityBox" ) )
        writer.WriteLine( "TaskTimeoutMinutes=%s" % scriptDialog.GetValue( "MantraTaskTimeoutBox" ) )
        writer.WriteLine( "EnableAutoTimeout=%s" % scriptDialog.GetValue( "MantraAutoTimeoutBox" ) )
        writer.WriteLine( "ConcurrentTasks=%s" % scriptDialog.GetValue( "MantraConcurrentTasksBox" ) )
        writer.WriteLine( "LimitConcurrentTasksToNumberOfCpus=%s" % scriptDialog.GetValue( "MantraLimitConcurrentTasksBox" ) )
        writer.WriteLine( "MachineLimit=%s" % scriptDialog.GetValue( "MachineLimitBox" ) )
        if( bool(scriptDialog.GetValue( "IsBlacklistBox" )) ):
            writer.WriteLine( "Blacklist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
        else:
            writer.WriteLine( "Whitelist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
            
        writer.WriteLine( "JobDependencies=%s" % ",".join(jobIds) )
        
        if( bool(scriptDialog.GetValue( "SubmitSuspendedBox" )) ):
            writer.WriteLine( "InitialStatus=Suspended" )
        
        if singleRegionJob:
            writer.WriteLine( "Frames=%s" % scriptDialog.GetValue( "SingleJobFrameBox" ) )
        else:
            writer.WriteLine( "Frames=%s" % frames )
        #writer.WriteLine( "Frames=0-%i" % (len(frameList)-1) )
       
        writer.WriteLine( "ChunkSize=1" )
        
        if ifdFile != "":
            writer.WriteLine( "OutputDirectory0=%s" % Path.GetDirectoryName(ifdFile) )
        elif paddedOutputFile != "":
            writer.WriteLine( "OutputFilename0=%s" % paddedOutputFile )
        
        writer.WriteLine( "BatchName=%s" % (batchName ) ) 
        writer.Close()
        
        
        # Create plugin info file
        writer = StreamWriter( jigsawPluginInfoFilename, False, Encoding.Unicode )
        
        writer.WriteLine( "ErrorOnMissing=%s\n" % (scriptDialog.GetValue( "ErrorOnMissingCheck" )) )
        writer.WriteLine( "ErrorOnMissingBackground=%s\n" % (scriptDialog.GetValue( "ErrorOnMissingBackgroundCheck" )) )
        writer.WriteLine( "CleanupTiles=%s\n" % (scriptDialog.GetValue( "CleanupTilesCheck" )) )
        writer.WriteLine( "MultipleConfigFiles=%s\n" % True )
        
        writer.Close()
        
        configFiles = []
        
        frameList = []
        if singleRegionJob:
            frameList = [scriptDialog.GetValue( "SingleJobFrameBox" )]
        else:
            frameList = FrameUtils.Parse( frames )
        
        for frame in frameList:
            imageFileName = paddedOutputFile.replace("\\","/")
            
            tileName = imageFileName
            outputName = imageFileName
            paddingRegex = re.compile( "(#+)", re.IGNORECASE )
            matches = paddingRegex.findall( os.path.basename( imageFileName ) )
            if matches != None and len( matches ) > 0:
                paddingString = matches[ len( matches ) - 1 ]
                paddingSize = len( paddingString )
                padding = str(frame)
                while len(padding) < paddingSize:
                    padding = "0" + padding
                
                outputName = RightReplace( imageFileName, paddingString, padding, 1 )
                padding = "_tile?_" + padding
                tileName = RightReplace( imageFileName, paddingString, padding, 1 )
            else:
                outputName = imageFileName
                splitFilename = os.path.splitext(imageFileName)
                tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
            
            date = time.strftime("%Y_%m_%d_%H_%M_%S")
            configFilename = Path.Combine( GetDeadlineTempPath(), outputName+"_"+str(frame)+"_config_"+date+".txt" )
            writer = StreamWriter( configFilename, False, Encoding.Unicode )
            writer.WriteLine( "" )
            writer.WriteLine( "ImageFileName=" +outputName )
            backgroundType = scriptDialog.GetValue( "AssembleOverBox" )
            if backgroundType == "Previous Output":
                fileHandle.write( "BackgroundSource=" +outputName +"\n" )
            elif backgroundType == "Selected Image":
                fileHandle.write( "BackgroundSource=" +scriptDialog.GetValue( "BackgroundBox" ) +"\n" )
            
            writer.WriteLine( "TilesCropped=False" )
            writer.WriteLine( "TileCount=" +str( tilesInX * tilesInY ) )
            writer.WriteLine( "DistanceAsPixels=False" )
            
            currTile = 0
            for y in range(0, tilesInY):
                for x in range(0, tilesInX):
                    width = 1.0/tilesInX
                    height = 1.0/tilesInY
                    xRegion = x*width
                    yRegion = y*height
                    
                    regionOutputFileName = tileName.replace( "?", str(currTile) )
                    
                    writer.WriteLine( "Tile%iFileName=%s"%(currTile,regionOutputFileName) )
                    writer.WriteLine( "Tile%iX=%s"%(currTile,xRegion) )
                    writer.WriteLine( "Tile%iY=%s"%(currTile,yRegion) )
                    writer.WriteLine( "Tile%iWidth=%s"%(currTile,width) )
                    writer.WriteLine( "Tile%iHeight=%s"%(currTile,height) )
                    currTile += 1
            
            writer.Close()
            configFiles.append(configFilename)
        
        arguments = []
        arguments.append( jigsawJobInfoFilename )
        arguments.append( jigsawPluginInfoFilename )
        arguments.extend( configFiles )
        jobResult = ClientUtils.ExecuteCommandAndGetOutput( arguments )
        jobCount += 1
    
    if jobCount == 1:
        scriptDialog.ShowMessageBox( jobResult, "Submission Results" )
    else:
        scriptDialog.ShowMessageBox( ("All %d jobs submitted" % jobCount), "Submission Results" )
    