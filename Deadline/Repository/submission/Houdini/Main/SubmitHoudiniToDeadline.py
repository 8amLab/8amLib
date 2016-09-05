import sys
import os
import subprocess
import traceback
import re
import hou
import time
import threading
import socket
import uuid
import tempfile
import platform

try:
    import ConfigParser
except:
    print( "Could not load ConfigParser module, sticky settings will not be loaded/saved" )

dialog = None
closing = False
shotgunSettings = {}
fTrackSettings = {}
pulledFTrackSettings = {}

containsWedge = False

maxPriority = 0
homeDir = ""
deadlineSettings = ""
deadlineTemp = ""
configFile = ""
shotgunScript = ""
ftrackScript = ""
scriptRoot = ""

Formats = []
Resolutions = []
FrameRates = []
Restrictions = []

FormatsDict = {}
ResolutionsDict = {}
CodecsDict = {}
RestrictionsDict = {}


jigsawThread = None

def CallDeadlineCommand( arguments, background=True, readStdout=True ):
    # On OSX, we look for the DEADLINE_PATH file. On other platforms, we use the environment variable.
    if os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with file( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f: deadlineBin = f.read().strip()
        deadlineCommand = os.path.join( deadlineBin, "deadlinecommand" )
    else:
        deadlineBin = os.environ['DEADLINE_PATH']
        if os.name == 'nt':
            deadlineCommand = os.path.join( deadlineBin, "deadlinecommand.exe" )
        else:
            deadlineCommand = os.path.join( deadlineBin, "deadlinecommand" )

    startupinfo = None
    if background and os.name == 'nt':
        # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
        if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    arguments.insert( 0, deadlineCommand)
    
    stdoutPipe = None
    if readStdout:
        stdoutPipe=subprocess.PIPE
        
    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, cwd=deadlineBin, stdin=subprocess.PIPE, stdout=stdoutPipe, stderr=subprocess.PIPE, startupinfo=startupinfo)
    proc.stdin.close()
    proc.stderr.close()

    output = ""
    if readStdout:
        output = proc.stdout.read()
    return output

def WriteStickySettings():
    global dialog, configFile

    try:
        print "Writing sticky settings..."
        config = ConfigParser.ConfigParser()
        config.add_section( "Sticky" )

        # sticky stuff
        config.set( "Sticky", "Department", dialog.value( "department.val" ) )
        config.set( "Sticky", "Pool", dialog.value( "pool.val" ) )
        config.set( "Sticky", "SecondaryPool", dialog.value( "secondarypool.val" ) )
        config.set( "Sticky", "Group", dialog.value( "group.val" ) )
        config.set( "Sticky", "Priority", dialog.value( "priority.val" ) ) 
        config.set( "Sticky", "MachineLimit", dialog.value( "machinelimit.val" ) ) 
        config.set( "Sticky", "IsBlacklist", dialog.value( "isblacklist.val" ) ) 
        config.set( "Sticky", "MachineList", dialog.value( "machinelist.val" ) )
        config.set( "Sticky", "LimitGroups", dialog.value( "limits.val" ) )
        config.set( "Sticky", "SubmitSuspended", dialog.value( "jobsuspended.val" ) )
        config.set( "Sticky", "ChunkSize", dialog.value( "framespertask.val" ) ) 
        config.set( "Sticky", "ConcurrentTasks", dialog.value( "concurrent.val" ) ) 
        config.set( "Sticky", "LimitConcurrentTasks", dialog.value( "slavelimit.val" ) ) 
        config.set( "Sticky", "IgnoreInputs", dialog.value( "ignoreinputs.val" ) ) 
        config.set( "Sticky", "SubmitScene", dialog.value( "submitscene.val" ) ) 
        config.set( "Sticky", "SubmitMantra", dialog.value( "mantrajob.val" ) ) 
        config.set( "Sticky", "MantraThreads", dialog.value( "mantrathreads.val" ) ) 
        config.set( "Sticky", "MantraPool", dialog.value( "mantrapool.val" ) )
        config.set( "Sticky", "MantraSecondaryPool", dialog.value( "mantrasecondarypool.val" ) )
        config.set( "Sticky", "MantraGroup", dialog.value( "mantragroup.val" ) )
        config.set( "Sticky", "MantraPriority", dialog.value( "mantrapriority.val" ) ) 
        config.set( "Sticky", "MantraMachineLimit", dialog.value( "mantramachinelimit.val" ) ) 
        config.set( "Sticky", "MantraIsBlacklist", dialog.value( "mantraisblacklist.val" ) ) 
        config.set( "Sticky", "MantraMachineList", dialog.value( "mantramachinelist.val" ) )
        config.set( "Sticky", "MantraLimitGroups", dialog.value( "mantralimits.val" ) )
        config.set( "Sticky", "MantraConcurrentTasks", dialog.value( "mantraconcurrent.val" ) ) 
        config.set( "Sticky", "MantraLimitConcurrentTasks", dialog.value( "mantraslavelimit.val" ) ) 
        
        config.set( "Sticky", "SubmitArnold", dialog.value( "arnoldjob.val" ) ) 
        config.set( "Sticky", "ArnoldThreads", dialog.value( "arnoldthreads.val" ) ) 
        config.set( "Sticky", "ArnoldPool", dialog.value( "arnoldpool.val" ) )
        config.set( "Sticky", "ArnoldSecondaryPool", dialog.value( "arnoldsecondarypool.val" ) )
        config.set( "Sticky", "ArnoldGroup", dialog.value( "arnoldgroup.val" ) )
        config.set( "Sticky", "ArnoldPriority", dialog.value( "arnoldpriority.val" ) ) 
        config.set( "Sticky", "ArnoldMachineLimit", dialog.value( "arnoldmachinelimit.val" ) ) 
        config.set( "Sticky", "ArnoldIsBlacklist", dialog.value( "arnoldisblacklist.val" ) ) 
        config.set( "Sticky", "ArnoldMachineList", dialog.value( "arnoldmachinelist.val" ) )
        config.set( "Sticky", "ArnoldLimitGroups", dialog.value( "arnoldlimits.val" ) )
        config.set( "Sticky", "ArnoldConcurrentTasks", dialog.value( "arnoldconcurrent.val" ) ) 
        config.set( "Sticky", "ArnoldLimitConcurrentTasks", dialog.value( "arnoldslavelimit.val" ) ) 
        
        config.set( "Sticky", "CleanupTiles", dialog.value( "cleanuptiles.val" ) ) 
        config.set( "Sticky", "ErrorOnMissingTiles", dialog.value( "erroronmissingtiles.val" ) ) 
        config.set( "Sticky", "ErroronMissingBackground", dialog.value( "erroronmissingbackground.val" ) )         
        
        # draft sticky
        config.set( "Sticky", "UseDraft", dialog.value( "draftsubmit.val" ) ) 

        config.set( "Sticky", "DraftUpload", dialog.value( "drafttoshotgun.val" ) ) 

        config.set( "Sticky", "DraftQuick", dialog.value( "draftQuick.val" ) ) 
        config.set( "Sticky", "DraftFormat", dialog.value( "draftFormat.val" ) ) 
        config.set( "Sticky", "DraftCodec", dialog.value( "draftCodec.val" ) ) 
        config.set( "Sticky", "DraftResolution", dialog.value( "draftResolution.val" ) ) 
        config.set( "Sticky", "DraftQuality", int( float( dialog.value( "draftQuality.val" ) ) ) ) 
        config.set( "Sticky", "DraftFrameRate", dialog.value( "draftFrameRate.val" ) ) 

        config.set( "Sticky", "DraftTemplate", dialog.value( "drafttemplate.val" ) )
        config.set( "Sticky", "DraftUser", dialog.value( "draftusername.val" ) )
        config.set( "Sticky", "DraftEntity", dialog.value( "draftentityname.val" ) )
        config.set( "Sticky", "DraftVersion", dialog.value( "draftversionname.val" ) )
        config.set( "Sticky", "DraftExtraArgs", dialog.value( "draftadditionalargs.val" ) )

        fileHandle = open( configFile, "w" )
        config.write( fileHandle )
        fileHandle.close()

    except:
        print( "Could not write sticky settings" ) 
        print( traceback.format_exc() )

def SaveSceneFields():
    global dialog
    
    try:
        currentNode = hou.node( "/out")
        
        currentNode.setUserData("deadline_department", str(dialog.value( "department.val" ) ))
        currentNode.setUserData("deadline_pool", str(dialog.value( "pool.val" ) ))
        currentNode.setUserData("deadline_secpool", str(dialog.value( "secondarypool.val" ) ))
        currentNode.setUserData("deadline_group", str(dialog.value( "group.val" ) ))
        currentNode.setUserData("deadline_priority", str(dialog.value( "priority.val" ) ))
        currentNode.setUserData("deadline_machinelimit", str(dialog.value( "machinelimit.val" ) ))
        currentNode.setUserData("deadline_isblacklist", str(dialog.value( "isblacklist.val" ) ))
        currentNode.setUserData("deadline_machinelist", str(dialog.value( "machinelist.val" ) ))
        currentNode.setUserData("deadline_limits", str(dialog.value( "limits.val" ) ))
        currentNode.setUserData("deadline_jobsuspended", str(dialog.value( "jobsuspended.val" ) ))
        currentNode.setUserData("deadline_framespertask", str(dialog.value( "framespertask.val" ) ))
        currentNode.setUserData("deadline_concurrent", str(dialog.value( "concurrent.val" ) ))
        currentNode.setUserData("deadline_slavelimit", str(dialog.value( "slavelimit.val" ) ))
        currentNode.setUserData("deadline_ignoreinputs", str(dialog.value( "ignoreinputs.val" ) ))
        currentNode.setUserData("deadline_submitscene", str(dialog.value( "submitscene.val" ) ))
        currentNode.setUserData("deadline_mantrajob", str(dialog.value( "mantrajob.val" ) ))
        currentNode.setUserData("deadline_mantrathreads", str(dialog.value( "mantrathreads.val" ) ))
        currentNode.setUserData("deadline_mantrapool", str(dialog.value( "mantrapool.val" ) ))
        currentNode.setUserData("deadline_mantrasecondarypool", str(dialog.value( "mantrasecondarypool.val" ) ))
        currentNode.setUserData("deadline_mantragroup", str(dialog.value( "mantragroup.val" ) ))
        currentNode.setUserData("deadline_mantrapriority", str(dialog.value( "mantrapriority.val" ) ))
        currentNode.setUserData("deadline_mantramachinelimit", str(dialog.value( "mantramachinelimit.val" ) ))
        currentNode.setUserData("deadline_mantraisblacklist", str(dialog.value( "mantraisblacklist.val" ) ))
        currentNode.setUserData("deadline_mantramachinelist", str(dialog.value( "mantramachinelist.val" ) ))
        currentNode.setUserData("deadline_mantralimits", str(dialog.value( "mantralimits.val" ) ))
        currentNode.setUserData("deadline_mantraconcurrent", str(dialog.value( "mantraconcurrent.val" ) ))
        currentNode.setUserData("deadline_mantraslavelimit", str(dialog.value( "mantraslavelimit.val" ) ))
        
        currentNode.setUserData("deadline_arnoldjob", str(dialog.value( "arnoldjob.val" ) ))
        currentNode.setUserData("deadline_arnoldthreads", str(dialog.value( "arnoldthreads.val" ) ))
        currentNode.setUserData("deadline_arnoldpool", str(dialog.value( "arnoldpool.val" ) ))
        currentNode.setUserData("deadline_arnoldsecondarypool", str(dialog.value( "arnoldsecondarypool.val" ) ))
        currentNode.setUserData("deadline_arnoldgroup", str(dialog.value( "arnoldgroup.val" ) ))
        currentNode.setUserData("deadline_arnoldpriority", str(dialog.value( "arnoldpriority.val" ) ))
        currentNode.setUserData("deadline_arnoldmachinelimit", str(dialog.value( "arnoldmachinelimit.val" ) ))
        currentNode.setUserData("deadline_arnoldisblacklist", str(dialog.value( "arnoldisblacklist.val" ) ))
        currentNode.setUserData("deadline_arnoldmachinelist", str(dialog.value( "arnoldmachinelist.val" ) ))
        currentNode.setUserData("deadline_arnoldlimits", str(dialog.value( "arnoldlimits.val" ) ))
        currentNode.setUserData("deadline_arnoldconcurrent", str(dialog.value( "arnoldconcurrent.val" ) ))
        currentNode.setUserData("deadline_arnoldslavelimit", str(dialog.value( "arnoldslavelimit.val" ) ))
        
        currentNode.setUserData("deadline_tilesenabled", str(dialog.value( "tilesenabled.val" ) ))
        currentNode.setUserData("deadline_jigsawenabled", str(dialog.value( "jigsawenabled.val" ) ))
        
        currentNode.setUserData("deadline_tilesinx", str(dialog.value( "tilesinx.val" ) ))
        currentNode.setUserData("deadline_tilesiny", str(dialog.value( "tilesiny.val" ) ))
        
        currentNode.setUserData("deadline_tilessingleframeenabled", str(dialog.value( "tilessingleframeenabled.val" ) ))
        currentNode.setUserData("deadline_tilessingleframe", str(dialog.value( "tilessingleframe.val" ) ))
        currentNode.setUserData("deadline_submitdependentassembly", str(dialog.value( "submitdependentassembly.val" ) ))
        currentNode.setUserData("deadline_cleanuptiles", str(dialog.value( "cleanuptiles.val" ) ))
        currentNode.setUserData("deadline_erroronmissingtiles", str(dialog.value( "erroronmissingtiles.val" ) ))
        currentNode.setUserData("deadline_erroronmissingbackground", str(dialog.value( "erroronmissingbackground.val" ) ))
        currentNode.setUserData("deadline_backgroundoption", str(dialog.value( "backgroundoption.val" ) ))
        currentNode.setUserData("deadline_backgroundimagelabel", str(dialog.value( "backgroundimagelabel.val" ) ))
        currentNode.setUserData("deadline_backgroundimage", str(dialog.value( "backgroundimage.val" ) ))
        
        currentNode.setUserData("deadline_draftsubmit", str(dialog.value( "draftsubmit.val" ) ))

        currentNode.setUserData("deadline_draftupload", str(dialog.value( "drafttoshotgun.val" ) ))

        currentNode.setUserData("deadline_draftquick", str(dialog.value( "draftQuick.val" ) ))
        currentNode.setUserData("deadline_draftformat", str(dialog.value( "draftFormat.val" ) ))
        currentNode.setUserData("deadline_draftcodec", str(dialog.value( "draftCodec.val" ) ))
        currentNode.setUserData("deadline_draftresolution", str(dialog.value( "draftResolution.val" ) ))
        currentNode.setUserData("deadline_draftquality", str(int( float( dialog.value( "draftQuality.val" ) ) ) ))
        currentNode.setUserData("deadline_draftframerate", str(dialog.value( "draftFrameRate.val" ) ))

        currentNode.setUserData("deadline_drafttemplate", str(dialog.value( "drafttemplate.val" ) ))
        currentNode.setUserData("deadline_draftusername", str(dialog.value( "draftusername.val" ) ))
        currentNode.setUserData("deadline_draftentityname", str(dialog.value( "draftentityname.val" ) ))
        currentNode.setUserData("deadline_draftversionname", str(dialog.value( "draftversionname.val" ) ))
        currentNode.setUserData("deadline_draftadditionalargs", str(dialog.value( "draftadditionalargs.val" ) ))
        
        
    except:
        print( "Could not write submission settings to scene" ) 
        print( traceback.format_exc() )
        
def LoadSceneFileSubmissionSettings():
    global dialog
    
    currentNode = hou.node( "/out")
    
    try:
        data = currentNode.userData("deadline_department")
        if data != None:
            dialog.setValue("department.val", data)
            
        data = currentNode.userData("deadline_pool")
        if data != None:
            dialog.setValue("pool.val", data)
            
        data = currentNode.userData("deadline_secpool")
        if data != None:
            dialog.setValue("secondarypool.val", data)
            
        data = currentNode.userData("deadline_group")
        if data != None:
            dialog.setValue("group.val", data)
            
        data = currentNode.userData("deadline_priority")
        if data != None:
            data = int(data)
            dialog.setValue("priority.val", data)
            
        data = currentNode.userData("deadline_machinelimit")
        if data != None:
            data = int(data)
            dialog.setValue("machinelimit.val", data)
            
        data = currentNode.userData("deadline_isblacklist")
        if data != None:
            data = int(data)
            dialog.setValue("isblacklist.val", data)
            
        data = currentNode.userData("deadline_machinelist")
        if data != None:
            dialog.setValue("machinelist.val", data)
            
        data = currentNode.userData("deadline_limits")
        if data != None:
            dialog.setValue("limits.val", data)
            
        data = currentNode.userData("deadline_jobsuspended")
        if data != None:
            data = int(data)
            dialog.setValue("jobsuspended.val", data)
            
        data = currentNode.userData("deadline_framespertask")
        if data != None:
            data = int(data)
            dialog.setValue("framespertask.val", data)
            
        data = currentNode.userData("deadline_concurrent")
        if data != None:
            data = int(data)
            dialog.setValue("concurrent.val", data)
            
        data = currentNode.userData("deadline_slavelimit")
        if data != None:
            data = int(data)
            dialog.setValue("slavelimit.val", data)
            
        data = currentNode.userData("deadline_ignoreinputs")
        if data != None:
            data = int(data)
            dialog.setValue("ignoreinputs.val", data)
            
        data = currentNode.userData("deadline_submitscene")
        if data != None:
            data = int(data)
            dialog.setValue("submitscene.val", data)
            
        data = currentNode.userData("deadline_mantrajob")
        if data != None:
            data = int(data)
            dialog.setValue("mantrajob.val", data)
            
        data = currentNode.userData("deadline_mantrathreads")
        if data != None:
            data = int(data)
            dialog.setValue("mantrathreads.val", data)
            
        data = currentNode.userData("deadline_mantrapool")
        if data != None:
            dialog.setValue("mantrapool.val", data)
            
        data = currentNode.userData("deadline_mantrasecondarypool")
        if data != None:
            dialog.setValue("mantrasecondarypool.val", data)
            
        data = currentNode.userData("deadline_mantragroup")
        if data != None:
            dialog.setValue("mantragroup.val", data)
            
        data = currentNode.userData("deadline_mantrapriority")
        if data != None:
            data = int(data)
            dialog.setValue("mantrapriority.val", data)
            
        data = currentNode.userData("deadline_mantramachinelimit")
        if data != None:
            data = int(data)
            dialog.setValue("mantramachinelimit.val", data)
            
        data = currentNode.userData("deadline_mantraisblacklist")
        if data != None:
            data = int(data)
            dialog.setValue("mantraisblacklist.val", data)
            
        data = currentNode.userData("deadline_mantramachinelist")
        if data != None:
            dialog.setValue("mantramachinelist.val", data)
            
        data = currentNode.userData("deadline_mantralimits")
        if data != None:
            dialog.setValue("mantralimits.val", data)
            
        data = currentNode.userData("deadline_mantraconcurrent")
        if data != None:
            data = int(data)
            dialog.setValue("mantraconcurrent.val", data)
            
        data = currentNode.userData("deadline_mantraslavelimit")
        if data != None and data != "":
            data = int(data)
            dialog.setValue("mantraslavelimit.val", data)
            
        data = currentNode.userData("deadline_arnoldjob")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldjob.val", data)
            
        data = currentNode.userData("deadline_arnoldthreads")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldthreads.val", data)
            
        data = currentNode.userData("deadline_mantrapool")
        if data != None:
            dialog.setValue("arnoldpool.val", data)
            
        data = currentNode.userData("deadline_arnoldsecondarypool")
        if data != None:
            dialog.setValue("arnoldsecondarypool.val", data)
            
        data = currentNode.userData("deadline_arnoldgroup")
        if data != None:
            dialog.setValue("arnoldgroup.val", data)
            
        data = currentNode.userData("deadline_arnoldpriority")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldpriority.val", data)
            
        data = currentNode.userData("deadline_arnoldmachinelimit")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldmachinelimit.val", data)
            
        data = currentNode.userData("deadline_arnoldisblacklist")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldisblacklist.val", data)
            
        data = currentNode.userData("deadline_arnoldmachinelist")
        if data != None:
            dialog.setValue("arnoldmachinelist.val", data)
            
        data = currentNode.userData("deadlinearnoldlimits")
        if data != None:
            dialog.setValue("mantralimits.val", data)
            
        data = currentNode.userData("deadline_arnoldconcurrent")
        if data != None:
            data = int(data)
            dialog.setValue("arnoldconcurrent.val", data)
            
        data = currentNode.userData("deadline_arnoldslavelimit")
        if data != None and data != "":
            data = int(data)
            dialog.setValue("arnoldslavelimit.val", data)
        
        data = currentNode.userData("deadline_tilesenabled")
        if data != None and data != "":
            data = int(data)
            dialog.setValue("tilesenabled.val", data)
        
        data = currentNode.userData("deadline_jigsawenabled")
        if data != None:
            data = int(data)
            dialog.setValue("jigsawenabled.val", data)
        
        
        data = currentNode.userData("deadline_tilesinx")
        if data != None and data != "":
            data = int(data)
            dialog.setValue("tilesinx.val", data)
        
        data = currentNode.userData("deadline_tilesiny")
        if data != None:
            data = int(data)
            dialog.setValue("tilesiny.val", data)
        
        data = currentNode.userData("deadline_tilessingleframeenabled")
        if data != None:
            data = int(data)
            dialog.setValue("tilessingleframeenabled.val", data)
        
        data = currentNode.userData("deadline_tilessingleframe")
        if data != None:
            data = int(data)
            dialog.setValue("tilessingleframe.val", data)
        
        data = currentNode.userData("deadline_submitdependentassembly")
        if data != None:
            data = int(data)
            dialog.setValue("submitdependentassembly.val", data)
            
        data = currentNode.userData("deadline_backgroundoption")
        if data != None:
            dialog.setValue("backgroundoption.val", data)
            
        data = currentNode.userData("deadline_backgroundimagelabel")
        if data != None:
            dialog.setValue("backgroundimagelabel.val", data)
        
        data = currentNode.userData("deadline_backgroundimage")
        if data != None:
            dialog.setValue("backgroundimage.val", data)
                
        data = currentNode.userData("deadline_draftsubmit")
        if data != None:
            data = int(data)
            dialog.setValue("draftsubmit.val", data)
        
        data = currentNode.userData("deadline_draftupload")
        if data != None:
            data = int(data)
            dialog.setValue("drafttoshotgun.val", data)
        
        data = currentNode.userData("deadline_draftquick")
        if data != None:
            data = int(data)
            dialog.setValue("draftQuick.val", data)
            dialog.setValue("draftCustom.val", int(not data))
            
        data = currentNode.userData("deadline_draftformat")
        if data != None:
            dialog.setValue("draftFormat.val", data)
            
        data = currentNode.userData("deadline_draftcodec")
        if data != None:
            dialog.setValue("draftCodec.val", data)
            
        data = currentNode.userData("deadline_draftresolution")
        if data != None:
            dialog.setValue("draftResolution.val", data)
            
        data = currentNode.userData("deadline_draftquality")
        if data != None and data != "":
            data = int(float(data))
            dialog.setValue("draftQuality.val", data)
            
        data = currentNode.userData("deadline_draftframerate")
        if data != None:
            dialog.setValue("draftFrameRate.val", data)
            
        data = currentNode.userData("deadline_drafttemplate")
        if data != None:
            dialog.setValue("drafttemplate.val", data)
            
        data = currentNode.userData("deadline_draftusername")
        if data != None:
            dialog.setValue("draftusername.val", data)
            
        data = currentNode.userData("deadline_draftentityname")
        if data != None:
            dialog.setValue("draftentityname.val", data)
            
        data = currentNode.userData("deadline_draftversionname")
        if data != None:
            dialog.setValue("draftversionname.val", data)
            
        data = currentNode.userData("deadline_draftadditionalargs")
        if data != None:
            dialog.setValue("draftadditionalargs.val", data)
        
    except:
        print( "Could not read submission settings from scene" )
        print( traceback.format_exc() )
        
def ReadStickySettings():
    global dialog, deadlineSettings, configFile

    try:
        if os.path.isfile( configFile ):
            config = ConfigParser.ConfigParser()
            config.read( configFile )
            print "Reading sticky settings from %s" % configFile

            if config.has_section( "Sticky" ):
                if config.has_option( "Sticky", "Department" ):
                    dialog.setValue( "department.val", config.get( "Sticky", "Department" ) )
                if config.has_option( "Sticky", "Pool" ):
                    dialog.setValue( "pool.val", config.get( "Sticky", "Pool" ) )
                if config.has_option( "Sticky", "SecondaryPool" ):
                    dialog.setValue( "secondarypool.val", config.get( "Sticky", "SecondaryPool" ) )
                if config.has_option( "Sticky", "Group" ):
                    dialog.setValue( "group.val", config.get( "Sticky", "Group" ) )
                if config.has_option( "Sticky", "Priority" ):
                    dialog.setValue( "priority.val", config.getint( "Sticky", "Priority" ) )
                if config.has_option( "Sticky", "MachineLimit" ):
                    dialog.setValue( "machinelimit.val", config.getint( "Sticky", "MachineLimit" ) )
                if config.has_option( "Sticky", "IsBlacklist" ):
                    dialog.setValue( "isblacklist.val", config.getint( "Sticky", "IsBlacklist" ) )
                if config.has_option( "Sticky", "MachineList" ):
                    dialog.setValue( "machinelist.val", config.get( "Sticky", "MachineList" ) )
                if config.has_option( "Sticky", "LimitGroups" ):
                    dialog.setValue( "limits.val", config.get( "Sticky", "LimitGroups" ) )
                if config.has_option( "Sticky", "SubmitSuspended" ):
                    dialog.setValue( "jobsuspended.val", config.getint( "Sticky", "SubmitSuspended" ) )
                if config.has_option( "Sticky", "ChunkSize" ):
                    dialog.setValue( "framespertask.val", config.getint( "Sticky", "ChunkSize" ) )
                if config.has_option( "Sticky", "ConcurrentTasks" ):
                    dialog.setValue( "concurrent.val", config.getint( "Sticky", "ConcurrentTasks" ) )
                if config.has_option( "Sticky", "LimitConcurrentTasks" ):
                    dialog.setValue( "slavelimit.val", config.getint( "Sticky", "LimitConcurrentTasks" ) )
                if config.has_option( "Sticky", "IgnoreInputs" ):
                    dialog.setValue( "ignoreinputs.val", config.getint( "Sticky", "IgnoreInputs" ) )
                if config.has_option( "Sticky", "SubmitScene" ):
                    dialog.setValue( "submitscene.val", config.getint( "Sticky", "SubmitScene" ) )
                if config.has_option( "Sticky", "SubmitMantra" ):
                    dialog.setValue( "mantrajob.val", config.getint( "Sticky", "SubmitMantra" ) )
                if config.has_option( "Sticky", "MantraThreads" ):
                    dialog.setValue( "mantrathreads.val", config.getint( "Sticky", "MantraThreads" ) )
                if config.has_option( "Sticky", "MantraPool" ):
                    dialog.setValue( "mantrapool.val", config.get( "Sticky", "MantraPool" ) )
                if config.has_option( "Sticky", "MantraSecondaryPool" ):
                    dialog.setValue( "mantrasecondarypool.val", config.get( "Sticky", "MantraSecondaryPool" ) )
                if config.has_option( "Sticky", "MantraGroup" ):
                    dialog.setValue( "mantragroup.val", config.get( "Sticky", "MantraGroup" ) )
                if config.has_option( "Sticky", "MantraPriority" ):
                    dialog.setValue( "mantrapriority.val", config.getint( "Sticky", "MantraPriority" ) )
                if config.has_option( "Sticky", "MantraMachineLimit" ):
                    dialog.setValue( "mantramachinelimit.val", config.getint( "Sticky", "MantraMachineLimit" ) )
                if config.has_option( "Sticky", "MantraIsBlacklist" ):
                    dialog.setValue( "mantraisblacklist.val", config.getint( "Sticky", "MantraIsBlacklist" ) )
                if config.has_option( "Sticky", "MantraMachineList" ):
                    dialog.setValue( "mantramachinelist.val", config.get( "Sticky", "MantraMachineList" ) )
                if config.has_option( "Sticky", "MantraLimitGroups" ):
                    dialog.setValue( "mantralimits.val", config.get( "Sticky", "MantraLimitGroups" ) )
                if config.has_option( "Sticky", "MantraConcurrentTasks" ):
                    dialog.setValue( "mantraconcurrent.val", config.getint( "Sticky", "MantraConcurrentTasks" ) )
                if config.has_option( "Sticky", "MantraLimitConcurrentTasks" ):
                    dialog.setValue( "mantraslavelimit.val", config.getint( "Sticky", "MantraLimitConcurrentTasks" ) )

                if config.has_option( "Sticky", "SubmitArnold" ):
                    dialog.setValue( "arnoldjob.val", config.getint( "Sticky", "SubmitArnold" ) )
                if config.has_option( "Sticky", "ArnoldThreads" ):
                    dialog.setValue( "arnoldthreads.val", config.getint( "Sticky", "ArnoldThreads" ) )
                if config.has_option( "Sticky", "ArnoldPool" ):
                    dialog.setValue( "arnoldpool.val", config.get( "Sticky", "ArnoldPool" ) )
                if config.has_option( "Sticky", "ArnoldSecondaryPool" ):
                    dialog.setValue( "arnoldsecondarypool.val", config.get( "Sticky", "ArnoldSecondaryPool" ) )
                if config.has_option( "Sticky", "ArnoldGroup" ):
                    dialog.setValue( "arnoldgroup.val", config.get( "Sticky", "ArnoldGroup" ) )
                if config.has_option( "Sticky", "ArnoldPriority" ):
                    dialog.setValue( "arnoldpriority.val", config.getint( "Sticky", "ArnoldPriority" ) )
                if config.has_option( "Sticky", "ArnoldMachineLimit" ):
                    dialog.setValue( "arnoldmachinelimit.val", config.getint( "Sticky", "ArnoldMachineLimit" ) )
                if config.has_option( "Sticky", "ArnoldIsBlacklist" ):
                    dialog.setValue( "arnoldisblacklist.val", config.getint( "Sticky", "ArnoldIsBlacklist" ) )
                if config.has_option( "Sticky", "ArnoldMachineList" ):
                    dialog.setValue( "arnoldmachinelist.val", config.get( "Sticky", "ArnoldMachineList" ) )
                if config.has_option( "Sticky", "ArnoldLimitGroups" ):
                    dialog.setValue( "arnoldlimits.val", config.get( "Sticky", "ArnoldLimitGroups" ) )
                if config.has_option( "Sticky", "ArnoldConcurrentTasks" ):
                    dialog.setValue( "arnoldconcurrent.val", config.getint( "Sticky", "ArnoldConcurrentTasks" ) )
                if config.has_option( "Sticky", "ArnoldLimitConcurrentTasks" ):
                    dialog.setValue( "arnoldslavelimit.val", config.getint( "Sticky", "ArnoldLimitConcurrentTasks" ) )          
                    
                if config.has_option( "Sticky", "UseDraft" ):
                    dialog.setValue( "draftsubmit.val", config.getint( "Sticky", "UseDraft" ) )
                if config.has_option( "Sticky", "DraftUpload" ):
                    dialog.setValue( "drafttoshotgun.val", config.getint( "Sticky", "DraftUpload" ) )
                if config.has_option( "Sticky", "DraftQuick"):
                    data = int( config.get( "Sticky", "DraftQuick" ) )
                    dialog.setValue( "draftQuick.val", data )
                    dialog.setValue( "draftCustom.val", int( not data ) )
                if config.has_option( "Sticky", "DraftFormat" ):
                    dialog.setValue( "draftFormat.val", config.get( "Sticky", "DraftFormat" ) )
                if config.has_option( "Sticky", "DraftCodec" ):
                    dialog.setValue( "draftCodec.val", config.get( "Sticky", "DraftCodec" ) )
                if config.has_option( "Sticky", "DraftResolution" ):
                    dialog.setValue( "draftResolution.val", config.get( "Sticky", "DraftResolution" ) )
                if config.has_option( "Sticky", "DraftQuality" ):
                    dialog.setValue( "draftQuality.val", config.get( "Sticky", "DraftQuality" ) )
                if config.has_option( "Sticky", "DraftFrameRate" ):
                    dialog.setValue( "draftFrameRate.val", config.get( "Sticky", "DraftFrameRate" ) )
                if config.has_option( "Sticky", "DraftTemplate" ):
                    dialog.setValue( "drafttemplate.val", config.get( "Sticky", "DraftTemplate" ) )
                if config.has_option( "Sticky", "DraftUser" ):
                    dialog.setValue( "draftusername.val", config.get( "Sticky", "DraftUser" ) )
                if config.has_option( "Sticky", "DraftEntity" ):
                    dialog.setValue( "draftentityname.val", config.get( "Sticky", "DraftEntity" ) )
                if config.has_option( "Sticky", "DraftVersion" ):
                    dialog.setValue( "draftversionname.val", config.get( "Sticky", "DraftVersion" ) )
                if config.has_option( "Sticky", "DraftExtraArgs" ):
                    dialog.setValue( "draftadditionalargs.val", config.get( "Sticky", "DraftExtraArgs" ) )
                if config.has_option( "Sticky", "CleanupTiles" ):
                    dialog.setValue( "cleanuptiles.val", config.get( "Sticky", "CleanupTiles" ) )
                if config.has_option( "Sticky", "ErrorOnMissingTiles" ):
                    dialog.setValue( "erroronmissingtiles.val", config.get( "Sticky", "ErrorOnMissingTiles" ) )
                if config.has_option( "Sticky", "ErroronMissingBackground" ):
                    dialog.setValue( "erroronmissingbackground.val", config.get( "Sticky", "ErroronMissingBackground" ) )
                
                
    except:
        print( "Could not read sticky settings" )
        print( traceback.format_exc() )

def InitializeDialog():
    global dialog, maxPriority, containsWedge
    global ResolutionsDict
    global FormatsDict
    global Formats 
    global Resolutions
    global CodecsDict
    global FrameRates
    
    pools = []
    secondaryPools = [" "] # empty string cannot be reselected
    groups = []
    ropList = []
    bits = ""
    startFrame = 0
    endFrame = 0
    frameStep = 1
    frameString = ""
    renderers = ""

    # Get maximum priority
    try:
        output = CallDeadlineCommand( ["-getmaximumpriority",] )
        maxPriority = int(output)
    except:
        maxPriority = 100

    # Get pools
    output = CallDeadlineCommand( ["-pools",] )
    pools = output.splitlines()
    secondaryPools.extend(pools) 

    # Get groups
    output = CallDeadlineCommand( ["-groups",] )
    groups = output.splitlines()

    # Find the "64-bitness" of the machine
    is64bit = sys.maxsize > 2**32
    if is64bit:
        bits = "64bit"
    else:
        bits = "32bit"

    # Make the file name the name of the job
    scene = hou.hipFile.name() 
    index1 = scene.rfind( "\\" )
    index2 = scene.rfind( "/" )
    
    name = ""
    if index1 > index2:
        name = scene[index1+1:len(scene)]
    else:
        name = scene[index2+1:len(scene)]

    # Fill the ROP list
    renderers = []
    
    node = hou.node( "/" )
    allNodes = node.allSubChildren()
    
    for rop in allNodes:
        if isinstance(rop, hou.RopNode):
            renderers.append(rop)
    
    #if there are no valid ROPs, exit submission script
    if len(renderers) < 1:
        hou.ui.displayMessage( "There are no valid ROPs to render.  Exiting.", title="Submit Houdini To Deadline" )
        dialog.setValue( "dlg.val", 0 )
        return False

    for rop in renderers:
        if rop.type().description() == "Wedge":
            containsWedge = True
        ropList.append( rop.path() )

    renderNode = hou.node(  ropList[0] )
    frameString = GetFrameInfo( renderNode )
    
    ReadInDraftOptions()

    #SET INITIAL GUI VALUES
    dialog.setValue( "joboptions.val", 1 )
    dialog.setValue( "jobname.val", name )
    dialog.setValue( "comment.val", "" )
    dialog.setValue( "department.val", "" )

    dialog.setMenuItems( "pool.val", pools )
    dialog.setMenuItems( "secondarypool.val", secondaryPools )
    dialog.setMenuItems( "group.val", groups )
    dialog.setValue( "priority.val", maxPriority/2 )
    dialog.setValue( "tasktimeout.val", 0 )
    dialog.setValue( "autotimeout.val", 0 )
    dialog.setValue( "concurrent.val", 1 )
    dialog.setValue( "slavelimit.val", 1 )
    dialog.setValue( "machinelimit.val", 0 )
    dialog.setValue( "machinelist.val", "" )
    dialog.setValue( "isblacklist.val", 0 )
    dialog.setValue( "limits.val", "" )
    dialog.setValue( "dependencies.val", "" )
    dialog.setMenuItems( "onjobcomplete.val", ["Nothing", "Archive", "Delete"] )
    dialog.setValue( "jobsuspended.val", 0 )

    dialog.setMenuItems( "ropoption.val", ["Choose", "Selected", "All"] )
    dialog.setMenuItems( "rop.val", ropList )
    dialog.setValue( "overrideframes.val", 0 )
    dialog.setValue( "framelist.val", frameString )
    dialog.enableValue( "framelist.val", dialog.value( "overrideframes.val" ) )
    dialog.setValue( "ignoreinputs.val", 0 )
    dialog.setValue( "submitscene.val", 0 )
    dialog.setValue( "framespertask.val", 1 )
    dialog.setMenuItems( "bits.val", ["None", "32bit", "64bit"] )
    dialog.setValue( "bits.val", bits )
    dialog.setValue( "separateWedgeJobs.val", 0 )
    dialog.setValue( "automaticDependencies.val", 1 )
    dialog.enableValue( "automaticDependencies.val", False )
    dialog.setValue( "bypassDependencies.val", 1 )
    
    enabled = 0
    if renderNode.type().description() == "Wedge":
        enabled = 1
    dialog.enableValue("separateWedgeJobs.val", enabled)
    
    dialog.setValue( "tilesenabled.val", 0 )
    jigsawVersion = False
    
    currentVersion = hou.applicationVersion()
    if currentVersion[0] >14:
        jigsawVersion = True
    elif currentVersion[0] == 14:
        if currentVersion[1] >0:
            jigsawVersion = True
        else:
            if currentVersion[2] >= 311:
                jigsawVersion = True
                
    dialog.setValue( "jigsawenabled.val",1)
    dialog.enableValue("jigsawenabled.val", jigsawVersion)
    
    dialog.setValue( "tilesinx.val", 3 )
    dialog.setValue( "tilesiny.val", 3 )
    
    dialog.setValue( "tilessingleframe.val", 1 )
    
    dialog.setValue( "tilessingleframeenabled.val", 1 )
    dialog.setValue( "submitdependentassembly.val", 1 )
    dialog.setValue( "cleanuptiles.val", 1 )
    dialog.setValue( "erroronmissingtiles.val", 1 )
    dialog.setValue( "erroronmissingbackground.val", 0 )
    dialog.setValue( "backgroundoption.val", "Blank Image" )
    dialog.setValue( "backgroundimagelabel.val", "" )
    dialog.setValue( "backgroundimage.val", "" )
        
    dialog.setValue( "mantrajob.val", 0 )
    dialog.setValue( "mantrathreads.val", 0 )
    dialog.enableValue( "mantrathreads.val", dialog.value( "mantrajob.val" ) )
    dialog.setMenuItems( "mantrapool.val", pools )
    dialog.setMenuItems( "mantrasecondarypool.val", secondaryPools )
    dialog.setMenuItems( "mantragroup.val", groups )
    dialog.setValue( "mantrapriority.val", maxPriority/2 )
    dialog.setValue( "mantratasktimeout.val", 0 )
    dialog.setValue( "mantraautotimeout.val", 0 )
    dialog.setValue( "mantraconcurrent.val", 1 )
    dialog.setValue( "mantraslavelimit.val", 1 )
    dialog.setValue( "mantramachinelimit.val", 0 )
    dialog.setValue( "mantramachinelist.val", "" )
    dialog.setValue( "mantraisblacklist.val", 0 )
    dialog.setValue( "mantralimits.val", "" )
    
    dialog.setValue( "arnoldjob.val", 0 )
    dialog.setValue( "arnoldthreads.val", 0 )
    dialog.enableValue( "arnoldthreads.val", dialog.value( "arnoldjob.val" ) )
    dialog.setMenuItems( "arnoldpool.val", pools )
    dialog.setMenuItems( "arnoldsecondarypool.val", secondaryPools )
    dialog.setMenuItems( "arnoldgroup.val", groups )
    dialog.setValue( "arnoldpriority.val", maxPriority/2 )
    dialog.setValue( "arnoldtasktimeout.val", 0 )
    dialog.setValue( "arnoldautotimeout.val", 0 )
    dialog.setValue( "arnoldconcurrent.val", 1 )
    dialog.setValue( "arnoldslavelimit.val", 1 )
    dialog.setValue( "arnoldmachinelimit.val", 0 )
    dialog.setValue( "arnoldmachinelist.val", "" )
    dialog.setValue( "arnoldisblacklist.val", 0 )
    dialog.setValue( "arnoldlimits.val", "" )
    
    dialog.setValue( "integration.val", "Shotgun")
    dialog.setValue( "sgsubmit.val", 0 )
    dialog.enableValue( "sgsubmit.val", False )
    dialog.setValue( "sgversion.val", "" )
    dialog.enableValue( "sgversion.val", dialog.value( "sgsubmit.val" ) )
    dialog.setValue( "sgdescription.val", "" )
    dialog.enableValue( "sgdescription.val", dialog.value( "sgsubmit.val" ) )
    dialog.setValue( "sgentityinfo.val", "" )
    dialog.enableValue( "sgentityinfo.val", dialog.value( "sgsubmit.val" ) )
    dialog.enableValue( "sgentitylabel.val", dialog.value( "sgsubmit.val" ) )
    dialog.setValue( "sguploadmovie.val", dialog.value( "sgsubmit.val" ) )
    dialog.enableValue( "sguploadmovie.val", dialog.value( "sgsubmit.val" ) )
    dialog.setValue( "sguploadfilm.val", dialog.value( "sgsubmit.val" ) )
    dialog.enableValue( "sguploadfilm.val", dialog.value( "sgsubmit.val" ) )

    dialog.setValue( "draftsubmit.val", 0 )
    dialog.setValue( "drafttoshotgun.val", 0 )
    dialog.enableValue( "drafttoshotgun.val", dialog.value( "draftsubmit.val" ) and dialog.value( "sgsubmit.val" ) )
    dialog.setValue( "draftQuick.val", 1 )
    dialog.enableValue("draftQuick.val", dialog.value( "draftsubmit.val") )
    dialog.setMenuItems( "draftFormat.val", Formats )
    dialog.enableValue( "draftFormat.val", dialog.value( "draftsubmit.val") and dialog.value( "draftQuick.val") )
    selectedFormat = FormatsDict[dialog.value("draftFormat.val")][0]
    dialog.setMenuItems( "draftCodec.val", CodecsDict[selectedFormat] )
    dialog.enableValue( "draftCodec.val", False )
    dialog.setMenuItems( "draftResolution.val", Resolutions )
    dialog.enableValue( "draftResolution.val", dialog.value( "draftsubmit.val") and dialog.value( "draftQuick.val") )
    dialog.setValue( "draftQuality.val", 85 )
    dialog.enableValue( "draftQuality.val", dialog.value( "draftsubmit.val") and dialog.value( "draftQuick.val") )
    dialog.setMenuItems( "draftFrameRate.val", FrameRates )
    if '24' in FrameRates:
        dialog.setValue( "draftFrameRate.val", 24 )
    dialog.enableValue( "draftFrameRate.val", False )
    dialog.setValue( "drafttemplate.val", "" )
    dialog.enableValue( "drafttemplate.val", dialog.value( "draftsubmit.val" ) )
    dialog.enableValue( "drafttemplatelabel.val", dialog.value( "draftsubmit.val" ) )
    dialog.setValue( "draftusername.val", "" )
    dialog.enableValue( "draftusername.val", dialog.value( "draftsubmit.val" ) )
    dialog.setValue( "draftentityname.val", "" )
    dialog.enableValue( "draftentityname.val", dialog.value( "draftsubmit.val" ) )
    dialog.setValue( "draftversionname.val", "" )
    dialog.enableValue( "draftversionname.val", dialog.value( "draftsubmit.val" ) )
    dialog.setValue( "draftadditionalargs.val", "" )
    dialog.enableValue( "draftadditionalargs.val", dialog.value( "draftsubmit.val" ) )
    dialog.enableValue( "draftshotgundata.val", dialog.value( "draftsubmit.val" ) and dialog.value( "sgsubmit.val" ) and dialog.value( "draftCustom.val" ) )
    
    LoadIntegrationSettings()
    updateDisplay()
    dialog.setValue( "sgsubmit.val", False )
        
    return True
    
def SetOptions(type, options):

    global dialog

    draftBox = "draft"+str(type)+".val"
        
    selection = dialog.value(draftBox)
    dialog.setMenuItems(draftBox, options)
    
    if selection in options:
        dialog.setValue(draftBox, selection)
    elif type == "FrameRate":
        items = dialog.menuItems(draftBox)
        if '24' in items:
            dialog.setValue(draftBox, 24)
    # else:
        # if draftBox.numValues() > 0:
            # value = draftBox.values()[0]
            # draftBox.setValue(value)
        
    
def GetOptions( selection, selectionType, validOptions):
    global RestrictionsDict
    
    if selection in RestrictionsDict:
        if selectionType in RestrictionsDict[selection]:
            restrictedOptions = RestrictionsDict[selection][selectionType]
            validOptions = set( validOptions ).intersection( restrictedOptions )
    return list(validOptions)
    
def AdjustCodecs( *args ):
    global dialog
    global CodecsDict
    global FormatsDict
    global Restrictions
    global FrameRates
    
    selectedFormat = FormatsDict[dialog.value("draftFormat.val")][0]
    validOptions = CodecsDict[selectedFormat]
    validOptions = GetOptions( selectedFormat, "Codec", validOptions )
    
    SetOptions( "Codec", validOptions )
    
    # # Adjust the drop down for codecs. If possible, keep previous codec selection.
    # selectedCodec = dialog.value( "draftCodec.val" )
    # dialog.setMenuItems( "draftCodec.val", validCodecs )
    # if( selectedCodec in validCodecs ):
        # dialog.setValue( "draftCodec.val", selectedCodec )

def AdjustFrameRates( *args ):
    global dialog
    global FormatsDict
    global Restrictions
    global FrameRates
    
    validOptions = FrameRates
        
    selectedFormat = FormatsDict[dialog.value("draftFormat.val")][0]
    validOptions = GetOptions( selectedFormat, "FrameRate", validOptions )
        
    selectedCodec = dialog.value("draftCodec.val")
    validOptions = GetOptions( selectedCodec, "FrameRate", validOptions )
        
    SetOptions("FrameRate", validOptions)

def AdjustQuality():
    global dialog
    draftEnabled = dialog.value( "draftsubmit.val" )
    draftQuickEnabled = dialog.value( "draftQuick.val" )
    selectedFormat = FormatsDict[dialog.value("draftFormat.val")][0]
    selectedCodec = dialog.value("draftCodec.val")
    draftQualityEnabled = ValidQuality( selectedFormat, selectedCodec, "EnableQuality" )

    dialog.enableValue( "draftQuality.val", 1 if (draftEnabled and draftQuickEnabled and draftQualityEnabled) else 0 )

def ValidQuality( selectedFormat, selectedCodec, enableQuality ):
    global RestrictionsDict
    if selectedFormat in RestrictionsDict:
        if enableQuality in RestrictionsDict[selectedFormat]:
            validQualityCodecs = RestrictionsDict[selectedFormat][enableQuality]
            if selectedCodec in (codec.lower() for codec in validQualityCodecs):
                return True
    return False

def ReadInDraftOptions():
    global Formats 
    global Resolutions
    global FrameRates
    global Restrictions
    global scriptRoot
    
    # Read in configuration files for Draft drop downs
    mainDraftFolder = os.path.join( scriptRoot, "submission", "Draft", "Main" )
    Formats = ReadInFormatsFile( os.path.join( mainDraftFolder, "formats.txt" ) )
    Resolutions = ReadInResolutionsFile( os.path.join( mainDraftFolder, "resolutions.txt" ) )
    ReadInCodecsFile( os.path.join( mainDraftFolder, "codecs.txt" ) )
    FrameRates = ReadInFile( os.path.join( mainDraftFolder, "frameRates.txt" ) )

    Restrictions = ReadInRestrictionsFile( os.path.join( mainDraftFolder, "restrictions.txt" ) )
    
def ReadInFormatsFile( filename ):
    global FormatsDict
    results = []
    try:
        for line in open( filename ):
            words = line.split(',')
            name = words[1].strip() + " (" + words[0].strip() + ")"
            results.append( name )
            FormatsDict[name] = [words[0].strip(), words[2].strip()]
        results = filter( None, results )
    except:
        errorMsg = "Failed to read in configuration file " + filename + "."
        print errorMsg
        raise Exception(errorMsg)
    return results

def ReadInResolutionsFile( filename ):
    global ResolutionsDict
    results = []
    try:
        for line in open( filename ):
            words = line.split(',')
            name = words[1].strip() 
            results.append( name )
            ResolutionsDict[name] = words[0].strip()
        results = filter( None, results )
    except:
        errorMsg = "Failed to read in configuration file " + filename + "."
        print errorMsg
        raise Exception(errorMsg)
    return results

def ReadInFile( filename ):
    try:
        results = filter( None, [line.strip() for line in open( filename )] )
    except: 
        errorMsg = "Failed to read in configuration file " + filename + "."
        print errorMsg
        raise Exception(errorMsg)
    return results

def ReadInCodecsFile( filename ):
    global CodecsDict
    try:
        for line in open( filename ):
            words = line.split( ':' )
            name = words[0].strip()
            codecList = map( str.strip, words[1].split( "," ) )
            if not name in CodecsDict:
                CodecsDict[name] = {}

            CodecsDict[name] = codecList

    except:
        errorMsg = "Failed to read in configuration file " + filename + "."
        print errorMsg
        raise Exception( errorMsg )

def ReadInRestrictionsFile( filename ):
    global RestrictionsDict
    results = []
    try:
        for line in open( filename ):
            words = line.split( ':' )
            name = words[0].strip()
            restriction = words[1].split( '=' )
            restrictionType = restriction[0].strip()
            restrictionList = map( str.strip, restriction[1].split( "," ) )
            if not name in RestrictionsDict:
                results.append( name )
                RestrictionsDict[name] = {}
                RestrictionsDict[name][restrictionType] = restrictionList
                #RestrictionsDict[name] = [[restrictionType, restrictionList]]
            else:
                RestrictionsDict[name][restrictionType] = restrictionList
                #RestrictionsDict[name].append([restrictionType, restrictionList])
        results = filter( None, results )
    except:
        errorMsg = "Failed to read in configuration file " + filename + "."
        print errorMsg
        raise Exception( errorMsg )
    return results

def IsMovieFromFormat( format ):
    return ( FormatsDict[format][1] == 'movie' )

def Callbacks():
    dialog.addCallback( "getmachinelist.val", GetMachineListFromDeadline )
    dialog.addCallback( "getlimits.val", GetLimitGroupsFromDeadline )
    dialog.addCallback( "getdependencies.val", GetDependenciesFromDeadline )

    dialog.addCallback( "priority.val", JobPriorityCallback )
    dialog.addCallback( "tasktimeout.val", TaskTimeoutCallback )
    dialog.addCallback( "concurrent.val", ConcurrentTasksCallback )
    dialog.addCallback( "machinelimit.val", MachineLimitCallback )

    dialog.addCallback( "ropoption.val", ROPOptionCallback )
    dialog.addCallback( "rop.val", ROPSelectionCallback )
    dialog.addCallback( "overrideframes.val", FramesCallback )
    dialog.addCallback( "framespertask.val", FramesPerTaskCallback )

    dialog.addCallback( "mantrajob.val", MantraStandaloneCallback )
    dialog.addCallback( "mantrathreads.val", MantraThreadsCallback )

    dialog.addCallback( "mantragetmachinelist.val", MantraGetMachineListFromDeadline )
    dialog.addCallback( "mantragetlimits.val", MantraGetLimitGroupsFromDeadline )

    dialog.addCallback( "mantrapriority.val", MantraJobPriorityCallback )
    dialog.addCallback( "mantratasktimeout.val", MantraTaskTimeoutCallback )
    dialog.addCallback( "mantraconcurrent.val", MantraConcurrentTasksCallback )
    dialog.addCallback( "mantramachinelimit.val", MantraMachineLimitCallback )
    
    dialog.addCallback( "arnoldjob.val", ArnoldStandaloneCallback )
    dialog.addCallback( "arnoldthreads.val", ArnoldThreadsCallback )
    dialog.addCallback( "arnoldgetmachinelist.val", ArnoldGetMachineListFromDeadline )
    dialog.addCallback( "arnoldgetlimits.val", ArnoldGetLimitGroupsFromDeadline )
    dialog.addCallback( "arnoldpriority.val", ArnoldJobPriorityCallback )
    dialog.addCallback( "arnoldtasktimeout.val", ArnoldTaskTimeoutCallback )
    dialog.addCallback( "arnoldconcurrent.val", ArnoldConcurrentTasksCallback )
    dialog.addCallback( "arnoldmachinelimit.val", ArnoldMachineLimitCallback )
    
    dialog.addCallback( "tilesenabled.val", TilesEnabledCallback )
    dialog.addCallback( "jigsawenabled.val", JigsawEnabledCallback )
    dialog.addCallback( "tilessingleframeenabled.val", TilesSingleFrameEnabledCallback )
    dialog.addCallback( "submitdependentassembly.val", SubmitDependentAssemblyCallback )
    dialog.addCallback( "backgroundoption.val", BackgroundOptionCallback)
    
    dialog.addCallback( "openjigsaw.val", OpenJigsaw)
    
    dialog.addCallback( "sgconnect.val", ShotgunConnectCallback )
    dialog.addCallback( "sgsubmit.val", ShotgunSubmitCallback )
    dialog.addCallback( "draftsubmit.val", DraftSubmitCallback )
    dialog.addCallback( "draftFormat.val", DraftSubmitCallback )
    dialog.addCallback( "draftFormat.val", AdjustCodecs )
    dialog.addCallback( "draftFormat.val", AdjustFrameRates )
    dialog.addCallback( "draftCodec.val", AdjustQuality )
    dialog.addCallback( "draftCodec.val", AdjustFrameRates )
    dialog.addCallback( "draftQuick.val", QuickToggled )
    dialog.addCallback( "draftCustom.val", CustomToggled )
    dialog.addCallback( "draftshotgundata.val", DraftShotgunDataCallback )

    dialog.addCallback( "submitjob.val", SubmitJobCallback )
    dialog.addCallback( "closedialog.val", CloseDialogCallback )
    
    dialog.addCallback( "integration.val", updateDisplay ) 
    
def QuickToggled():
    global dialog
    
    customValue = dialog.value("draftCustom.val")
    quickValue = dialog.value("draftQuick.val")
    
    dialog.removeCallback("draftCustom.val", CustomToggled)
    dialog.setValue("draftCustom.val", not quickValue )
    dialog.addCallback("draftCustom.val", CustomToggled)
       
    DraftSubmitCallback()
    
def CustomToggled():
    global dialog
    
    customValue = dialog.value("draftCustom.val")
    quickValue = dialog.value("draftQuick.val")
    
    dialog.removeCallback("draftQuick.val", QuickToggled)
    dialog.setValue("draftQuick.val", not customValue )
    dialog.addCallback("draftQuick.val", QuickToggled)
        
    DraftSubmitCallback()

def GetOutputPath( node ):
    outputFile = ""
    type = node.type().description()
    
    #Figure out which type of node is being rendered
    if type == "Geometry" or type == "ROP Output Driver":
        outputFile = node.parm( "sopoutput" )
    elif type == "Composite":
        outputFile = node.parm( "copoutput" )
    elif type == "Channel":
        outputFile = node.parm( "chopoutput" )
    elif type == "OpenGL":
        outputFile = node.parm( "picture" )
    elif type == "Dynamics":
        outputFile = node.parm( "dopoutput" )
    elif type == "Alfred":
        outputFile = node.parm( "alf_diskfile")
    elif type == "RenderMan":
        #if not node.parm( "soho_diskfile" ).isDisabled(): #node.parm( "rib_outputmode" ) and not node.parm( "rib_outputmode" ).isDisabled():    
        #    outputFile = node.parm( "soho_diskfile" )
        #else:
        #    outputFile = node.parm( "ri_display" )
        outputFile = node.parm( "ri_display" )
    elif type == "Mantra":
        #if not node.parm( "soho_diskfile" ).isDisabled(): #node.parm( "soho_outputmode" ) and not node.parm( "soho_outputmode" ).isDisabled():
        #    outputFile = node.parm( "soho_diskfile" )
        #else:
        #    outputFile = node.parm( "vm_picture" )
        outputFile = node.parm( "vm_picture" )
    elif type == "Wedge":
        driverNode = hou.node( node.parm("driver").eval() )
        outputFile = GetOutputPath(driverNode)
    elif type == "Arnold":
        outputFile = node.parm("ar_picture")
    elif type == "HQueue Simulation":
        innerNode = hou.node(node.parm("hq_driver").eval())
        outputFile = GetOutputPath( innerNode )
    elif type == "ROP Alembic Output":
        outputFile = node.parm( "filename" )
        
    #Check if outputFile could "potentially" be valid. ie. Doesn't allow Houdini's "ip"
    # or "md" values to be overridden, but silliness like " /*(xc*^zx$*asdf " would be "valid")
    if outputFile != "" and not os.path.isabs( outputFile.eval() ):
        outputFile = "COMMAND"

    return outputFile

def GetIFD( node ):
    ifdFile = None
    type = node.type().description()

    if type == "Mantra" and node.parm( "soho_outputmode" ).eval():
        ifdFile = node.parm( "soho_diskfile" )
    elif type == "Alfred":
        ifdFile = node.parm( "alf_diskfile")
    elif type == "RenderMan" and node.parm( "rib_outputmode" ) and node.parm( "rib_outputmode" ).eval():
        ifdFile = node.parm( "soho_diskfile" )
    elif type == "Wedge" and node.parm("driver").eval():
        ifdFile = GetIFD( hou.node(node.parm("driver").eval()) )
    elif type == "Arnold":
        ifdFile = node.parm( "ar_ass_file" )
    return ifdFile

def RightReplace( fullString, oldString, newString, occurences ):
    return newString.join( fullString.rsplit( oldString, occurences ) )

def WedgeTasks(wedgeNode):
    global dialog
    
    numTasks = 1
    
    if wedgeNode.type().description() == "Wedge":
        numParams = wedgeNode.parm("wedgeparams").eval()
        random = wedgeNode.parm("random").eval()
        
        if random:
            #We're using the random settings
            numRandom = wedgeNode.parm("numrandom").eval()
            numTasks = numRandom * numParams
            
        else:
            #Using the number wedge params to determine task count
            for i in range(1, numParams+1):
                numTasks = numTasks * wedgeNode.parm("steps"+str(i)).eval()
                
    return numTasks
    
def GetFrameInfo( renderNode ):
    startFrame = 0
    endFrame = 0
    frameStep = 1
    frameString = ""
    
    if renderNode.type().description() == "Wedge":
        if renderNode.parm("driver").eval():
            return GetFrameInfo(hou.node(renderNode.parm("driver").eval()))
        # numTasks = WedgeTasks(renderNode)
        
        # startFrame = 0
        # endFrame = numTasks - 1
        # frameStep = 1
    # else:
    startFrameParm = renderNode.parm( "f1" )
    if startFrameParm != None:
        startFrame = int(startFrameParm.eval())
        
    endFrameParm = renderNode.parm( "f2" )
    if endFrameParm != None:
        endFrame = int(endFrameParm.eval())
        
    frameStepParm = renderNode.parm( "f3" )
    if frameStepParm != None:
        frameStep = int(frameStepParm.eval())

    frameString = str(startFrame) + "-" + str(endFrame)
    if frameStep > 1:
        frameString = frameString + "x" + str(frameStep)

    return frameString

def GetROPsFromMergeROP( mergeROP, bypass = False ):
    rops = []
    
    # Double check that this is a merge node.
    if mergeROP.type().description() == "Merge":
        # Loop through all inputs to get the actual nodes.
        for inputROP in mergeROP.inputs():
            # If the input ROP is a merge node, do some recursion!
            if inputROP.type().description() == "Merge":
                for nestedInputROP in GetROPsFromMergeROP( inputROP, bypass ):
                    # We don't want duplicate ROPs.
                    if nestedInputROP not in rops:
                        rops.append( nestedInputROP )
            else:
                # Ignore bypassed ROPs.
                if not bypass or not inputROP.isBypassed():
                    # We don't want duplicate ROPs.
                    if inputROP not in rops:
                        rops.append( inputROP )
            
    return rops
    

def GetROPs( ropOption, bypass = False ):
    jobs = []
    renderNode = hou.node( "/" )
    renderers =[]
    for rop in renderNode.allSubChildren():
        #for rop in allNodes:
        if isinstance(rop, hou.RopNode):
            renderers.append(rop)
    
    if ropOption == "Selected" and len(renderers) > 0 and len(hou.selectedNodes()) > 0: # A node is selected
        for selectedNodes in hou.selectedNodes():
            if not bypass or not selectedNodes.isBypassed():
                for rop in renderers:
                    if rop.path() == selectedNodes.path():

                        if rop.type().description() =="Fetch":
                            nodeText=rop.parm("source").eval()
                            nodeSim=hou.node(nodeText)
                            if nodeSim.path() not in jobs:
                                jobs.append(nodeSim.path())
                        
                        # If this is a merge ROP, we want its input ROPs.
                        if rop.type().description() == "Merge":
                            for inputROP in GetROPsFromMergeROP( rop, bypass ):

                                if inputROP.type().description() =="Fetch":
                                    print "es fetch"
                                    nodeText=inputROP.parm("source").eval()
                                    nodeSim=hou.node(nodeText)
                                    if nodeSim.path() not in jobs:
                                        jobs.append(nodeSim.path())

                                if inputROP.path() not in jobs and inputROP.type().description() !="Fetch":
                                    jobs.append( inputROP.path() )
                        else:
                            if selectedNodes.path() not in jobs:
                                jobs.append( selectedNodes.path() )
                        break

        if jobs == []: # No valid selected Nodes
            print "Selected node(s) are invalid"
            return
        
    elif ropOption == "All" and len(renderers) > 0:
        for node in renderers:
            # Simply skip over any merge nodes.
            if node.type().description() == "Merge":
                continue
            
            if not bypass or not node.isBypassed():
                jobs.append( node.path() )

    return jobs

def IsPathLocal( path ):
    lowerPath = path.lower()
    return lowerPath.startswith( "c:" ) or lowerPath.startswith( "d:" ) or lowerPath.startswith( "e:" )

def GetSettingsFilename():
    return os.path.join( deadlineSettings, "houdiniSettings.ini" )

def GetShotgunSettingsFilename():
    return os.path.join( deadlineSettings, "HoudiniSettingsShotgun.ini" )

def GetFTrackSettingsFilename():
    return os.path.join( deadlineSettings, "HoudiniSettingsFTrack.ini" )
        
def GetMachineListFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectmachinelist", dialog.value("machinelist.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "machinelist.val", output )

def GetLimitGroupsFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectlimitgroups", dialog.value("limits.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "limits.val", output )

def GetDependenciesFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectdependencies", dialog.value("dependencies.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "dependencies.val", output )

def JobPriorityCallback():
    global dialog, maxPriority
    
    priority = dialog.value( "priority.val" )
    if priority > maxPriority:
        dialog.setValue( "priority.val", maxPriority )
    elif priority < 0:
        dialog.setValue( "priority.val", 0 )

def TaskTimeoutCallback():
    global dialog

    taskTimeout = dialog.value( "tasktimeout.val" )
    if taskTimeout > 1000000:
        dialog.setValue( "tasktimeout.val", 1000000 )
    elif taskTimeout < 0:
        dialog.setValue( "tasktimeout.val", 0 )

def ConcurrentTasksCallback():
    global dialog

    concurrentTasks = dialog.value( "concurrent.val" )
    if concurrentTasks > 16:
        dialog.setValue( "concurrent.val", 16 )
    elif concurrentTasks < 1:
        dialog.setValue( "concurrent.val", 1 )

def MachineLimitCallback():
    global dialog

    machineLimit = dialog.value( "machinelimit.val" )
    if machineLimit > 1000000:
        dialog.setValue( "machinelimit.val", 1000000 )
    elif machineLimit < 0:
        dialog.setValue( "machinelimit.val", 0 )

def ROPOptionCallback():
    global dialog, containsWedge

    ropOption = dialog.value( "ropoption.val" )
    dialog.enableValue( "rop.val", ropOption == "Choose" )
    
    dialog.enableValue( "automaticDependencies.val", ropOption != "Choose" )
    
    value = 0
    if containsWedge:
        value = 1
    if ropOption == "All":
        dialog.enableValue("separateWedgeJobs.val", value)
    else:
        ROPSelectionCallback()

def ROPSelectionCallback():
    global dialog
    frameString = ""

    ropSelection = dialog.value( "rop.val" )
    renderNode = hou.node( ropSelection )
    
    frameString = GetFrameInfo( renderNode )
    dialog.setValue( "framelist.val", frameString )
    
    if renderNode.type().description() == "Wedge":
        #dialog.setValue( "framespertask.val", 1 )
        dialog.enableValue("separateWedgeJobs.val", 1)
    else:
        dialog.enableValue("separateWedgeJobs.val", 0)

def FramesCallback():
    global dialog

    isOverrideFrames = dialog.value( "overrideframes.val" )
    dialog.enableValue( "framelist.val", isOverrideFrames )
    

def FramesPerTaskCallback():
    global dialog

    framesPerTask = dialog.value( "framespertask.val" )
    if framesPerTask > 1000000:
        dialog.setValue( "framespertask.val", 1000000 )
    elif framesPerTask < 1:
        dialog.setValue( "framespertask.val", 1 )

def MantraStandaloneCallback():
    global dialog

    isMantraJob = dialog.value( "mantrajob.val" )
    dialog.enableValue( "mantrathreads.val", isMantraJob )

def MantraThreadsCallback():
    global dialog

    mantraThreads = dialog.value( "mantrathreads.val" )
    if mantraThreads > 256:
        dialog.setValue( "mantrathreads.val", 256 )
    elif mantraThreads < 0:
        dialog.setValue( "mantrathreads.val", 0 )

def MantraGetMachineListFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectmachinelist", dialog.value("mantramachinelist.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "mantramachinelist.val", output )

def MantraGetLimitGroupsFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectlimitgroups", dialog.value("mantralimits.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "mantralimits.val", output )

def MantraGetDependenciesFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectdependencies", dialog.value("mantradependencies.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "mantradependencies.val", output )

def MantraJobPriorityCallback():
    global dialog, maxPriority
    
    priority = dialog.value( "mantrapriority.val" )
    if priority > maxPriority:
        dialog.setValue( "mantrapriority.val", maxPriority )
    elif priority < 0:
        dialog.setValue( "mantrapriority.val", 0 )

def MantraTaskTimeoutCallback():
    global dialog

    taskTimeout = dialog.value( "mantratasktimeout.val" )
    if taskTimeout > 1000000:
        dialog.setValue( "mantratasktimeout.val", 1000000 )
    elif taskTimeout < 0:
        dialog.setValue( "mantratasktimeout.val", 0 )

def MantraConcurrentTasksCallback():
    global dialog

    concurrentTasks = dialog.value( "mantraconcurrent.val" )
    if concurrentTasks > 16:
        dialog.setValue( "mantraconcurrent.val", 16 )
    elif concurrentTasks < 1:
        dialog.setValue( "mantraconcurrent.val", 1 )

def MantraMachineLimitCallback():
    global dialog

    machineLimit = dialog.value( "mantramachinelimit.val" )
    if machineLimit > 1000000:
        dialog.setValue( "mantramachinelimit.val", 1000000 )
    elif machineLimit < 0:
        dialog.setValue( "mantramachinelimit.val", 0 )

def ArnoldStandaloneCallback():
    global dialog

    isArnoldJob = dialog.value( "arnoldjob.val" )
    dialog.enableValue( "arnoldthreads.val", isArnoldJob )

def ArnoldThreadsCallback():
    global dialog

    arnoldThreads = dialog.value( "arnoldthreads.val" )
    if arnoldThreads > 256:
        dialog.setValue( "arnoldthreads.val", 256 )
    elif arnoldThreads < 0:
        dialog.setValue( "arnoldthreads.val", 0 )

def ArnoldGetMachineListFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectmachinelist", dialog.value("arnoldmachinelist.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "arnoldmachinelist.val", output )

def ArnoldGetLimitGroupsFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectlimitgroups", dialog.value("arnoldlimits.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "arnoldlimits.val", output )

def ArnoldGetDependenciesFromDeadline():
    global dialog

    output = CallDeadlineCommand( ["-selectdependencies", dialog.value("arnolddependencies.val")] )
    output = output.replace( "\r", "" ).replace( "\n", "" )
    if output != "Action was cancelled by user":
        dialog.setValue( "arnolddependencies.val", output )

def ArnoldJobPriorityCallback():
    global dialog, maxPriority
    
    priority = dialog.value( "arnoldpriority.val" )
    if priority > maxPriority:
        dialog.setValue( "arnoldpriority.val", maxPriority )
    elif priority < 0:
        dialog.setValue( "arnoldpriority.val", 0 )

def ArnoldTaskTimeoutCallback():
    global dialog

    taskTimeout = dialog.value( "arnoldtasktimeout.val" )
    if taskTimeout > 1000000:
        dialog.setValue( "arnoldtasktimeout.val", 1000000 )
    elif taskTimeout < 0:
        dialog.setValue( "arnoldtasktimeout.val", 0 )

def ArnoldConcurrentTasksCallback():
    global dialog

    concurrentTasks = dialog.value( "arnoldconcurrent.val" )
    if concurrentTasks > 16:
        dialog.setValue( "arnoldconcurrent.val", 16 )
    elif concurrentTasks < 1:
        dialog.setValue( "arnoldconcurrent.val", 1 )

def ArnoldMachineLimitCallback():
    global dialog

    machineLimit = dialog.value( "arnoldmachinelimit.val" )
    if machineLimit > 1000000:
        dialog.setValue( "arnoldmachinelimit.val", 1000000 )
    elif machineLimit < 0:
        dialog.setValue( "arnoldmachinelimit.val", 0 )
    
def TilesEnabledCallback():
    global dialog
    
    jigsawVersion = False
    currentVersion = hou.applicationVersion()
    if currentVersion[0] >14:
        jigsawVersion = True
    elif currentVersion[0] == 14:
        if currentVersion[1] >0:
            jigsawVersion = True
        else:
            if currentVersion[2] >= 311:
                jigsawVersion = True
                
    tilesEnabled = (dialog.value( "tilesenabled.val" ) == 1)
    
    dialog.enableValue( "jigsawenabled.val", tilesEnabled and jigsawVersion )
    
    dialog.enableValue( "tilessingleframeenabled.val", tilesEnabled )    
    dialog.enableValue( "submitdependentassembly.val", tilesEnabled ) 
    JigsawEnabledCallback()
    TilesSingleFrameEnabledCallback()
    SubmitDependentAssemblyCallback()
    
def JigsawEnabledCallback():
    global dialog
    jigsawVersion = False
    currentVersion = hou.applicationVersion()
    if currentVersion[0] >14:
        jigsawVersion = True
    elif currentVersion[0] == 14:
        if currentVersion[1] >0:
            jigsawVersion = True
        else:
            if currentVersion[2] >= 311:
                jigsawVersion = True
    
    jigsawEnabled = (dialog.value( "jigsawenabled.val" ) == 1) and jigsawVersion
    tilesEnabled = (dialog.value( "tilesenabled.val" ) == 1)
    
    dialog.enableValue( "tilesinx.val", tilesEnabled and not jigsawEnabled )   
    dialog.enableValue( "tilesiny.val", tilesEnabled and not jigsawEnabled )   
    
    dialog.enableValue( "openjigsaw.val", tilesEnabled and jigsawEnabled ) 

def TilesSingleFrameEnabledCallback():
    global dialog
    
    tilesEnabled = (dialog.value( "tilesenabled.val" ) == 1)
    tilesSingleFrameEnabled = (dialog.value( "tilessingleframeenabled.val" ) == 1 )
    dialog.enableValue("tilessingleframe.val", tilesEnabled and tilesSingleFrameEnabled)
    
def SubmitDependentAssemblyCallback():
    global dialog
    tilesEnabled = (dialog.value( "tilesenabled.val" ) == 1)
    submitDependent = (dialog.value( "submitdependentassembly.val") == 1)
    
    dialog.enableValue("cleanuptiles.val", tilesEnabled and submitDependent)
    dialog.enableValue("erroronmissingtiles.val", tilesEnabled and submitDependent)
    dialog.enableValue("erroronmissingbackground.val", tilesEnabled and submitDependent)
    dialog.enableValue("backgroundoption.val", tilesEnabled and submitDependent)
    BackgroundOptionCallback()
    
def BackgroundOptionCallback():
    global dialog
    tilesEnabled = (dialog.value( "tilesenabled.val" ) == 1)
    submitDependent = (dialog.value( "submitdependentassembly.val") == 1)
    backgroundType = dialog.value("backgroundoption.val")
    if backgroundType == "Selected Image":
        dialog.enableValue("backgroundimagelabel.val", tilesEnabled and submitDependent)
        dialog.enableValue("backgroundimage.val", tilesEnabled and submitDependent)
    else:
        dialog.enableValue("backgroundimagelabel.val", False)
        dialog.enableValue("backgroundimage.val", False)

def OpenJigsaw():
    global dialog
    global jigsawThread
    
    driver = dialog.value("rop.val")
    rop = hou.node( driver )
    camera = rop.parm( "camera" ).eval()
    cameraNode = hou.node(camera)
    if not cameraNode:
        hou.ui.displayMessage( "The selected Driver doesn't have a camera.", title="Submit Houdini To Deadline" )
        return
    
    if jigsawThread is not None:
        if jigsawThread.isAlive():        
            hou.ui.displayMessage( "The Jigsaw window is currently open.", title="Submit Houdini To Deadline" )
            return
    
    jigsawThread  = JigsawThread(name="JigsawThread")
    jigsawThread.driver = driver
    jigsawThread.start()
    
def ShotgunConnectCallback():
    global dialog
    global scriptDialog
   
    script = ""
    settingsName = ""
    usingShotgun = (dialog.value("integration.val") == "Shotgun")
    
    root = CallDeadlineCommand(["-getrepositoryroot"])
    additionalArgs = []
    if usingShotgun:
        script = shotgunScript
        settingsName = GetShotgunSettingsFilename()
        additionalArgs = BuildShotgunArgs()
    else:
        script = ftrackScript
        settingsName = GetFTrackSettingsFilename()
        additionalArgs = BuildFTrackArgs()
        
    args = ["-ExecuteScript", script, "Houdini"]
    for arg in additionalArgs:
        args.append(arg)
        
    output = CallDeadlineCommand( args, False ) # todo: if true, it crashes :)
    updated = ProcessLines( output.splitlines(), usingShotgun )
    if updated:
        updateDisplay()
        sgSettingsFile = open(settingsName, 'w+')
        sgSettingsFile.write( output ) #write all lines to file
        sgSettingsFile.close()
        
def BuildShotgunArgs():
    global shotgunSettings
    
    additionalArgs = []
    
    if 'VersionName' in shotgunSettings:
        versionValue = str(shotgunSettings.get( 'VersionName', "" ))
        if len(versionValue) > 0 and versionValue != "":
            additionalArgs.append("VersionName="+str(versionValue))
    
    if 'UserName' in shotgunSettings:
        userName = str(shotgunSettings[ 'UserName' ])
        if len(userName) > 0 and userName != "":
            additionalArgs.append("UserName="+str(userName))
            
    if 'TaskName' in shotgunSettings:
        taskName = str(shotgunSettings[ 'TaskName' ])
        if len(taskName) > 0 and taskName != "":
            additionalArgs.append("TaskName="+str(taskName))

    if 'ProjectName' in shotgunSettings:
        projectName = str(shotgunSettings[ 'ProjectName' ])
        if len(projectName) > 0 and projectName != "":
            additionalArgs.append("ProjectName="+str(projectName))

    if 'EntityName' in shotgunSettings:
        entityName = str(shotgunSettings[ 'EntityName' ])
        if len(entityName) > 0 and entityName != "":
            additionalArgs.append("EntityName="+str(entityName))

    if 'EntityType' in shotgunSettings:
        entityType = str(shotgunSettings[ 'EntityType' ])
        if len(entityType) > 0 and entityType != "":
            additionalArgs.append("EntityType="+str(entityType))
            
    return additionalArgs
    
def BuildFTrackArgs():
    global fTrackSettings
    global pulledFTrackSettings
    settings = pulledFTrackSettings
    if len(pulledFTrackSettings) == 0:
        settings = fTrackSettings
    additionalArgs = []
    
    if 'FT_Username' in settings:
        userName = str(settings[ 'FT_Username' ])
        if len(userName) > 0 and userName != "":
            additionalArgs.append("UserName="+str(userName))
            
    if 'FT_TaskName' in settings:
        taskName = str(settings[ 'FT_TaskName' ])
        if len(taskName) > 0 and taskName != "":
            additionalArgs.append("TaskName="+str(taskName))

    if 'FT_ProjectName' in settings:
        projectName = str(settings[ 'FT_ProjectName' ])
        if len(projectName) > 0 and projectName != "":
            additionalArgs.append("ProjectName="+str(projectName))

    if 'FT_AssetName' in settings:
        assetName = str(settings[ 'FT_AssetName' ])
        if len(assetName) > 0 and assetName != "":
            additionalArgs.append("AssetName="+str(assetName))
            
    return additionalArgs

def ProcessLines( lines, shotgun ):
    global shotgunSettings
    global fTrackSettings
    global pulledFTrackSettings
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
            pulledFTrackSettings = {}
            fTrackSettings = tempKVPs
        return True
    return False
                           
def updateDisplay():
    global fTrackSettings
    global shotgunSettings
    
    displayText = ""
    usingShotgun = (dialog.value("integration.val") == "Shotgun")
    if usingShotgun:
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
    
        dialog.setValue("sgentityinfo.val",displayText)
        dialog.setValue("sgversion.val",shotgunSettings.get( 'VersionName', "" ))
        dialog.setValue("sgdescription.val",shotgunSettings.get( 'Description', "" ))
        
    else:    
        if 'FT_Username' in fTrackSettings:
            displayText += "User Name: %s\n" % fTrackSettings[ 'FT_Username' ]
        if 'FT_TaskName' in fTrackSettings:
            displayText += "Task Name: %s\n" % fTrackSettings[ 'FT_TaskName' ]
        if 'FT_ProjectName' in fTrackSettings:
            displayText += "Project Name: %s\n" % fTrackSettings[ 'FT_ProjectName' ]
        
        dialog.setValue("sgentityinfo.val",displayText)
        dialog.setValue("sgversion.val",fTrackSettings.get( 'FT_AssetName', "" ))
        dialog.setValue("sgdescription.val",fTrackSettings.get( 'FT_Description', "" ))
        
    if len(displayText)>0:
        dialog.enableValue("sgsubmit.val",True)
        dialog.setValue("sgsubmit.val",True)
    else:
        dialog.enableValue("sgsubmit.val",False)
        dialog.setValue("sgsubmit.val",False)

def LoadIntegrationSettings():
    global fTrackSettings
    global shotgunSettings
    global pulledFTrackSettings
    fTrackSettings = {}
    shotgunSettings = {}
        
    settingsFile = GetShotgunSettingsFilename()
    if os.path.exists( settingsFile ):
        lines = [line.strip() for line in open(settingsFile)]
        ProcessLines( lines, True )
        
    settingsFile = GetFTrackSettingsFilename()
    if os.path.exists( settingsFile ):
        lines = [line.strip() for line in open(settingsFile)]
        ProcessLines( lines, False )
    
    pulledFTrackSettings = getFtrackData()
    if len(pulledFTrackSettings) >0:
        ftrackSettings = {}
    
def getFtrackData():
    # get ftrack data from launched app
    import os
    try:
        import ftrack
    except:
        return {}
        
    import json
    import base64
    decodedEventData = json.loads(
        base64.b64decode(
            os.environ.get('FTRACK_CONNECT_EVENT')
        )
    )
    taskId = decodedEventData.get('selection')[0]['entityId']
    user = decodedEventData.get('source')['user']
    task = ftrack.Task(taskId)
    
    ftrackData = {}
    ftrackData["FT_Username"] = user['username']
    ftrackData["FT_TaskName"] = task.getName()
    ftrackData["FT_TaskId"] = task.getId()
    ftrackData["FT_Description"] = task.getDescription()
    try:
        project = task.getProject()
        ftrackData["FT_ProjectName"] = project.getName()
        ftrackData["FT_ProjectId"] = project.getId()
    except:
        pass
    
    try:
        asset = task.getAssets()[0]
        ftrackData[ "FT_AssetName" ] = asset.getName()
        ftrackData["FT_AssetId"] = asset.getId()
    except:
        pass
    
    return ftrackData
    
def IntegrationTypeBoxChanged():
    updateDisplay()
    
    shotgunEnabled = (scriptDialog.GetValue("IntegrationTypeBox") == "Shotgun") and scriptDialog.GetValue( "CreateVersionBox" )
    scriptDialog.SetEnabled( "IntegrationUploadMovieBox", shotgunEnabled )
    scriptDialog.SetEnabled( "IntegrationUploadFilmStripBox", shotgunEnabled )
        
def ShotgunSubmitCallback():
    global dialog
    draftEnabled = dialog.value( "draftsubmit.val" )
    shotgunEnabled = dialog.value( "sgsubmit.val" )
    draftQuickEnabled = dialog.value( "draftQuick.val" )

    dialog.enableValue( "sgversion.val", shotgunEnabled )
    dialog.enableValue( "sgdescription.val", shotgunEnabled )
    dialog.enableValue( "sgentityinfo.val", shotgunEnabled )
    dialog.enableValue( "sgentitylabel.val", shotgunEnabled ) 
    
    dialog.enableValue( "sgdraftlabel.val", shotgunEnabled )
    dialog.enableValue( "sguploadmovie.val", shotgunEnabled )
    dialog.enableValue( "sguploadfilm.val", not(not shotgunEnabled or (not dialog.value("integration.val") == "Shotgun") )) 

    dialog.enableValue( "drafttoshotgun.val", draftEnabled and shotgunEnabled )
    dialog.enableValue( "draftshotgundata.val", draftEnabled and shotgunEnabled and not draftQuickEnabled )

def DraftSubmitCallback():
    global dialog
    draftEnabled = dialog.value( "draftsubmit.val" )
    shotgunEnabled = dialog.value( "sgsubmit.val" )
    draftQuickEnabled = dialog.value( "draftQuick.val" )
    draftCreatesMovie = IsMovieFromFormat( dialog.value( "draftFormat.val" ) )
    
    dialog.enableValue( "draftQuick.val", draftEnabled )
    dialog.enableValue( "draftFormat.val", 1 if (draftEnabled and draftQuickEnabled) else 0 )
    dialog.enableValue( "draftCodec.val", 1 if (draftEnabled and draftQuickEnabled) else 0 )
    dialog.enableValue( "draftResolution.val", 1 if (draftEnabled and draftQuickEnabled) else 0 )
    dialog.enableValue( "draftQuality.val", 1 if (draftEnabled and draftQuickEnabled and draftCreatesMovie) else 0 )
    dialog.enableValue( "draftFrameRate.val", 1 if (draftEnabled and draftQuickEnabled and draftCreatesMovie) else 0 )

    dialog.enableValue( "draftCustom.val", draftEnabled )
    dialog.enableValue( "drafttemplate.val", 1 if (draftEnabled and not draftQuickEnabled) else 0)
    dialog.enableValue( "drafttemplatelabel.val", 1 if (draftEnabled and not draftQuickEnabled) else 0 )
    dialog.enableValue( "draftusername.val", 1 if (draftEnabled and not draftQuickEnabled) else 0 )
    dialog.enableValue( "draftentityname.val", 1 if (draftEnabled and not draftQuickEnabled) else 0 )
    dialog.enableValue( "draftversionname.val", 1 if (draftEnabled and not draftQuickEnabled) else 0 )
    dialog.enableValue( "draftadditionalargs.val", 1 if (draftEnabled and not draftQuickEnabled) else 0 )

    dialog.enableValue( "drafttoshotgun.val", draftEnabled and shotgunEnabled )
    dialog.enableValue( "draftshotgundata.val", draftEnabled and shotgunEnabled and not draftQuickEnabled )

    AdjustQuality()

def DraftShotgunDataCallback():
    global dialog, shotgunSettings

    user = shotgunSettings.get( 'UserName', "" )
    task = shotgunSettings.get( 'Taskname', "" )
    project = shotgunSettings.get( 'ProjectName', "" )
    entity = shotgunSettings.get( 'EntityName', "" )
    draftTemplate = shotgunSettings.get( 'DraftTemplate', "" )

    entityName = ""
    if task.strip() != "" and task.strip() != "None":
        entityName = task
    elif project.strip() != "" and entity.strip() != "":
        entityName = "%s > %s" % (project, entity)

    draftTemplateName = dialog.value( "drafttemplate.val" )
    if draftTemplate.strip() != "" and draftTemplate != "None":
        draftTemplateName = draftTemplate

    version = dialog.value( "sgversion.val" )

    dialog.setValue( "drafttemplate.val", draftTemplateName )
    dialog.setValue( "draftusername.val", user )
    dialog.setValue( "draftentityname.val", entityName )
    dialog.setValue( "draftversionname.val", version )

def InputRenderJobs(job, availableJobs):
    dependentJobs = []
    node = hou.node(job)
    try:
        for inputNode in node.inputs():        
             # If this is a merge ROP, we want its input ROPs.
            if inputNode.type().description() == "Merge":
                for inputROP in GetROPsFromMergeROP( inputNode ):
                    if inputROP.path() in availableJobs:
                        dependentJobs.append(inputROP.path())
                    else:
                        dependentJobs.extend(InputRenderJobs(inputROP.path(),availableJobs))
            else:
                if inputNode.path() in availableJobs:
                    dependentJobs.append(inputNode.path())
                else:
                    dependentJobs.extend(InputRenderJobs(inputNode.path(),availableJobs))
    except:
        pass
    return dependentJobs
    
def SubmitRenderJob( job, jobOrdering, jobCount, totalJobs, batch, jigsawRegionCount, jigsawRegions ):
    global dialog
    
    groupBatch = batch
    autoDependencies = int(dialog.value( "automaticDependencies.val" ))
    if autoDependencies:
        if not jobOrdering[job][0] == "":
            return
    jigsawEnabled = (dialog.value( "jigsawenabled.val" ) == 1)
    dependencies = dialog.value( "dependencies.val" )
    if autoDependencies:
        if len(jobOrdering[job]) >1:
            dependencies = ""
            deps = []
            for i in range(1, len(jobOrdering[job]) ):
                depJobName = jobOrdering[job][i]
                SubmitRenderJob(depJobName,jobOrdering,jobCount,totalJobs, True, jigsawRegionCount, jigsawRegions)
                deps.append(jobOrdering[depJobName][0])
            
            dependencies = ",".join(deps)
            groupBatch = True
            
    
    if dialog.value("tilesenabled.val") is not None and dialog.value("tilesenabled.val") != "":
        tilesEnabled = int( dialog.value( "tilesenabled.val" ) )
        tilesInX = int( dialog.value( "tilesinx.val" ) )
        tilesInY = int( dialog.value( "tilesiny.val" ) )
    else:
        tilesEnabled = 0
        tilesInX = 0
        tilesInY = 0
    
    separateWedgeJobs = dialog.value("separateWedgeJobs.val")
    paddedNumberRegex = re.compile( "([0-9]+)", re.IGNORECASE )
    counter = 1
    innerCounter = 1
    innerTilesEnabled = tilesEnabled
    renderNode = hou.node( job )
    
    jobResult = ""
    
    isHQueueSim = renderNode.type().description() == "HQueue Simulation"
    if isHQueueSim:
        innerTilesEnabled = 0
    
    isWedge = renderNode.type().description() == "Wedge"
    if isWedge and separateWedgeJobs:
        counter = WedgeTasks(renderNode)
        
        wrange = renderNode.parm("wrange").eval()
        if wrange == 0:
            totalJobs += counter - 1
    
    if innerTilesEnabled:
        if jigsawEnabled:
            innerCounter = jigsawRegionCount
        else:
            innerCounter = tilesInX *tilesInY
    
    for i in range(0, counter):
        
        # Check the output file
        output = GetOutputPath( renderNode )
        if output != "" and output != "COMMAND":
            outputFile = output.eval()
            matches = paddedNumberRegex.findall( os.path.basename( outputFile ) )
            if matches != None and len( matches ) > 0:
                paddingString = matches[ len( matches ) - 1 ]
                paddingSize = len( paddingString )
                padding = "#"
                while len(padding) < paddingSize:
                    padding = padding + "#"
                paddedOutputFile = RightReplace( outputFile, paddingString, padding, 1 )
        elif output != "COMMAND":
            print "Output path for ROP: \"%s\" is not specified" % job

        # Get the IFD info, if applicable
        ifdFile = ""
        paddedIfdFile = ""
        ifdFileParameter = GetIFD( renderNode )
        if ifdFileParameter != None:
            ifdFile = ifdFileParameter.eval()
            matches = paddedNumberRegex.findall( os.path.basename( ifdFile ) )
            if matches != None and len( matches ) > 0:
                paddingString = matches[ len( matches ) - 1 ]
                paddingSize = len( paddingString )
                padding = "0"
                while len(padding) < paddingSize:
                    padding = padding + "0"
                paddedIfdFile = RightReplace( ifdFile, paddingString, padding, 1 )
            else:
                paddedIfdFile = ifdFile
        
        tilesSingleFrame = False
        
        isMantra = (renderNode.type().description() == "Mantra")
        isArnold = (renderNode.type().description() == "Arnold")
        
        if innerTilesEnabled == 0:
            innerCounter = 1
        else:
            if dialog.value( "tilessingleframeenabled.val" ) != 1:
                if ifdFile != "" and ( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ) ):
                    innerCounter = 1
                else:
                    if jigsawEnabled:
                        innerCounter = jigsawRegionCount
                    else:
                        innerCounter = tilesInX *tilesInY              
            else:
                innerCounter = 1
                tilesSingleFrame = True
        
        jobIds = []
        
        localMantraExport = (dialog.value( "localmantraexport.val" ) == 1)
        localArnoldExport = (dialog.value( "localarnoldexport.val" ) == 1)
        
        if ifdFile != "" and ( ( dialog.value( "mantrajob.val" ) and isMantra and localMantraExport ) or ( dialog.value( "arnoldjob.val" ) and isArnold and localArnoldExport ) ):
            if innerTilesEnabled and tilesSingleFrame:
                singleFrame = dialog.value( "tilessingleframe.val" )
                renderNode.render( (singleFrame,singleFrame,1), (), ignore_inputs=dialog.value( "ignoreinputs.val" ) )
            else:
                startFrame = 1
                startFrameParm = renderNode.parm( "f1" )
                if startFrameParm != None:
                    startFrame = int(startFrameParm.eval())
                    
                endFrame = 1
                endFrameParm = renderNode.parm( "f2" )
                if endFrameParm != None:
                    endFrame = int(endFrameParm.eval())
                    
                frameStep = 1
                frameStepParm = renderNode.parm( "f3" )
                if frameStepParm != None:
                    frameStep = int(frameStepParm.eval())
                
                renderNode.render( (startFrame,endFrame,frameStep), (), ignore_inputs=dialog.value( "ignoreinputs.val" ) )
            
        else:
            for j in range(0,innerCounter):
                
                # outputFile = "" 
                # paddedOutputFile = ""
                doShotgun = False
                doDraft = False
                
                # Check the output file
                output = GetOutputPath( renderNode )
                paddedOutputFile = ""
                if output != "" and output != "COMMAND":
                    paddedOutputFile = output.eval()
                else:
                    continue
                matches = paddedNumberRegex.findall( os.path.basename( paddedOutputFile ) )
                if matches != None and len( matches ) > 0:
                    paddingString = matches[ len( matches ) - 1 ]
                    paddingSize = len( paddingString )
                    padding = "#"
                    while len(padding) < paddingSize:
                        padding = padding + "#"
                    paddedOutputFile = RightReplace( paddedOutputFile, paddingString, padding, 1 )
                
                dialog.setValue( "status.val", str(int( ( jobCount * 100 ) / ( totalJobs * 2 ) ) ) + "%" )
                jobCount += 1   
                print "Preparing job %d of %d for submission..." % ( jobCount, totalJobs )
                
                jobName = dialog.value( "jobname.val" )
                jobName = "%s - %s"%(jobName,job)
                
                if separateWedgeJobs:
                    jobName = jobName + "{WEDGE #"+str(i)+"}"
                    
                if innerTilesEnabled and not tilesSingleFrame and not(ifdFile != "" and ( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ) ) ):
                    jobName = jobName + " - Region "+str(j)
                
                # Create submission info file
                jobInfoFile = os.path.join(homeDir, "temp", "houdini_submit_info%d.job") % jobCount
                fileHandle = open( jobInfoFile, "w" )
                fileHandle.write( "Plugin=Houdini\n" )
                fileHandle.write( "Name=%s\n" % jobName )
                fileHandle.write( "Comment=%s\n" % dialog.value( "comment.val" ) )
                fileHandle.write( "Department=%s\n" % dialog.value( "department.val" ) )
                fileHandle.write( "Pool=%s\n" % dialog.value( "pool.val" ) )
                fileHandle.write( "SecondaryPool=%s\n" % dialog.value( "secondarypool.val" ) )
                fileHandle.write( "Group=%s\n" % dialog.value( "group.val" ) )
                fileHandle.write( "Priority=%s\n" % dialog.value ( "priority.val" ) )
                fileHandle.write( "TaskTimeoutMinutes=%s\n" % dialog.value( "tasktimeout.val" ) )
                fileHandle.write( "EnableAutoTimeout=%s\n" % dialog.value( "autotimeout.val" ) )
                fileHandle.write( "ConcurrentTasks=%s\n" % dialog.value( "concurrent.val" ) )
                fileHandle.write( "MachineLimit=%s\n" % dialog.value( "machinelimit.val" ) )
                fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.value( "slavelimit.val" ) )
                fileHandle.write( "LimitGroups=%s\n" % dialog.value( "limits.val" ) )
                fileHandle.write( "JobDependencies=%s\n" % dependencies )
                fileHandle.write( "OnJobComplete=%s\n" % dialog.value( "onjobcomplete.val" ) )

                if dialog.value( "jobsuspended.val" ):
                    fileHandle.write( "InitialStatus=Suspended\n" )

                if dialog.value( "isblacklist.val" ):
                    fileHandle.write( "Blacklist=%s\n" % dialog.value( "machinelist.val" ) )
                else:
                    fileHandle.write( "Whitelist=%s\n" % dialog.value( "machinelist.val" ) )
                
                if isHQueueSim:
                    sliceCount = 1
                    sliceType = renderNode.parm("slice_type").evalAsString()
                    if sliceType == "volume":
                        slicesInX = renderNode.parm("slicediv1").eval()
                        slicesInY = renderNode.parm("slicediv2").eval()
                        slicesInZ = renderNode.parm("slicediv3").eval()
                        sliceCount = slicesInX * slicesInY * slicesInZ
                    elif sliceType == "particle":
                        sliceCount = renderNode.parm("num_slices").eval()
                    
                    fileHandle.write( "Frames=0-%s\n" % ( sliceCount - 1 ) )
                elif tilesSingleFrame:
                    if not( ifdFile != "" and (( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold )) ):
                        fileHandle.write( "TileJob=True\n" )
                        if jigsawEnabled:
                            fileHandle.write( "TileJobTilesInX=%s\n" % jigsawRegionCount )
                            fileHandle.write( "TileJobTilesInY=%s\n" % 1 )
                        else:
                            fileHandle.write( "TileJobTilesInX=%s\n" % tilesInX )
                            fileHandle.write( "TileJobTilesInY=%s\n" % tilesInY )
                        fileHandle.write( "TileJobFrame=%s\n" % dialog.value( "tilessingleframe.val" )  );
                    else:
                        fileHandle.write( "Frames=%s\n" % ( dialog.value( "tilessingleframe.val" ) ) )
                elif dialog.value( "overrideframes.val" ):
                    fileHandle.write( "Frames=%s\n" % dialog.value( "framelist.val" ) )
                else:
                    fileHandle.write( "Frames=%s\n" % GetFrameInfo( renderNode ) )
                
                if isHQueueSim:
                    fileHandle.write( "ChunkSize=1\n" )
                if renderNode.type().name() == "rop_alembic":
                    if not renderNode.parm("render_full_range").eval():
                        fileHandle.write("ChunkSize=10000\n" )
                    else:
                        fileHandle.write( "ChunkSize=%s\n" %  dialog.value( "framespertask.val" ) )
                elif tilesSingleFrame:
                    if ifdFile != "" and (( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold )):
                        fileHandle.write( "ChunkSize=1\n" )
                else:
                    fileHandle.write( "ChunkSize=%s\n" %  dialog.value( "framespertask.val" ) )
                
                if tilesSingleFrame and not( ifdFile != "" and (( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ))):
                    output = GetOutputPath( renderNode )
                    imageFileName = ""
                    if output != "" and output != "COMMAND":
                        imageFileName = output.eval()
                    else:
                        continue
                    tileName = ""
                    paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                    matches = paddedNumberRegex.findall( imageFileName )
                    if matches != None and len( matches ) > 0:
                        paddingString = matches[ len( matches ) - 1 ]
                        paddingSize = len( paddingString )
                        padding = str(dialog.value( "tilessingleframe.val" ))                            
                        padding = "_tile?_" + padding
                        tileName = RightReplace( imageFileName, paddingString, padding, 1 )
                    else:
                        splitFilename = os.path.splitext(imageFileName)
                        tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
                    
                    tileRange = range(0, tilesInX*tilesInY)
                    if jigsawEnabled:
                        tileRange = range(0, jigsawRegionCount)
                    for currTile in tileRange:
                        regionOutputFileName = tileName.replace( "?", str(currTile) )
                        fileHandle.write( "OutputFilename0Tile%s=%s\n"%(currTile,regionOutputFileName) )
                    
                elif ifdFile != "":
                    fileHandle.write( "OutputDirectory0=%s\n" % os.path.dirname( ifdFile ) )
                    if not( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ) ):
                        doShotgun = True
                elif paddedOutputFile != "":
                    fileHandle.write( "OutputFilename0=%s\n" % paddedOutputFile )
                    doDraft = True
                    doShotgun = True
                
                # Shotgun/Draft
                extraKVPIndex = 0
                
                if innerTilesEnabled:
                    groupBatch = True
                if ifdFile != "" and ( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ) ):
                    groupBatch = True
                if separateWedgeJobs:
                    groupBatch = True
                if doShotgun:
                    if dialog.value( "sgsubmit.val" ):
                        if dialog.value("integration.val") == "Shotgun":
                            fileHandle.write( "ExtraInfo0=%s\n" % shotgunSettings.get('TaskName', "") )
                            fileHandle.write( "ExtraInfo1=%s\n" % shotgunSettings.get('ProjectName', "") )
                            fileHandle.write( "ExtraInfo2=%s\n" % shotgunSettings.get('EntityName', "") )
                            fileHandle.write( "ExtraInfo3=%s\n" % dialog.value( "sgversion.val" ) )
                            fileHandle.write( "ExtraInfo4=%s\n" % dialog.value( "sgdescription.val" ) )
                            fileHandle.write( "ExtraInfo5=%s\n" % shotgunSettings.get('UserName', "") )
                        
                            for key in shotgunSettings:
                                if key != 'DraftTemplate':
                                    fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, shotgunSettings[key]) )
                                    extraKVPIndex += 1
                            if dialog.value( "sguploadmovie.val" ):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                            if dialog.value( "sguploadfilm.val" ):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                        else:
                            fileHandle.write( "ExtraInfo0=%s\n" % fTrackSettings.get('FT_TaskName', "") )
                            fileHandle.write( "ExtraInfo1=%s\n" % fTrackSettings.get('FT_ProjectName', "") )
                            fileHandle.write( "ExtraInfo2=%s\n" % dialog.value( "sgversion.val" ) )
                            fileHandle.write( "ExtraInfo4=%s\n" % dialog.value( "sgdescription.val" ) )
                            fileHandle.write( "ExtraInfo5=%s\n" % fTrackSettings.get('FT_Username', "") )
                            for key in fTrackSettings:
                                fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, fTrackSettings[key]) )
                                extraKVPIndex += 1
                            if dialog.value( "sguploadmovie.val" ):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateFTMovie=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                
                if doDraft:
                    if dialog.value( "draftsubmit.val" ):
                        if dialog.value( "draftQuick.val" ):
                            fileHandle.write( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][0]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][1]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, ResolutionsDict[dialog.value("draftResolution.val")]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, dialog.value("draftCodec.val")) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftQuality=%d\n" % (extraKVPIndex, int( float( dialog.value("draftQuality.val") ) ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, dialog.value("draftFrameRate.val")) )
                            extraKVPIndex += 1
                        else:
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, dialog.value( "drafttemplate.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.value( "draftusername.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.value( "draftentityname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.value( "draftversionname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, dialog.value( "draftadditionalargs.val" ) ) )
                            extraKVPIndex += 1

                        fileHandle.write( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, dialog.value( "drafttoshotgun.val" ) and dialog.value( "sgsubmit.val" ) ) )
                        extraKVPIndex += 1

                        groupBatch = True
                
                if groupBatch:
                    fileHandle.write( "BatchName=%s\n" % (dialog.value( "jobname.val" ) ) ) 
                
                fileHandle.close()

                # Create plugin info file
                pluginInfoFile = os.path.join( homeDir, "temp", "houdini_plugin_info%d.job" % jobCount )
                fileHandle = open( pluginInfoFile, "w" )

                if not dialog.value( "submitscene.val" ):
                    fileHandle.write( "SceneFile=%s\n" % hou.hipFile.path() )

                #alf sets it's own output driver
                if renderNode.type().description() == "Alfred" and renderNode.parm( "alf_driver" ) != None:
                    fileHandle.write( "OutputDriver=%s\n" % renderNode.parm( "alf_driver" ).eval() )
                else:
                    fileHandle.write( "OutputDriver=%s\n" % job )
                    print "OutputDriver=%s\n" % job

                fileHandle.write( "IgnoreInputs=%s\n" % dialog.value( "ignoreinputs.val" ) )
                fileHandle.write( "Version=%s\n" % hou.applicationVersion()[0] )
                fileHandle.write( "Build=%s\n" % dialog.value( "bits.val" ) )
                
                if isHQueueSim:
                    fileHandle.write( "SimJob=True" )
                
                if separateWedgeJobs:
                    fileHandle.write("WedgeNum=%s\n" % i)
                
                if not( ifdFile != "" and ( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold )) ) and innerTilesEnabled:
                    fileHandle.write( "RegionRendering=True\n" )
                    if tilesSingleFrame:
                        curRegion = 0
                        if jigsawEnabled:
                            for region in range(0,jigsawRegionCount):
                                xstart = jigsawRegions[region*4]
                                xend = jigsawRegions[region*4 + 1]
                                ystart = jigsawRegions[region*4 + 2]
                                yend = jigsawRegions[region*4 + 3]
                                
                                fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                fileHandle.write( "RegionBottom%s=%s\n" % (curRegion, ystart) )
                                fileHandle.write( "RegionTop%s=%s\n" % (curRegion,yend) )
                                curRegion += 1
                        else:
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    
                                    xstart = x * 1.0 / tilesInX
                                    xend = ( x + 1.0 ) / tilesInX
                                    ystart = y * 1.0 / tilesInY
                                    yend = ( y + 1.0 ) / tilesInY
                                    
                                    fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                    fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                    fileHandle.write( "RegionBottom%s=%s\n" % (curRegion, ystart) )
                                    fileHandle.write( "RegionTop%s=%s\n" % (curRegion,yend) )
                                    curRegion += 1
                    else:
                        fileHandle.write( "CurrentTile=%s\n" % j )
                        
                        if jigsawEnabled:
                            xstart = jigsawRegions[j*4]
                            xend = jigsawRegions[j*4 + 1]
                            ystart = jigsawRegions[j*4 + 2]
                            yend = jigsawRegions[j*4 + 3]
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                        else:
                            curY = 0
                            curX = 0
                            jobNumberFound = False
                            tempJobNum = 0
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    if tempJobNum == j:
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
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                
                fileHandle.close()
                
                arguments = []
                arguments.append( jobInfoFile )
                arguments.append( pluginInfoFile )
                if dialog.value( "submitscene.val" ):
                    arguments.append( hou.hipFile.path() )
                    
                jobResult = CallDeadlineCommand( arguments )
                jobId = "";
                resultArray = jobResult.split("\n")
                for line in resultArray:
                    if line.startswith("JobID="):
                        jobId = line.replace("JobID=","")
                        jobId = jobId.strip()
                        break
                
                jobIds.append(jobId)
                
                print "---------------------------------------------------"
                print jobResult
                print "---------------------------------------------------"
            
        
        arnoldTilesEnabled = False
        
        # Create mantra job and plugin info file, if necessary
        if ifdFile != "" and dialog.value( "mantrajob.val" ) and isMantra:
            dialog.setValue( "status.val", str(int( ( jobCount * 100 ) / ( totalJobs * 2 ) ) ) + "%" )
            
            mantraTilesEnabled = tilesEnabled
            mantraJobCount = 1
            tilesSingleFrameEnabled = False
            if renderNode.parm("vm_tile_render") == None:
                mantraTilesEnabled = False
            elif mantraTilesEnabled:
                if dialog.value( "tilessingleframeenabled.val" ) != 1:
                    mantraJobCount = tilesInX *tilesInY
                else:
                    mantraJobCount = 1
                    tilesSingleFrameEnabled = True
            
            mantraJobDependencies = ",".join(jobIds)
            jobIds = []
            
            for jMantra in range(0,mantraJobCount):
                jobCount += 1   
                print "Preparing job %d of %d for submission..." % ( jobCount, totalJobs )
            
                mantraJobInfoFile = os.path.join( homeDir, "temp", "mantra_job_info%d.job" % jobCount )
                mantraPluginInfoFile = os.path.join( homeDir, "temp", "mantra_plugin_info%d.job" % jobCount )

                
                mantraJobName = (dialog.value( "jobname.val" ) + "- Mantra Job" )
                if mantraTilesEnabled and dialog.value( "tilessingleframeenabled.val" ) != 1:
                    mantraJobName += " - Region " + str( jMantra )
                
                fileHandle = open( mantraJobInfoFile, 'w' )
                fileHandle.write( "Plugin=Mantra\n" )
                fileHandle.write( "Name=%s\n" % mantraJobName )
                
                if innerTilesEnabled == 1 or dialog.value( "localmantraexport.val" ) != 1:
                    fileHandle.write( "BatchName=%s\n" % (dialog.value( "jobname.val" ) ) ) 
                
                fileHandle.write( "Comment=%s\n" % dialog.value( "comment.val" ) )
                fileHandle.write( "Department=%s\n" % dialog.value( "department.val" ) )
                fileHandle.write( "Pool=%s\n" % dialog.value( "mantrapool.val" ) )
                fileHandle.write( "SecondaryPool=%s\n" % dialog.value( "mantrasecondarypool.val" ) )
                fileHandle.write( "Group=%s\n" % dialog.value( "mantragroup.val" ) )
                fileHandle.write( "Priority=%s\n" % dialog.value ( "mantrapriority.val" ) )
                fileHandle.write( "TaskTimeoutMinutes=%s\n" % dialog.value( "mantratasktimeout.val" ) )
                fileHandle.write( "EnableAutoTimeout=%s\n" % dialog.value( "mantraautotimeout.val" ) )
                fileHandle.write( "ConcurrentTasks=%s\n" % dialog.value( "mantraconcurrent.val" ) )
                fileHandle.write( "MachineLimit=%s\n" % dialog.value( "mantramachinelimit.val" ) )
                fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.value( "mantraslavelimit.val" ) )
                fileHandle.write( "LimitGroups=%s\n" % dialog.value( "mantralimits.val" ) )
                fileHandle.write( "IsFrameDependent=true\n" )
                fileHandle.write( "OnJobComplete=%s\n" % dialog.value( "onjobcomplete.val" ) )
                fileHandle.write( "JobDependencies=%s\n" % mantraJobDependencies )
                
                if dialog.value( "jobsuspended.val" ):
                    fileHandle.write( "InitialStatus=Suspended\n" )

                if dialog.value( "mantraisblacklist.val" ):
                    fileHandle.write( "Blacklist=%s\n" % dialog.value( "mantramachinelist.val" ) )
                else:
                    fileHandle.write( "Whitelist=%s\n" % dialog.value( "mantramachinelist.val" ) )
                
                if tilesSingleFrame:
                    fileHandle.write( "TileJob=True\n" )
                    if jigsawEnabled:
                        fileHandle.write( "TileJobTilesInX=%s\n" % jigsawRegionCount )
                        fileHandle.write( "TileJobTilesInY=%s\n" % 1 )
                    else:
                        fileHandle.write( "TileJobTilesInX=%s\n" % tilesInX )
                        fileHandle.write( "TileJobTilesInY=%s\n" % tilesInY )
                    
                    fileHandle.write( "TileJobFrame=%s\n" % dialog.value( "tilessingleframe.val" )  )
                elif dialog.value( "overrideframes.val" ):
                    fileHandle.write( "Frames=%s\n" % dialog.value( "framelist.val" ) )
                    fileHandle.write( "ChunkSize=1\n" )
                else:
                    fileHandle.write( "Frames=%s\n" % GetFrameInfo( renderNode ) )
                    fileHandle.write( "ChunkSize=1\n" )

                if paddedOutputFile != "":
                    if tilesSingleFrame:
                        tileName = paddedOutputFile
                        paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                        matches = paddingRegex.findall( os.path.basename( tileName ) )
                        if matches != None and len( matches ) > 0:
                            paddingString = matches[ len( matches ) - 1 ]
                            paddingSize = len( paddingString )
                            padding = str(dialog.value( "tilessingleframe.val" ))                            
                            while len(padding) < paddingSize:
                                padding = "0" + padding
                            
                            padding = "_tile?_" + padding
                            tileName = RightReplace( tileName, paddingString, padding, 1 )
                        else:
                            splitFilename = os.path.splitext(tileName)
                            tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
                        
                        for currTile in range(0, tilesInX*tilesInY):
                            regionOutputFileName = tileName.replace( "?", str(currTile) )
                            fileHandle.write( "OutputFilename0Tile%s=%s\n"%(currTile,regionOutputFileName) )
                            
                    else:
                        fileHandle.write( "OutputFilename0=%s\n" % paddedOutputFile)

                    eztraKVPIndex = 0
                    if dialog.value( "sgsubmit.val" ):
                        fileHandle.write( "ExtraInfo0=%s\n" % shotgunSettings.get('TaskName', "") )
                        fileHandle.write( "ExtraInfo1=%s\n" % shotgunSettings.get('ProjectName', "") )
                        fileHandle.write( "ExtraInfo2=%s\n" % shotgunSettings.get('EntityName', "") )
                        fileHandle.write( "ExtraInfo3=%s\n" % dialog.value( "sgversion.val" ) )
                        fileHandle.write( "ExtraInfo4=%s\n" % dialog.value( "sgdescription.val" ) )
                        fileHandle.write( "ExtraInfo5=%s\n" % shotgunSettings.get('UserName', "") )

                        for key in shotgunSettings:
                            if key != 'DraftTemplate':
                                fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, shotgunSettings[key] ) )
                                extraKVPIndex += 1

                    if dialog.value( "draftsubmit.val" ):
                        if dialog.value( "draftQuick.val" ):
                            fileHandle.write( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][0]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][1]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, ResolutionsDict[dialog.value("draftResolution.val")]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, dialog.value("draftCodec.val")) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftQuality=%d\n" % (extraKVPIndex, int( float( dialog.value("draftQuality.val") ) ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, dialog.value("draftFrameRate.val")) )
                            extraKVPIndex += 1
                        else:
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, dialog.value( "drafttemplate.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.value( "draftusername.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.value( "draftentityname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.value( "draftversionname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, dialog.value( "drafttoshotgun.val" ) and dialog.value( "sgsubmit.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, dialog.value( "draftadditionalargs.val" ) ) )
                            extraKVPIndex += 1

                fileHandle.close()
                
                # Create plugin info file for Mantra
                fileHandle = open( mantraPluginInfoFile, 'w' )
                fileHandle.write( "SceneFile=%s\n" % paddedIfdFile )
                fileHandle.write( "Version=%s\n" % hou.applicationVersion()[0] )
                fileHandle.write( "Threads=%s\n" % dialog.value( "mantrathreads.val" ) )
                fileHandle.write( "CommandLineOptions=\n" )
                
                if mantraTilesEnabled:
                    fileHandle.write( "RegionRendering=True\n" )
                    if tilesSingleFrame:
                        curRegion = 0
                        if jigsawEnabled:
                            for region in range(0,jigsawRegionCount):
                                xstart = jigsawRegions[region*4]
                                xend = jigsawRegions[region*4+1]
                                ystart = jigsawRegions[region*4+2]
                                yend = jigsawRegions[region*4+3]
                                
                                fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                fileHandle.write( "RegionBottom%s=%s\n" % (curRegion, ystart) )
                                fileHandle.write( "RegionTop%s=%s\n" % (curRegion,yend) )
                                curRegion += 1
                        else:
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    
                                    xstart = x * 1.0 / tilesInX
                                    xend = ( x + 1.0 ) / tilesInX
                                    ystart = y * 1.0 / tilesInY
                                    yend = ( y + 1.0 ) / tilesInY
                                    
                                    fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                    fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                    fileHandle.write( "RegionBottom%s=%s\n" % (curRegion, ystart) )
                                    fileHandle.write( "RegionTop%s=%s\n" % (curRegion,yend) )
                                    curRegion += 1
                    else:
                        fileHandle.write( "CurrentTile=%s\n" % jMantra )
                        
                        if jigsawEnabled:
                            xstart = jigsawRegions[j*4]
                            xend = jigsawRegions[j*4+1]
                            ystart = jigsawRegions[j*4+2]
                            yend = jigsawRegions[j*4+3]
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                        else:
                            curY = 0
                            curX = 0
                            jobNumberFound = False
                            tempJobNum = 0
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    if tempJobNum == jMantra:
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
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                        
                fileHandle.close()
            
                arguments = []
                arguments.append( mantraJobInfoFile )
                arguments.append( mantraPluginInfoFile )
                if dialog.value( "submitscene.val" ):
                    arguments.append( hou.hipFile.path() )
                    
                jobResult = CallDeadlineCommand( arguments )
                jobId = "";
                resultArray = jobResult.split()
                for line in resultArray:
                    if line.startswith("JobID="):
                        jobId = line.replace("JobID=","")
                        break
                
                jobIds.append(jobId)
                
                print "---------------------------------------------------"
                print jobResult
                print "---------------------------------------------------"
        elif ifdFile != "" and dialog.value( "arnoldjob.val" ) and isArnold:
            dialog.setValue( "status.val", str(int( ( jobCount * 100 ) / ( totalJobs * 2 ) ) ) + "%" )
            
            arnoldTilesEnabled = tilesEnabled
            arnoldJobCount = 1
            tilesSingleFrameEnabled = False
            if arnoldTilesEnabled:
                if dialog.value( "tilessingleframeenabled.val" ) != 1:
                    arnoldJobCount = tilesInX *tilesInY
                else:
                    arnoldJobCount = 1
                    tilesSingleFrameEnabled = True
            
            arnoldJobDependencies = ",".join(jobIds)
            jobIds = []
            
            for jArnold in range(0,arnoldJobCount):
                jobCount += 1   
                print "Preparing job %d of %d for submission..." % ( jobCount, totalJobs )
            
                arnoldJobInfoFile = os.path.join( homeDir, "temp", "arnold_job_info%d.job" % jobCount )
                arnoldPluginInfoFile = os.path.join( homeDir, "temp", "arnold_plugin_info%d.job" % jobCount )

                
                arnoldJobName = (dialog.value( "jobname.val" ) + "- Arnold Job" )
                if arnoldTilesEnabled and dialog.value( "tilessingleframeenabled.val" ) != 1:
                    mantraJobName += " - Region " + str( jArnold )
                
                fileHandle = open( arnoldJobInfoFile, 'w' )
                fileHandle.write( "Plugin=Arnold\n" )
                fileHandle.write( "Name=%s\n" % arnoldJobName )
                
                if innerTilesEnabled == 1 or dialog.value( "localarnoldexport.val" ) != 1:
                    fileHandle.write( "BatchName=%s\n" % (dialog.value( "jobname.val" ) ) ) 
                
                fileHandle.write( "Comment=%s\n" % dialog.value( "comment.val" ) )
                fileHandle.write( "Department=%s\n" % dialog.value( "department.val" ) )
                fileHandle.write( "Pool=%s\n" % dialog.value( "arnoldpool.val" ) )
                fileHandle.write( "SecondaryPool=%s\n" % dialog.value( "arnoldsecondarypool.val" ) )
                fileHandle.write( "Group=%s\n" % dialog.value( "arnoldgroup.val" ) )
                fileHandle.write( "Priority=%s\n" % dialog.value ( "arnoldpriority.val" ) )
                fileHandle.write( "TaskTimeoutMinutes=%s\n" % dialog.value( "arnoldtasktimeout.val" ) )
                fileHandle.write( "EnableAutoTimeout=%s\n" % dialog.value( "arnoldautotimeout.val" ) )
                fileHandle.write( "ConcurrentTasks=%s\n" % dialog.value( "arnoldconcurrent.val" ) )
                fileHandle.write( "MachineLimit=%s\n" % dialog.value( "arnoldmachinelimit.val" ) )
                fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.value( "arnoldslavelimit.val" ) )
                fileHandle.write( "LimitGroups=%s\n" % dialog.value( "arnoldlimits.val" ) )
                fileHandle.write( "IsFrameDependent=true\n" )
                fileHandle.write( "OnJobComplete=%s\n" % dialog.value( "onjobcomplete.val" ) )
                fileHandle.write( "JobDependencies=%s\n" % arnoldJobDependencies )
                
                if dialog.value( "jobsuspended.val" ):
                    fileHandle.write( "InitialStatus=Suspended\n" )

                if dialog.value( "arnoldisblacklist.val" ):
                    fileHandle.write( "Blacklist=%s\n" % dialog.value( "arnoldmachinelist.val" ) )
                else:
                    fileHandle.write( "Whitelist=%s\n" % dialog.value( "arnoldmachinelist.val" ) )
                
                if tilesSingleFrame:
                    fileHandle.write( "TileJob=True\n" )
                    if jigsawEnabled:
                        fileHandle.write( "TileJobTilesInX=%s\n" % jigsawRegionCount )
                        fileHandle.write( "TileJobTilesInY=%s\n" % 1 )
                    else:
                        fileHandle.write( "TileJobTilesInX=%s\n" % tilesInX )
                        fileHandle.write( "TileJobTilesInY=%s\n" % tilesInY )
                    
                    fileHandle.write( "TileJobFrame=%s\n" % dialog.value( "tilessingleframe.val" )  )
                elif dialog.value( "overrideframes.val" ):
                    fileHandle.write( "Frames=%s\n" % dialog.value( "framelist.val" ) )
                    fileHandle.write( "ChunkSize=1\n" )
                else:
                    fileHandle.write( "Frames=%s\n" % GetFrameInfo( renderNode ) )
                    fileHandle.write( "ChunkSize=1\n" )

                if paddedOutputFile != "":
                    if tilesSingleFrame:
                        tileName = paddedOutputFile
                        paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                        matches = paddingRegex.findall( os.path.basename( tileName ) )
                        if matches != None and len( matches ) > 0:
                            paddingString = matches[ len( matches ) - 1 ]
                            paddingSize = len( paddingString )
                            padding = str(dialog.value( "tilessingleframe.val" ))                            
                            while len(padding) < paddingSize:
                                padding = "0" + padding
                            
                            padding = "_tile?_" + padding
                            tileName = RightReplace( tileName, paddingString, padding, 1 )
                        else:
                            splitFilename = os.path.splitext(tileName)
                            tileName = splitFilename[0]+"_tile?_"+splitFilename[1]
                        
                        for currTile in range(0, tilesInX*tilesInY):
                            regionOutputFileName = tileName.replace( "?", str(currTile) )
                            fileHandle.write( "OutputFilename0Tile%s=%s\n"%(currTile,regionOutputFileName) )
                            
                    else:
                        fileHandle.write( "OutputFilename0=%s\n" % paddedOutputFile)

                    eztraKVPIndex = 0
                    if dialog.value( "sgsubmit.val" ):
                        fileHandle.write( "ExtraInfo0=%s\n" % shotgunSettings.get('TaskName', "") )
                        fileHandle.write( "ExtraInfo1=%s\n" % shotgunSettings.get('ProjectName', "") )
                        fileHandle.write( "ExtraInfo2=%s\n" % shotgunSettings.get('EntityName', "") )
                        fileHandle.write( "ExtraInfo3=%s\n" % dialog.value( "sgversion.val" ) )
                        fileHandle.write( "ExtraInfo4=%s\n" % dialog.value( "sgdescription.val" ) )
                        fileHandle.write( "ExtraInfo5=%s\n" % shotgunSettings.get('UserName', "") )

                        for key in shotgunSettings:
                            if key != 'DraftTemplate':
                                fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, shotgunSettings[key] ) )
                                extraKVPIndex += 1

                    if dialog.value( "draftsubmit.val" ):
                        if dialog.value( "draftQuick.val" ):
                            fileHandle.write( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][0]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, FormatsDict[dialog.value("draftFormat.val")][1]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, ResolutionsDict[dialog.value("draftResolution.val")]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, dialog.value("draftCodec.val")) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftQuality=%d\n" % (extraKVPIndex, int( float( dialog.value("draftQuality.val") ) ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, dialog.value("draftFrameRate.val")) )
                            extraKVPIndex += 1
                        else:
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, dialog.value( "drafttemplate.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, dialog.value( "draftusername.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, dialog.value( "draftentityname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, dialog.value( "draftversionname.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, dialog.value( "drafttoshotgun.val" ) and dialog.value( "sgsubmit.val" ) ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, dialog.value( "draftadditionalargs.val" ) ) )
                            extraKVPIndex += 1

                fileHandle.close()
                
                # Create plugin info file for Mantra
                fileHandle = open( arnoldPluginInfoFile, 'w' )
                fileHandle.write( "InputFile=" + ifdFile + "\n" );
                fileHandle.write( "Threads=%s\n" % dialog.value( "arnoldthreads.val" ) )
                fileHandle.write( "CommandLineOptions=\n" );
                fileHandle.write( "Verbose=4\n" );
                
                if arnoldTilesEnabled:
                    fileHandle.write( "RegionJob=True\n" )
                    
                    camera = renderNode.parm( "camera" ).eval()
                    cameraNode = hou.node(camera)
                    
                    width = cameraNode.parm("resx").eval()
                    height = cameraNode.parm("resy").eval()
                    
                    if tilesSingleFrame:
                        
                        singleFrame = dialog.value( "tilessingleframe.val" )
                        fileHandle.write( "SingleAss=True\n" )
                        fileHandle.write( "SingleRegionFrame=%s\n"% singleFrame )
                        curRegion = 0
                        
                        output = GetOutputPath( renderNode )
                        imageFileName = ""
                        if output != "" and output != "COMMAND":
                            imageFileName = output.eval()
                        else:
                            continue
                        tileName = ""
                        outputName = ""
                        paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                        matches = paddedNumberRegex.findall( imageFileName )
                        if matches != None and len( matches ) > 0:
                            paddingString = matches[ len( matches ) - 1 ]
                            paddingSize = len( paddingString )
                            padding = str(singleFrame)
                            while len(padding) < paddingSize:
                                padding = "0" + padding
                            
                            outputName = RightReplace( imageFileName, paddingString, padding, 1 )
                            padding = "_tile#_" + padding
                            tileName = RightReplace( imageFileName, paddingString, padding, 1 )
                        else:
                            outputName = imageFileName
                            splitFilename = os.path.splitext(imageFileName)
                            tileName = splitFilename[0]+"_tile#_"+splitFilename[1]
                        
                        if jigsawEnabled:
                            for region in range(0,jigsawRegionCount):
                                xstart = int(jigsawRegions[region*4] * width +0.5 )
                                xend = int(jigsawRegions[region*4+1] * width +0.5 )
                                ystart = int(jigsawRegions[region*4+2] * height +0.5 )
                                yend = int(jigsawRegions[region*4+3] * height +0.5 )
                                
                                if xend >= width:
                                    xend  = width-1
                                if yend >= height:
                                    yend  = height-1
                                
                                regionOutputFileName = ""
                                matches = paddingRegex.findall( os.path.basename( tileName ) )
                                if matches != None and len( matches ) > 0:
                                    paddingString = matches[ len( matches ) - 1 ]
                                    paddingSize = len( paddingString )
                                    padding = str(curRegion)
                                    while len(padding) < paddingSize:
                                        padding = "0" + padding
                                    regionOutputFileName = RightReplace( tileName, paddingString, padding, 1 )
                                    
                                fileHandle.write( "RegionFilename%s=%s\n" % (curRegion, regionOutputFileName) )
                                fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                fileHandle.write( "RegionBottom%s=%s\n" % (curRegion,yend) )
                                fileHandle.write( "RegionTop%s=%s\n" % (curRegion,ystart) )
                                curRegion += 1
                        else:
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    
                                    xstart = x * 1.0 / tilesInX
                                    xend = ( x + 1.0 ) / tilesInX
                                    ystart = y * 1.0 / tilesInY
                                    yend = ( y + 1.0 ) / tilesInY
                                    
                                    xstart = int(xstart * width +0.5 )
                                    xend = int(xend * width +0.5 )
                                    ystart = int(ystart * height +0.5 )
                                    yend = int(yend * height +0.5 )
                                    
                                    if xend >= width:
                                        xend  = width-1
                                    if yend >= height:
                                        yend  = height-1
                                    
                                    regionOutputFileName = ""
                                    matches = paddingRegex.findall( os.path.basename( tileName ) )
                                    if matches != None and len( matches ) > 0:
                                        paddingString = matches[ len( matches ) - 1 ]
                                        paddingSize = len( paddingString )
                                        padding = str(curRegion)
                                        while len(padding) < paddingSize:
                                            padding = "0" + padding
                                        regionOutputFileName = RightReplace( tileName, paddingString, padding, 1 )
                                    
                                    fileHandle.write( "RegionFilename%s=%s\n" % (curRegion, regionOutputFileName) )
                                    fileHandle.write( "RegionLeft%s=%s\n" % (curRegion, xstart) )
                                    fileHandle.write( "RegionRight%s=%s\n" % (curRegion, xend) )
                                    fileHandle.write( "RegionBottom%s=%s\n" % (curRegion, yend) )
                                    fileHandle.write( "RegionTop%s=%s\n" % (curRegion,ystart) )
                                    curRegion += 1
                    else:
                        fileHandle.write( "CurrentTile=%s\n" % jArnold )
                        fileHandle.write( "SingleAss=False\n" )
                        if jigsawEnabled:
                            xstart = jigsawRegions[j*4]
                            xend = jigsawRegions[j*4+1]
                            ystart = jigsawRegions[j*4+2]
                            yend = jigsawRegions[j*4+3]
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                        else:
                            curY = 0
                            curX = 0
                            jobNumberFound = False
                            tempJobNum = 0
                            for y in range(0, tilesInY):
                                for x in range(0, tilesInX):
                                    if tempJobNum == jMantra:
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
                        
                            fileHandle.write( "RegionLeft=%s\n" % xstart )
                            fileHandle.write( "RegionRight=%s\n" % xend )
                            fileHandle.write( "RegionBottom=%s\n" % ystart )
                            fileHandle.write( "RegionTop=%s\n" % yend )
                        
                fileHandle.close()
            
                arguments = []
                arguments.append( arnoldJobInfoFile )
                arguments.append( arnoldPluginInfoFile )
                if dialog.value( "submitscene.val" ):
                    arguments.append( hou.hipFile.path() )
                    
                jobResult = CallDeadlineCommand( arguments )
                jobId = "";
                resultArray = jobResult.split()
                for line in resultArray:
                    if line.startswith("JobID="):
                        jobId = line.replace("JobID=","")
                        break
                
                jobIds.append(jobId)
                
                print "---------------------------------------------------"
                print jobResult
                print "---------------------------------------------------"
    
        if innerTilesEnabled == 1 and dialog.value( "submitdependentassembly.val" ) == 1 and len(jobIds)>0:
            assemblyJobIds = []
            startFrame = 1
            startFrameParm = renderNode.parm( "f1" )
            if startFrameParm != None:
                startFrame = int(startFrameParm.eval())
                
            endFrame = 1
            endFrameParm = renderNode.parm( "f2" )
            if endFrameParm != None:
                endFrame = int(endFrameParm.eval())
                
            frameStep = 1
            frameStepParm = renderNode.parm( "f3" )
            if frameStepParm != None:
                frameStep = int(frameStepParm.eval())
            
            renderFrames = None
            if tilesSingleFrame:
                singleFrame = dialog.value( "tilessingleframe.val" )
                renderFrames = xrange( singleFrame, singleFrame + 1 )
            else:
                renderFrames = xrange(startFrame,endFrame+1,frameStep)
            
            jobName = dialog.value( "jobname.val" )
            jobName = "%s - %s - Assembly"%(jobName,job)
            
            # Create submission info file
            jobInfoFile = os.path.join(homeDir, "temp", "jigsaw_submit_info%d.job") % jobCount
            fileHandle = open( jobInfoFile, "w" )
            fileHandle.write( "Plugin=DraftTileAssembler\n" )
            fileHandle.write( "Name=%s\n" % jobName )
            fileHandle.write( "Comment=%s\n" % dialog.value( "comment.val" ) )
            fileHandle.write( "Department=%s\n" % dialog.value( "department.val" ) )
            fileHandle.write( "Pool=%s\n" % dialog.value( "pool.val" ) )
            fileHandle.write( "SecondaryPool=%s\n" % dialog.value( "secondarypool.val" ) )
            fileHandle.write( "Group=%s\n" % dialog.value( "group.val" ) )
            fileHandle.write( "Priority=%s\n" % dialog.value ( "priority.val" ) )
            fileHandle.write( "TaskTimeoutMinutes=%s\n" % dialog.value( "tasktimeout.val" ) )
            fileHandle.write( "EnableAutoTimeout=%s\n" % dialog.value( "autotimeout.val" ) )
            fileHandle.write( "ConcurrentTasks=%s\n" % dialog.value( "concurrent.val" ) )
            fileHandle.write( "MachineLimit=%s\n" % dialog.value( "machinelimit.val" ) )
            fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % dialog.value( "slavelimit.val" ) )
            fileHandle.write( "LimitGroups=%s\n" % dialog.value( "limits.val" ) )
            fileHandle.write( "JobDependencies=%s\n" % ",".join(jobIds) )
            fileHandle.write( "OnJobComplete=%s\n" % dialog.value( "onjobcomplete.val" ) )
            
            if dialog.value( "jobsuspended.val" ):
                fileHandle.write( "InitialStatus=Suspended\n" )

            if dialog.value( "isblacklist.val" ):
                fileHandle.write( "Blacklist=%s\n" % dialog.value( "machinelist.val" ) )
            else:
                fileHandle.write( "Whitelist=%s\n" % dialog.value( "machinelist.val" ) )
            
            #fileHandle.write( "Frames=0-%i\n" % (len(renderFrames)-1) )
           
            if tilesSingleFrame:
                fileHandle.write( "Frames=%s\n" % ( dialog.value( "tilessingleframe.val" ) ) )
            else:
                fileHandle.write( "Frames=%s\n" % GetFrameInfo( renderNode ) )
            
            fileHandle.write( "ChunkSize=1\n" )

            if ifdFile != "":
                fileHandle.write( "OutputDirectory0=%s\n" % os.path.dirname( ifdFile ) )
                if not ( ( dialog.value( "mantrajob.val" ) and isMantra ) or ( dialog.value( "arnoldjob.val" ) and isArnold ) ):
                    doShotgun = True
            elif paddedOutputFile != "":
                fileHandle.write( "OutputFilename0=%s\n" % paddedOutputFile )
                doDraft = True
                doShotgun = True

            fileHandle.write( "BatchName=%s\n" % (dialog.value( "jobname.val" ) ) ) 
            
            fileHandle.close()

            # Create plugin info file
            pluginInfoFile = os.path.join( homeDir, "temp", "jigsaw_plugin_info%d.job" % jobCount )
            fileHandle = open( pluginInfoFile, "w" )
            
            fileHandle.write( "ErrorOnMissing=%s\n" % (dialog.value( "erroronmissingtiles.val" ) == "1") )
            fileHandle.write( "ErrorOnMissingBackground=%s\n" % (dialog.value( "erroronmissingbackground.val" ) == "1") )
            
            fileHandle.write( "CleanupTiles=%s\n" % (dialog.value( "cleanuptiles.val" ) == "1") )
            fileHandle.write( "MultipleConfigFiles=%s\n" % True )
            
            fileHandle.close()
            
            configFiles = []
            
            for frame in renderFrames:
                
                output = GetOutputPath( renderNode )
                imageFileName = ""
                if output != "" and output != "COMMAND":
                    imageFileName = output.eval()
                else:
                    continue
                    
                tileName = ""
                outputName = ""
                paddingRegex = re.compile( "(#+)", re.IGNORECASE )
                matches = paddedNumberRegex.findall( imageFileName )
                if matches != None and len( matches ) > 0:
                    paddingString = matches[ len( matches ) - 1 ]
                    paddingSize = len( paddingString )
                    padding = str(frame)
                    while len(padding) < paddingSize:
                        padding = "0" + padding
                    
                    outputName = RightReplace( imageFileName, paddingString, padding, 1 )
                    padding = "_tile#_" + padding
                    tileName = RightReplace( imageFileName, paddingString, padding, 1 )
                else:
                    outputName = imageFileName
                    splitFilename = os.path.splitext(imageFileName)
                    tileName = splitFilename[0]+"_tile#_"+splitFilename[1]
                    
                # Create the directory for the config file if it doesn't exist.
                directory = os.path.dirname(imageFileName)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                
                fileName, fileExtension = os.path.splitext(imageFileName)
                
                date = time.strftime("%Y_%m_%d_%H_%M_%S")
                configFilename = fileName+"_"+str(frame)+"_config_"+date+".txt"
                fileHandle = open( configFilename, "w" )
                fileHandle.write( "\n" )
                
                fileHandle.write( "ImageFileName=" +outputName +"\n" )
                backgroundType = dialog.value( "backgroundoption.val" )
                
                if backgroundType == "Previous Output":
                    fileHandle.write( "BackgroundSource=" +outputName +"\n" )
                elif backgroundType == "Selected Image":
                    fileHandle.write( "BackgroundSource=" +dialog.value( "backgroundimage.val" ) +"\n" )
                
                if arnoldTilesEnabled:
                    renderWidth = cameraNode.parm("resx").eval()
                    renderHeight = cameraNode.parm("resy").eval()
                    fileHandle.write("ImageHeight=%s\n" % renderHeight)
                    fileHandle.write("ImageWidth=%s\n" % renderWidth)
                fileHandle.write( "TilesCropped=False\n" )
                
                if jigsawEnabled:
                    fileHandle.write( "TileCount=" +str( jigsawRegionCount ) + "\n" )
                else:
                    fileHandle.write( "TileCount=" +str( tilesInX * tilesInY ) + "\n" )
                fileHandle.write( "DistanceAsPixels=False\n" )
                
                currTile = 0
                if jigsawEnabled:
                    for region in range(0,jigsawRegionCount):
                        width = jigsawRegions[region*4+1]-jigsawRegions[region*4]
                        height = jigsawRegions[region*4+3]-jigsawRegions[region*4+2]
                        xRegion = jigsawRegions[region*4]
                        yRegion = jigsawRegions[region*4+2]
                        
                        regionOutputFileName = ""
                        matches = paddingRegex.findall( os.path.basename( tileName ) )
                        if matches != None and len( matches ) > 0:
                            paddingString = matches[ len( matches ) - 1 ]
                            paddingSize = len( paddingString )
                            padding = str(currTile)
                            while len(padding) < paddingSize:
                                padding = "0" + padding
                            regionOutputFileName = RightReplace( tileName, paddingString, padding, 1 )
                        
                        fileHandle.write( "Tile%iFileName=%s\n"%(currTile,regionOutputFileName) )
                        fileHandle.write( "Tile%iX=%s\n"%(currTile,xRegion) )
                        if arnoldTilesEnabled:
                            fileHandle.write( "Tile%iY=%s\n"%(currTile,1.0-yRegion-height) )
                        else:
                            fileHandle.write( "Tile%iY=%s\n"%(currTile,yRegion) )
                        fileHandle.write( "Tile%iWidth=%s\n"%(currTile,width) )
                        fileHandle.write( "Tile%iHeight=%s\n"%(currTile,height) )
                        currTile += 1
                    fileHandle.close()
                    configFiles.append(configFilename)
                else:
                    for y in range(0, tilesInY):
                        for x in range(0, tilesInX):
                            width = 1.0/tilesInX
                            height = 1.0/tilesInY
                            xRegion = x*width
                            yRegion = y*height
                            
                            regionOutputFileName = ""
                            matches = paddingRegex.findall( os.path.basename( tileName ) )
                            if matches != None and len( matches ) > 0:
                                paddingString = matches[ len( matches ) - 1 ]
                                paddingSize = len( paddingString )
                                padding = str(currTile)
                                while len(padding) < paddingSize:
                                    padding = "0" + padding
                                regionOutputFileName = RightReplace( tileName, paddingString, padding, 1 )
                            
                            fileHandle.write( "Tile%iFileName=%s\n"%(currTile,regionOutputFileName) )
                            fileHandle.write( "Tile%iX=%s\n"%(currTile,xRegion) )
                            if arnoldTilesEnabled:
                                fileHandle.write( "Tile%iY=%s\n"%(currTile,1.0-yRegion-height) )
                            else:
                                fileHandle.write( "Tile%iY=%s\n"%(currTile,yRegion) )
                            fileHandle.write( "Tile%iWidth=%s\n"%(currTile,width) )
                            fileHandle.write( "Tile%iHeight=%s\n"%(currTile,height) )
                            currTile += 1
                    fileHandle.close()
                    configFiles.append(configFilename)
            
            arguments = []
            arguments.append( jobInfoFile )
            arguments.append( pluginInfoFile )
            arguments.extend( configFiles )
                
            jobResult = CallDeadlineCommand( arguments )
            
            jobId = "";
            resultArray = jobResult.split()
            for line in resultArray:
                if line.startswith("JobID="):
                    jobId = line.replace("JobID=","")
                    break
            
            jobIds = [jobId]
            
            print "---------------------------------------------------"
            print jobResult
            print "---------------------------------------------------"
    if autoDependencies:
        jobOrdering[job][0] = ",".join(jobIds)
    
    return jobResult
    
def SubmitJobCallback():
    global dialog, homeDir, jigsawThread
    jobs = []
    submissions = []
    jobOrdering = {}
    
    jobResult = ""
    jobCount = 0
    totalJobs = 0
    ropOption = ""
    localPaths = ""
    missingIFDPaths = ""
    ropOption = dialog.value("ropoption.val")
    
    jigsawRegions = []
    jigsawRegionCount = 0
    # Save the scene file
    if hou.hipFile.hasUnsavedChanges():
        if hou.ui.displayMessage( "The scene has unsaved changes and must be saved before the job can be submitted.\nDo you wish to save?", buttons=( "Yes" , "No" ), title="Submit Houdini To Deadline" ) == 0:
            hou.hipFile.save()
        else:
            return
    
    bypassNodes = ( int(dialog.value( "bypassDependencies.val" )) == 1 )
    
    # Find out how many jobs to do
    if ropOption == "Choose":
        jobs = []
        selectedROP = hou.node( dialog.value( "rop.val" ) )
        
         # If this is a merge ROP, we want its input ROPs.
        if selectedROP.type().description() == "Merge":
            for inputROP in GetROPsFromMergeROP( selectedROP, bypassNodes ):
                if inputROP.path() not in jobs:
                    jobs.append( inputROP.path() )
        else:
            if not bypassNodes or not selectedROP.isBypassed():
                if selectedROP.path() not in jobs:
                    jobs.append( selectedROP.path() )
        
        totalJobs = len(jobs)
        if totalJobs == 0:
            print "ERROR: Invalid ROPs selected"
            hou.ui.displayMessage( "There are no valid ROPs selected. Check to see if the selected nodes are being bypassed.", title="Submit Houdini To Deadline" )
            return
    else: 
        jobs = GetROPs( ropOption, bypassNodes )
        if not jobs:
            print "ERROR: Invalid ROPs selected"
            hou.ui.displayMessage( "There are no valid ROPs selected. Check to see if the selected nodes are being bypassed.", title="Submit Houdini To Deadline" )
            return
        else:
            totalJobs = len(jobs)
    
    if int(dialog.value( "automaticDependencies.val" )) ==1:
        for job in jobs:
            jobOrdering[job] = [""]
            jobOrdering[job].extend(InputRenderJobs( job, jobs) )
        
    if dialog.value( "tilesenabled.val" ) == 1:
        if dialog.value( "jigsawenabled.val" ) == 1:
            if jigsawThread is None:
                print "ERROR: Jigsaw window is not open"
                hou.ui.displayMessage( "In order to submit Jigsaw renders the Jigsaw window must be open.", title="Submit Houdini To Deadline" )
                return
            if not jigsawThread.isAlive() or jigsawThread.sockOut is None:
                print "ERROR: Jigsaw window is not open"
                hou.ui.displayMessage( "In order to submit Jigsaw renders the Jigsaw window must be open.", title="Submit Houdini To Deadline" )
                return
            
            jigsawRegions = jigsawThread.getRegions()
            jigsawRegionCount = int(len(jigsawRegions)/4)
        
        if dialog.value( "tilessingleframeenabled.val" ) == 1:
            taskLimit = int(CallDeadlineCommand( ["-GetJobTaskLimit"] ))
            taskCount = jigsawRegionCount
            if dialog.value( "jigsawenabled.val" ) != 1:
                taskCount = int( dialog.value( "tilesinx.val" ) ) * int( dialog.value( "tilesiny.val" ) )
            if taskCount > taskLimit:
                print "Unable to submit job with " + (str(taskCount)) + " tasks.  Task Count exceeded Job Task Limit of "+str(taskLimit)
                hou.ui.displayMessage( "Unable to submit job with " + (str(taskCount)) + " tasks.  Task Count exceeded Job Task Limit of "+str(taskLimit) )
                return
        
        
    # check if the nodes are outputing to local
    for node in jobs:
        outputPath = GetOutputPath( hou.node( node ) )
        if outputPath != "" and outputPath != "COMMAND":
            if IsPathLocal( outputPath.eval() ):
                localPaths += "  %s  (output file)\n" % node
        renderNode = hou.node( node )
        
        if dialog.value( "tilesenabled.val" ) == 1:
            if dialog.value( "tilessingleframeenabled.val" ) != 1:
                if dialog.value( "jigsawenabled.val" ) == 0: 
                    tilesInX = int( dialog.value( "tilesinx.val" ) )
                    tilesInY = int( dialog.value( "tilesiny.val" ) )
                else:
                    tilesInX = jigsawRegionCount
                    tilesInY = 1
                totalJobs += (tilesInX * tilesInY) -1
                
            if dialog.value( "submitdependentassembly.val" ) == 1:
                totalJobs += 1
               
        ifdPath = GetIFD( renderNode )
        isMantra = (renderNode.type().description() == "Mantra")
        isArnold = (renderNode.type().description() == "Arnold")
        if ifdPath != None:
            if IsPathLocal( ifdPath.eval() ):
                localPaths += "  %s  (disk file)\n" % node
            
            if dialog.value( "mantrajob.val" ) == 1 and dialog.value( "localmantraexport.val" ) != 1 and isMantra:
                totalJobs += 1
                        
            if dialog.value( "arnoldjob.val" ) == 1 and dialog.value( "localarnoldexport.val" ) != 1 and isArnold:
                totalJobs += 1
            
        else:
            missingIFDPaths += "  %s  \n" % node

    if localPaths != "":
        if hou.ui.displayMessage( "The following ROPs have local output/disk paths. Do you wish to continue?\n\n%s" % localPaths, buttons=( "Yes" , "No" ), title="Submit Houdini To Deadline" ) != 0:
            WriteStickySettings()
            SaveSceneFields()
            return

    if missingIFDPaths != "" and dialog.value( "mantrajob.val" ):
        if hou.ui.displayMessage( "The Dependent Mantra Standalone job option is enabled, but the following ROPs don't have the Disk File option enabled to export IFD files. Do you wish to continue?\n\n%s" % missingIFDPaths, buttons=( "Yes" , "No" ), title="Submit Houdini To Deadline" ) != 0:
            WriteStickySettings()
            SaveSceneFields()
            return

    # check if draft template exists
    if dialog.value( "draftsubmit.val" ):
        if dialog.value("draftCustom.val") and (dialog.value( "drafttemplate.val" ) == "" or not os.path.exists( dialog.value( "drafttemplate.val" ) )):
            hou.ui.displayMessage( "ERROR: Trying to submit draft job without valid draft template", title="Submit Houdini To Deadline" )
            WriteStickySettings()
            SaveSceneFields()
            return
        elif dialog.value("draftCustom.val") and (os.path.exists( dialog.value( "drafttemplate.val" ) ) and IsPathLocal( dialog.value( "drafttemplate.val" ) ) and hou.ui.displayMessage( "Draft Template is local, continue?", buttons=( "Yes" , "No" ), title="Submit Houdini To Deadline" ) != 0):
                WriteStickySettings()
                SaveSceneFields()
                return

    #check if overriding frame range, and empty
    if dialog.value( "overrideframes.val" ) and dialog.value( "framelist.val" ).strip() == "":
        hou.ui.displayMessage( "ERROR: Overriding Frame List, but Frame List is empty, exiting", title="Submit Houdini To Deadline" )
        return
 
    WriteStickySettings()
    SaveSceneFields()
    
    # if no secondary pool is selected, get rid of the space
    if dialog.value( "secondarypool.val" ) == " ":
        dialog.setValue( "secondarypool.val", "" )
    # for job in jobs:
        # renderNode = hou.node( "/out/" + job )
        # isWedge = renderNode.type().description() == "Wedge"
        # if isWedge:
            # totalJobs += 1
            
    for job in jobs:
        jobResult = SubmitRenderJob(job, jobOrdering, jobCount, totalJobs, (totalJobs >1), jigsawRegionCount, jigsawRegions )
        
    if totalJobs > 1:
        dialog.setValue( "status.val", "100%: All " + str( totalJobs ) + " jobs submitted" )
        print "All %d jobs submitted\n" % totalJobs
        hou.ui.displayMessage( "All %d jobs submitted" % totalJobs, title="Submit Houdini To Deadline" )
    else:
        if jobResult == "":
            hou.ui.displayMessage( "Failed to submit job.  Check log window for more information.", title="Submit Houdini To Deadline" )
        else:
            dialog.setValue( "status.val", "100%: Job submitted" )
            print "Job submitted\n"
            hou.ui.displayMessage( jobResult, title="Submit Houdini To Deadline" )

def CloseDialogCallback():
    WriteStickySettings()
    SaveSceneFields()
    
    if jigsawThread is not None:
        if jigsawThread.isAlive():        
            jigsawThread.closeJigsaw()
    
    print "Closing Submission Dialog..."
    dialog.setValue( "dlg.val", 0 )

def SubmitToDeadline( root ): 
    global dialog, deadlineSettings, deadlineTemp, shotgunScript, homeDir, configFile, ftrackScript, scriptRoot
    
    scriptRoot = root
    
    # Save the scene file
    #if hou.hipFile.hasUnsavedChanges():
    #    if hou.ui.displayMessage( "Save changes to the following Houdini scene file?\n" + hou.hipFile.path(), buttons=( "Yes" , "No" ), title="Submit Houdini To Deadline" ) == 0:
    #        hou.hipFile.save()
    #    else:
    #        return
    
    homeDir = CallDeadlineCommand( ["-GetCurrentUserHomeDirectory",] )
    homeDir = homeDir.replace( "\r", "" ).replace( "\n", "" )
    
    # Need to strip off the last eol char, it wasn't a \n
    deadlineTemp = os.path.join( homeDir, "temp" )
    deadlineSettings = os.path.join( homeDir, "settings" )
    configFile = os.path.join( deadlineSettings, "houdini_py_submission.ini" )
    shotgunScript = os.path.join( root, "events", "Shotgun", "ShotgunUI.py" )
    ftrackScript = os.path.join( root, "submission", "FTrack","Main", "FTrackUI.py" )
    uiPath = os.path.join( root, "submission", "Houdini", "Main", "SubmitHoudiniToDeadline.ui" )
    print "Creating Submission Dialog..."
    dialog = hou.ui.createDialog( uiPath )
    
    if not InitializeDialog():
        return

    print "Initializing Callbacks..."
    Callbacks()
    ReadStickySettings()
    LoadSceneFileSubmissionSettings()
    
    LoadIntegrationSettings()
    ROPSelectionCallback()
    updateDisplay()
    dialog.setValue( "sgsubmit.val", False )

class JigsawThread(threading.Thread):
    sockIn = None
    sockOut = None
    tempFile = None
    savedRegions = ""
    usingWidth = 1
    usingHeight = 1
    driver = ""
    def run(self):
        #Create an input socket on an open port
        HOSTin = ''                 # Symbolic name meaning all available interfaces
        PORTin = self.get_open_port()              # Arbitrary non-privileged port
        self.sockIn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockIn.bind((HOSTin, PORTin))
        self.sockIn.listen(1)
        repo = CallDeadlineCommand(["-GetRepositoryRoot"]).rstrip()
        
        #in the main thread get a screen shot
        screenshot = self.getScreenshot()
        info = screenshot.split("=")
        #if the screenshot exists then continue else create the failed message and return
        draftPath = repo+os.sep+"draft"
        if len(info) == 1:
            self.failedScreenshot()
            return
            
        if platform.system() == "Linux":
            deadlineBin = os.environ['DEADLINE_PATH']
            newLDPath = deadlineBin+os.sep+"python"+os.sep+"lib"+os.pathsep+draftPath
            if "LD_LIBRARY_PATH" in os.environ:
                newLDPath = newLDPath + os.pathsep + os.environ["LD_LIBRARY_PATH"]
            os.environ["LD_LIBRARY_PATH"] = newLDPath
        elif platform.system() == "Darwin":
            draftPath = draftPath+os.sep+"Mac"
            deadlineBin = ""
            with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f: deadlineBin = f.read().strip()
            
            newDYLDPath = deadlineBin+os.sep+"python"+os.sep+"lib"+os.pathsep+draftPath
            if "DYLD_LIBRARY_PATH" in os.environ:
                newDYLDPath = newDYLDPath + os.pathsep + os.environ["DYLD_LIBRARY_PATH"]

            os.environ["DYLD_LIBRARY_PATH"] = newDYLDPath
            
        #Get deadlinecommand to execute a script and pass in a screenshot and the port to connect to.
        CallDeadlineCommand(["-executescript",repo+os.sep+"submission"+os.sep+"Jigsaw"+os.sep+"Jigsaw.py",str(PORTin),info[1], "True", "0", "0"], False, False)
        
        conn, addr = self.sockIn.accept()
        #wait to receive the a message with the port in which to connect to for outgoing messages
        data = recvData(conn)
        if not data:
            #If we do not get one return
            conn.close()
            return
        HostOut = 'localhost'
        PORTout = int(data)
        self.sockOut = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockOut.connect((HostOut, PORTout))
        #constantly listen 
        while 1:
            data = recvData(conn)
            #if we do not get data then exit
            if not data:
                break
            #otherwise split the data on =
            command = str(data).split("=")
            #if we got the command exit then break out of the loop
            if command[0].lower() == "exit":
                break
            #if we were told to get the screenshot then retrieve a screenshot and send it to the jigsaw ui
            elif command[0].lower() == "getscreenshot":
                screenshot = self.getScreenshot()
                if(not screenshot):
                    #cmds.confirmDialog(title="No Background", message="Unable to get background. Make sure that the viewport is selected.");
                    self.closeJigsaw()
                else:
                    self.sockOut.sendall(screenshot+"\n")
            #When we are told to fit the region
            elif command[0].lower() == "getselected":
                mode = 0#Vertex
                padding = 0 #percentage based padding
                if len(command)>1:
                    arguments=command[1].split(";")
                    arguments[0].split()
                    if arguments[0].lower() == "tight":
                        mode = 0#vertex
                    elif arguments[0].lower() == "loose":
                        mode = 1#boundingbox
                    padding = float(arguments[1])
                regions = self.getSelectedBoundingRegion(mode, padding)
                regionMessage = ""
                for region in regions:
                    if not regionMessage == "":
                        regionMessage+=";"
                    first = True
                    for val in region:
                        if not first:
                            regionMessage+=","
                        regionMessage += str(val)
                        first = False
                self.sockOut.sendall("create="+regionMessage+"\n")
            #when told to save the regions save them to the scene
            elif command[0].lower() == "saveregions":
                if not len(command)>1:
                    self.saveRegions("")
                else:
                    self.saveRegions(command[1])
            #when told to load the regions send the regions back to Jigsaw 
            elif command[0].lower() == "loadregions":
                regions = self.loadRegions()
                self.sockOut.sendall("loadregions="+regions+"\n")
            
        conn.close()
        try:
            os.remove(self.tempFile)
        except:
            pass
    #if we failed to get the screen shot the first time then let the user know.  This will be run on the main thread
    def failedScreenshot(self):
        pass
        #cmds.confirmDialog( title='Unable to open Jigsaw', message='Failed to get screenshot.\nPlease make sure the current Viewport is selected')
    def requestSave(self):
        self.sockOut.sendall("requestSave\n")
    #Save the regions to the scene
    def saveRegions(self, regions):
        try:
            currentNode = hou.node( "/out")
            regionData = []
            for region in regions.split(";"):
                data = region.split(",")
                if len(data) == 7:
                    regionData.append( str(float(data[0])/float(self.usingWidth)) )#XPos
                    regionData.append( str(float(data[1])/float(self.usingHeight)) )#YPos
                    regionData.append( str(float(data[2])/float(self.usingWidth)) )#Width
                    regionData.append( str(float(data[3])/float(self.usingHeight)) )#Height
                    regionData.append( data[4] )#tiles in x
                    regionData.append( data[5] )#tiles in y
                    regionData.append( data[6] )# enabled
            
            currentNode.setUserData("deadline_jigsawregions", ','.join(regionData) )
        except:
            print( "Could not write regions to scene" ) 
            print( traceback.format_exc() )

    #Create a string out of all of the saved regions and return them.
    def loadRegions(self):
        currentNode = hou.node( "/out")
        results = ""
        try:
            data = currentNode.userData("deadline_jigsawregions")
            if data != None:
                regionData = data.split(",")
                count = 0
                for i in range(0,len(regionData) / 7):
                    if not results == "":
                        results += ";"
                        
                    results += str( int( float(regionData[7*i]) * float(self.usingWidth) ) ) #XPos
                    results += "," + str( int( float(regionData[7*i+1]) * float(self.usingHeight) ) ) #YPos
                    results += "," + str( int( float(regionData[7*i+2]) * float(self.usingWidth) ) ) #Width
                    results += "," + str( int( float(regionData[7*i+3]) * float(self.usingHeight) ) ) #Height
                    results += "," + regionData[7*i+4] #tiles in x
                    results += "," + regionData[7*i+5] #tiles in y
                    results += "," + regionData[7*i+6] #enabled
                    
        except:
            print( "Could not read Jigsaw settings from scene" )
            print( traceback.format_exc() )
        return results
    
    #Get the Jigsaw UI to return all of the regions and return an array of the ints with the appropriate positions
    def getRegions(self, invert = True):
        self.sockOut.sendall("getrenderregions\n")
        data = recvData(self.sockOut)
        
        regionString = str(data)
        regionData = regionString.split("=")
        regions = []
        if regionData[0] == "renderregion" and len(regionData) >1:
            regionData = regionData[1]
            regionData = regionData.split(";")
            for region in regionData:
                coordinates = region.split(",")
                if len(coordinates) == 4:
                    regions.append( float(coordinates[0])/self.usingWidth )
                    regions.append( ( float(coordinates[0])+float(coordinates[2] ) )/self.usingWidth )
                    regions.append( 1.0 - (float(coordinates[1])+float(coordinates[3]))/self.usingHeight )
                    regions.append( 1.0 - float(coordinates[1])/self.usingHeight )
        return regions
    
    def getScreenshot(self):
        if self.tempFile is None:
            filename = str(uuid.uuid4())
            self.tempFile = tempfile.gettempdir()+os.sep+filename+".png"
        
        rop = hou.node( self.driver )
        camera = rop.parm( "camera" ).eval()
        cameraNode = hou.node(camera)
        
        width = cameraNode.parm("resx").eval()
        height = cameraNode.parm("resy").eval()
        
        panel = hou.ui.curDesktop().createFloatingPanel(hou.paneTabType.SceneViewer)
        viewer = panel.paneTabOfType(hou.paneTabType.SceneViewer)
        desktop_name = hou.ui.curDesktop().name()
        pane_name = viewer.name()
        viewport_name = viewer.curViewport().name()
        full_sceneviewer_path = "%s.%s.world.%s" % (desktop_name, pane_name, viewport_name)
        hou.hscript('viewcamera -c '+camera+' ' + full_sceneviewer_path )
        panel.setSize((width+38, height+85))
        
        hou.hscript('viewwrite '+full_sceneviewer_path+' "'+self.tempFile+'"')
        
        panel.close()
        
        modelWidth = width
        modelHeight = height
        
        renderWidth = width
        renderHeight = height
        
        if renderWidth < modelWidth and renderHeight<modelHeight:
            self.usingWidth = renderWidth
            self.usingHeight = renderHeight
        else:
            renderRatio = renderWidth/(renderHeight+0.0)
            widthRatio = renderWidth/(modelWidth+0.0)
            heightRatio = renderHeight/(modelHeight+0.0)
            if widthRatio<=1 and heightRatio<=1:
                self.usingWidth = renderWidth
                self.usingHeight = renderHeight
            elif widthRatio > heightRatio:
                self.usingWidth = int(modelWidth)
                self.usingHeight = int(modelWidth/renderRatio)
            else:
                self.usingWidth = int(modelHeight*renderRatio)
                self.usingHeight = int(modelHeight)
               
        return "screenshot="+self.tempFile
    
    #Let jigsaw know that we want it to exit.
    def closeJigsaw(self):
        self.sockOut.sendall("exit\n")
    
    #get the bounding regions of all of the selected objects
    #Mode = False: Tight vertex based bounding box
    #Mode = True: Loose Bounding box based
    def getSelectedBoundingRegion(self, mode=False, padding = 0.0):
        
        rop = hou.node( self.driver )
        camera = rop.parm( "camera" ).eval()
        cameraNode = hou.node(camera)
        
        width = cameraNode.parm("resx").eval()
        height = cameraNode.parm("resy").eval()
        
        panel = hou.ui.curDesktop().createFloatingPanel(hou.paneTabType.SceneViewer)
        viewer = panel.paneTabOfType(hou.paneTabType.SceneViewer)
        desktop_name = hou.ui.curDesktop().name()
        pane_name = viewer.name()
        viewport_name = viewer.curViewport().name()
        full_sceneviewer_path = "%s.%s.world.%s" % (desktop_name, pane_name, viewport_name)
        hou.hscript('viewcamera -c '+camera+' ' + full_sceneviewer_path )
        panel.setSize((width+38, height+85))
        
        regions = []
        try:
            node = hou.node( "/" )
            allNodes = node.allSubChildren()
            for selectedNode in allNodes:
                minX = 0
                maxX = 0
                minY = 0
                maxY = 0
                if selectedNode.isSelected() and selectedNode.type().name() == "geo":
                    if not mode: #Tight vertex based
                        selectedGeometry = selectedNode.displayNode().geometry()
                        firstPoint = True
                        for point in selectedGeometry.iterPoints():
                            newPos =  point.position() * selectedNode.worldTransform()
                            mappedPos = hou.ui.floatingPanels()[-1].paneTabs()[0].curViewport().mapToScreen(newPos)
                            if firstPoint:
                                firstPoint = False
                                minX = mappedPos[0]
                                minY = mappedPos[1]
                            
                            if mappedPos[0] < minX:
                                minX = mappedPos[0]
                            if mappedPos[0] > maxX:
                                maxX = mappedPos[0]
                            if mappedPos[1] < minY:
                                minY = mappedPos[1]
                            if mappedPos[1] > maxY:
                                maxY = mappedPos[1]
                    else: #Loose bounding box based
                        boundingBox = selectedNode.displayNode().geometry().boundingBox()
                        firstPoint = True
                        minvec = boundingBox.minvec()
                        maxvec = boundingBox.maxvec()
                        xVals = [ minvec[0], maxvec[0] ]
                        yVals = [ minvec[1], maxvec[1] ]
                        zVals = [ minvec[2], maxvec[2] ]
                        
                        for x in xVals:
                            for y in yVals:
                                for z in zVals:
                                    newPos =  hou.Vector3( (x, y, z) ) * selectedNode.worldTransform()
                                    mappedPos = hou.ui.floatingPanels()[-1].paneTabs()[0].curViewport().mapToScreen(newPos)
                                    if firstPoint:
                                        firstPoint = False
                                        minX = mappedPos[0]
                                        minY = mappedPos[1]
                                    
                                    if mappedPos[0] < minX:
                                        minX = mappedPos[0]
                                    if mappedPos[0] > maxX:
                                        maxX = mappedPos[0]
                                    if mappedPos[1] < minY:
                                        minY = mappedPos[1]
                                    if mappedPos[1] > maxY:
                                        maxY = mappedPos[1]
                                        
                    regions.append([ int( minX + 0.5 ), int( height - maxY + 0.5 ), int( maxX - minX + 0.5 ), int( maxY -minY + 0.5 ) ])        
        finally:
            panel.close()
        
        return regions        
        
    #find a random open port to connect to
    def get_open_port(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        port = s.getsockname()[1]
        s.close()
        return port

def recvData(theSocket):
    totalData=[]
    data=''
    while True:
        data=theSocket.recv(8192)
        if not data:
            return
        if "\n" in data:
            totalData.append(data[:data.find("\n")])
            break
        totalData.append(data)
    return ''.join(totalData)

################################################################################
## DEBUGGING
################################################################################
#
# HOWTO: (1) Open Houdini's python shell: Alt + Shift + P   or   Windows --> Python Shell
#        (2) Copy and paste line (A) to import this file (MAKE SURE THE PATH IS CORRECT FOR YOU)
#        (3) Copy and paste line (B) to execute this file for testing
#        (4) If you change this file, copy and paste line (C) to reload this file, GOTO step (3)
#
# (A)
# root = "C:/DeadlineRepository7/";import os;os.chdir(root + "submission/Houdini/Main/");import SubmitHoudiniToDeadline
#
# (B)
# SubmitHoudiniToDeadline.SubmitToDeadline(root)
#
# (C)
# reload(SubmitHoudiniToDeadline)