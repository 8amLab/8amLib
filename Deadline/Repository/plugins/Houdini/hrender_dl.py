import sys
import traceback
import os
import re

def setupTileOutput( file, tileNumber ):
    frameRegex = re.compile( "\$F", re.IGNORECASE )    
    matches = frameRegex.findall( file )
    if matches != None and len( matches ) > 0:
        paddingString = matches[ len( matches ) - 1 ]
        padding = "_tile"+str(tileNumber)+"_$F"
        file = RightReplace( file, paddingString, padding, 1 )
    else:
        paddedNumberRegex = re.compile( "([0-9]+)", re.IGNORECASE )
        matches = paddedNumberRegex.findall( file )
        if matches != None and len( matches ) > 0:
            paddingString = matches[ len( matches ) - 1 ]
            padding = "_tile"+str(tileNumber)+"_"+paddingString
            file = RightReplace( file, paddingString, padding, 1 )
        else:
            splitFilename = os.path.splitext(file)
            file = splitFilename[0]+"_tile"+str(tileNumber)+"_"+splitFilename[1]
        
    return file

def RightReplace( fullString, oldString, newString, occurences ):
    return newString.join( fullString.rsplit( oldString, occurences ) )    

try:
    args = sys.argv
    print( args )
    
    startFrame = 0
    endFrame = 0
    increment = 1
    # Parse the arguments
    if "-f" in args:
        frameIndex = args.index( "-f" )
        startFrame = int(args[ frameIndex + 1 ])
        endFrame = int(args[ frameIndex + 2 ])
        increment = int(args[ frameIndex + 3 ])
        print( "Start: " + str(startFrame) )
        print( "End: " + str(endFrame) )
        print( "Increment: " + str(increment) )
        
    resolution = ()
    if "-r" in args:
        resolutionIndex = args.index( "-r" )
        width = int( args[ resolutionIndex + 1 ] )
        height = int( args[ resolutionIndex + 2 ] )
        resolution = (width,height)
        print( "Width: " + str(width) )
        print( "Height: " + str(height) )
    
    ignoreInputs = False
    if "-g" in args:
        ignoreInputs = True
        print( "Ignore Inputs: True" )
    else:
        print( "Ignore Inputs: False" )
    
    if "-o" not in args:
        output = None
        ext = None
        print( "No output specified. Output will be handled by the driver" )
    else:
        outputIndex = args.index( "-o" )
        output = args[ outputIndex + 1 ]
        print( "Output: " + output )
    
    if "-i" not in args:
        ifd = None
    else:
        ifdIndex = args.index( "-i" )
        ifd = args[ ifdIndex + 1 ]
        print( "IFD: " + ifd )
    
    tileRender = False
    xStart = 0
    xEnd = 0
    yStart = 0
    yEnd = 0
    currTile = 0
    if "-t" in args:
        tileRender = True
        tileIndex = args.index( "-t" )
        currTile = int( args[ tileIndex + 1 ] )
        xStart = float( args[ tileIndex + 2 ] )
        xEnd = float( args[ tileIndex + 3 ] )
        yStart = float( args[ tileIndex + 4 ] )
        yEnd = float( args[ tileIndex + 5 ] )
        
    if "-wedgenum" not in args:
        wedgeNum = -1
    else:
        wedgeNumIndex = args.index("-wedgenum")
        wedgeNum = int(args[wedgeNumIndex + 1])
        print( "Wedge Number: "+str(wedgeNum))
    
    driverIndex = args.index( "-d" )
    driver = args[ driverIndex + 1 ]
    #if not driver.startswith( "/" ):
    #	driver = "/out/" + driver
    print( "Driver: " + driver )
    
    inputFile = args[ len(args) - 1 ]
    print( "Input File: " + inputFile )
    
    isSim = False
    sliceNum = 0
    trackerMachine = ""
    trackerPort = -1
    if "-s" in args:
        isSim = True
        sliceIndex = args.index("-s")
        sliceNum = int( args[ sliceIndex + 1 ] )
        trackerMachine = args[ sliceIndex + 2 ]
        trackerPort = int( args[ sliceIndex + 3 ] )
        
    # Print out load warnings, but continue on a successful load.
    try:
        hou.hipFile.load( inputFile )
    except hou.LoadWarning, e:
        print e
    
    # Get the output driver.
    rop = hou.node( driver )
    if rop == None:
        print( "Error: Driver \"" + driver + "\" does not exist" )
    else:
        if isSim:
            # Sim job, so update the sim control node and get the actual ROP for rendering.
            simControlName = rop.parm("hq_sim_controls").evalAsString()
            print( "Sim control node: " + simControlName )
            
            simControlNode = hou.node( simControlName )
            simControlNode.parm("visaddress").set( trackerMachine )
            simControlNode.parm("port").set( trackerPort )
            
            print( "Sim Tracker: " + trackerMachine )
            print( "Sim Port: " + str(trackerPort) )
            
            hou.hscript("setenv SLICE="+str(sliceNum))
            hou.hscript("varchange")
            print( "Sim slice: " + str(sliceNum) )
            
            rop = hou.node( rop.parm("hq_driver").eval() )
            startFrame = int(rop.evalParm("f1"))
            endFrame = int(rop.evalParm("f2"))
            increment = int(rop.evalParm("f3"))
    
        # Set the necessar IFD settings if exporting IFD files.
        if ifd != None:
            print( "Setting SOHO output mode to 1" )
            ifdExportParm = rop.parm( "soho_outputmode" )
            if ifdExportParm != None:
                ifdExportParm.set( 1 )
            
            print( "Setting SOHO disk file to " + ifd )
            ifdFilenameParm = rop.parm( "soho_diskfile" )
            if ifdFilenameParm != None:
                ifdFilenameParm.set( ifd )
        
        # Turn progress reporting on, and set the output path. The reason we set the output path here instead of
        # in the 'render' function below is that the 'render' function always seems to replace the $F padding with
        # frame 1. So the output for each frame always overwrites the previous.
        ropType = rop.type().name()
        print( "ROP type: " + ropType )
        
        wedgeNode = None
        
        isWedge = (ropType == "wedge")
        numTasks = 1
        
        #If this is a wedge rop we need to do some additional set up
        if isWedge:
            
            #Get the render rop and make sure the frame range is set correctly
            renderNode = hou.node(rop.parm("driver").eval())
            renderNode.parm("f1").set(startFrame)
            renderNode.parm("f2").set(endFrame)
            renderNode.parm("f3").set(increment)
            
            if (wedgeNum >= 0):
                #We are only using one wedge, set it up as such
                rop.parm("wrange").set(1)
                rop.parm("wedgenum").set(wedgeNum)
            else:
                #Do all the wedges for the frame range. We will use this scripts last call to render as the last wedge's render call,
                # so we just need to render the first n-1 wedges here and then set up the rop for the last render.
                numParams = rop.parm("wedgeparams").eval()
                random = rop.parm("random").eval()
                
                if random:
                    #We're using the random settings
                    numRandom = rop.parm("numrandom").eval()
                    numTasks = numRandom * numParams
                    
                else:
                    #Using the number wedge params to determine task count
                    for i in range(1, numParams+1):
                        numTasks = numTasks * int(rop.parm("steps"+str(i)).eval())
                rop.parm("wrange").set(1)
                
            #Store the wedge rop for rendering later, set the output driver rop as the current rop to ensure
            #all our output and progress is tracked.
            wedgeNode = rop
            rop = renderNode
            ropType = rop.type().name()
        
        if ropType == 'rop_geometry':
            # Turn on Alfred-style progress reporting on Geo ROP.
            alf_prog_parm = rop.parm("alfprogress")
            if alf_prog_parm is not None:
                alf_prog_parm.set(1)
                
        elif ropType == 'geometry':
            alfredProgress = rop.parm( "alfprogress" )
            if alfredProgress != None:
                alfredProgress.set( 1 )
                print( "Enabled Alfred style progress" )
            
            reportNetwork = rop.parm( "reportnetwork" )
            if reportNetwork != None:
                reportNetwork.set( 1 )
                print( "Enabled network use reporting" )
            
            if tileRender:
                if output == None:
                    output = rop.parm( "sopoutput" ).unexpandedString()
                
                output = setupTileOutput( output, currTile )
                
            if output != None:
                outputFile = rop.parm( "sopoutput" )
                if outputFile != None:
                    outputFile.set( output )
        
        elif ropType == 'ifd':
            alfredProgress = rop.parm( "vm_alfprogress" )
            if alfredProgress != None:
                alfredProgress.set( 1 )
                print( "Enabled Alfred style progress" )
            
            verbosity = rop.parm( "vm_verbose" )
            if verbosity != None:
                verbosity.set( 3 )
                print( "Set verbosity to 3" )
                        
            if tileRender:
                if output == None:
                    output = rop.parm( "vm_picture" ).unexpandedString()
                
                output = setupTileOutput(output, currTile )
                
                ropTilesEnabled = rop.parm( "vm_tile_render" )
                if ropTilesEnabled != None:
                    ropTilesEnabled.set(0)
                    
            if output != None:
                outputFile = rop.parm( "vm_picture" )
                if outputFile != None:
                    outputFile.set( output )
            
        elif ropType == 'arnold':
            logToConsole = rop.parm( "ar_log_console_enable" )
            if logToConsole != None:
                logToConsole.set( 1 )
                print( "Enabled log to console" )
            
            logVerbosity = rop.parm( "ar_log_verbosity" )
            if logVerbosity != None:
                logVerbosity.set( 'detailed' )
                print( "Set verbosity to " + logVerbosity.eval() )
            
            if tileRender:
                if output == None:
                    output = rop.parm( "ar_picture" ).unexpandedString()
                
                output = setupTileOutput(output, currTile)
            
            if output != None:
                outputFile = rop.parm( "ar_picture" )
                if outputFile != None:
                    outputFile.set( output )
        
        elif ropType == "comp":
            if tileRender:
                if output == None:
                    output = rop.parm( "copoutput" ).unexpandedString()
                
                output = setupTileOutput( output, currTile )
                
            if output != None:
                outputFile = rop.parm( "copoutput" )
                if outputFile != None:
                    outputFile.set( output )
        
        elif ropType == "channel":
            if tileRender:
                if output == None:
                    output = rop.parm( "chopoutput" ).unexpandedString()
                
                output = setupTileOutput( output, currTile )
            
            if output != None:
                outputFile = rop.parm( "chopoutput" )
                if outputFile != None:
                    outputFile.set( output )
        
        elif ropType == "dop":
            if tileRender:
                if output == None:
                    output = rop.parm( "dopoutput" ).unexpandedString()
                
                output = setupTileOutput( output, currTile )
            
            if output != None:
                outputFile = rop.parm( "dopoutput" )
                if outputFile != None:
                    outputFile.set( output )
        
        elif ropType == "rib":
            if tileRender:
                if output == None:
                    output = rop.parm( "ri_display" ).unexpandedString()
                
                output = setupTileOutput( output, currTile )
                
            if output != None:
                outputFile = rop.parm( "ri_display" )
                if outputFile != None:
                    outputFile.set( output )
        elif ropType == "rop_alembic":
            if output != None:
                outputFile = rop.parm( "filename" )
                if outputFile != None:
                    outputFile.set( output )
                    
        if tileRender:
            camera = rop.parm( "camera" ).eval()
            cameraNode = hou.node(camera)
                        
            cropLeft = cameraNode.parm( "cropl" )
            if cropLeft != None:
                cropLeft.set( xStart )
            
            cropRight = cameraNode.parm( "cropr" )
            if cropRight != None:
                cropRight.set( xEnd )
            
            cropBottom = cameraNode.parm( "cropb" )
            if cropBottom != None:
                cropBottom.set( yStart )
            
            cropTop = cameraNode.parm( "cropt" )
            if cropTop != None:
                cropTop.set( yEnd )
        
        frameString = ""
        # Render the frames.
        if startFrame == endFrame:
            frameString = "frame " + str(startFrame)
        else:        
            frameString = "frame " + str(startFrame) + " to " + str(endFrame)
        
        if isWedge:
            rop = wedgeNode
            if wedgeNum == -1:
                #Do all the wedges for the frame range. We will use this scripts' last call to render as the last wedge's render call,
                # so we just need to render the first n-1 wedges here and then set up the rop for the last render.
                for i in range(0, (numTasks - 1)):
                    print( "Rendering wedge "+str(i)+" for "+frameString )
                    rop.parm("wedgenum").set(i)
                    rop.render( (startFrame,endFrame,increment), resolution, ignore_inputs=ignoreInputs )
                    
                #Since we looped to the second last, we need to set the wedge number for the last render call
                print( "Rendering wedge "+str(numTasks-1)+" for "+frameString )
                rop.parm("wedgenum").set(numTasks-1)
            else:
                #This is a single wedge job
                print( "Rendering wedge "+str(wedgeNum)+" for "+frameString )
        else:
            print( "Rendering "+frameString )
        
        #Renders the given rop. Renders the last wedge of a multi-wedge wedge job.
        rop.render( (startFrame,endFrame,increment), resolution, ignore_inputs=ignoreInputs )
        
        print( "Finished Rendering" )
except:
    print( "Error: Caught exception: " + str(traceback.format_exception(*sys.exc_info())[-2:]).strip().replace('\n',': ') )

