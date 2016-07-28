from image_graph import ImageGraph
import shutil
import exif
import os
import numpy as np
from PIL import Image, ImageTk
import tool_set 
from software_loader import Software
import tempfile
import plugins
import graph_rules

suffixes = [".jpg",".png",".tiff"]

def createProject(dir,notify=None,base=None):
    """ This utility function creates a ProjectModel given a directory.
        If the directory contains a JSON file, then that file is used as the project file.
        Otherwise, the directory is inspected for images.
        All images found in the directory are imported into the project.
        If the 'base' parameter is provided, the project is named based on that image name.
        If the 'base' parameter is not provided, the project name is set based on finding the
        first image in the list of found images, sorted in lexicographic order, starting with JPG, then PNG and then TIFF.
        Returns an error message upon error, otherwise None
    """

    if (dir.endswith(".json")):
       return ProjectModel(os.path.abspath(dir),notify=notify)
    selectionSet = [filename for filename in os.listdir(dir) if filename.endswith(".json")]
    if len(selectionSet) != 0 and base is not None:
        print 'Cannot add base image to an existing project'
        return None
    if len(selectionSet) == 0 and base is None:
       print 'No project found and base image not provided; Searching for a base image'
       suffixPos = 0
       while len(selectionSet) == 0 and suffixPos < len(suffixes):
          suffix = suffixes[suffixPos]
          selectionSet = [filename for filename in os.listdir(dir) if filename.endswith(suffix)]
          selectionSet.sort()
          suffixPos+=1
       projectFile = selectionSet[0] if len(selectionSet) > 0 else None
       if projectFile is None:
         print 'Could not find a base image'
         return None
    # add base is not None
    elif len(selectionSet) == 0: 
       projectFile = os.path.split(base)[1]
    else:
       projectFile = selectionSet[0]
    projectFile = os.path.abspath(os.path.join(dir,projectFile))
    if not os.path.exists(projectFile):
      print 'Base project file ' + projectFile + ' not found'
      return None
    image = None
    if  not projectFile.endswith(".json"):
        image = projectFile
        projectFile = projectFile[0:projectFile.rfind(".")] + ".json"
    model=  ProjectModel(projectFile,notify=notify)
    if  image is not None:
       model.addImagesFromDir(dir,baseImageFileName=os.path.split(image)[1])
    return model

class Modification:
   operationName = None
   additionalInfo = ''
   category = None
   inputmaskpathname=None
   arguments = {}

   def __init__(self, name, additionalInfo, category=None,inputmaskpathname=None,arguments={}):
     self.additionalInfo  = additionalInfo
     self.operationName = name
     self.category = category
     self.inputmaskpathname = inputmaskpathname
     self.arguments = arguments

class ProjectModel:
    """
       A ProjectModel manages a project.  A project is made up of a directed graph of Image nodes and links.
       Each link is associated with a manipulation between the source image to the target image.  
       A link contains a mask(black and white) image file describing the changes.
       A mask's X&Y dimensions match the source image.
       A link contains a desciption of the manipulation operation, software used to perfrom the manipulation,
       analytic results comparing source to target images, and an input mask path name.  The input mask path name
       describes a mask used by the manipulation software as a parameter describing the manipulation.
       Links may be 'read-only' indicating that they are created through an automated plugin.

       A ProjectModel can be reused to open new projects.   It is designed to represent a view model (MVC).
       A ProjectModel has two state paremeters, 'start' and 'end', containing the name of image nodes in the graph.
       When both set, a link is selected.  When 'start' is set and 'end' is None, only a single image node is selected.
       Several methods on the ProjectModel depend on the state of these parameters.  For example, adding a new link
       to a image node, chooses the source node referenced by 'end' if set, otherwise it chooses the node referenced by 'start'
    """
  
    G = None
    start = None
    end = None

    def __init__(self, projectFileName, importImage=False, notify=None):
      self.G = ImageGraph(projectFileName)
      self._setup()
      self.notify = notify

    def get_dir(self):
       return self.G.dir

    def addImagesFromDir(self,dir,baseImageFileName=None,xpos=20,ypos=50):
       """
         Bulk add all images from a given directory into the project.
         Position the images in a grid, separated by 50 vertically with a maximum height of 520.
         Images are imported in lexicographic order, first importing JPG, then PNG and finally TIFF.
         If baseImageFileName, the name of an image node, is provided, then that node is selected
         upong completion of the operation.  Otherwise, the last not imported is selected"
       """
       initialYpos = ypos
       for suffix in suffixes:
         p = [filename for filename in os.listdir(dir) if filename.endswith(suffix) and not filename.endswith('_mask' + suffix)]
         p.sort()
         for filename in p:
             pathname = os.path.abspath(os.path.join(dir,filename))
             nname = self.G.add_node(pathname,xpos=xpos,ypos=ypos)
             ypos+=50
             if ypos == 520:
                 ypos=initialYpos
                 xpos+=20
             if filename==baseImageFileName:
               self.start = nname
               self.end = None

    def addImage(self, pathname):
       nname = self.G.add_node(pathname)
       self.start = nname
       self.end = None
       return nname

    def update_edge(self,mod,software=None):
        self.G.update_edge(self.start, self.end, \
            inputmaskpathname=mod.inputmaskpathname, \
            op=mod.operationName, \
            description=mod.additionalInfo, \
            softwareName=('' if software is None else software.name), \
            softwareVersion=('' if software is None else software.version))

    def compare(self, destination,seamAnalysis=True):
       """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
           Return both images, the mask and the analysis results (a dictionary)
       """
       im1 = self.getImage(self.start)
       im2 = self.getImage(destination)
       mask, analysis = tool_set.createMask(im1,im2, invert=False, seamAnalysis=seamAnalysis)
       return im1,im2,mask,analysis

    def getExifDiff(self):
      """ Return the EXIF differences between nodes referenced by 'start' and 'end' 
      """
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return e['exifdiff'] if 'exifdiff' in e else None

    def _compareImages(self,start,destination, invert=False):
       startIm,startFileName = self.getImageAndName(start)
       destIm,destFileName = self.getImageAndName(destination)
       mask,analysis = tool_set.createMask(startIm,destIm, invert=invert)
       maskname=start + '_' + destination + '_mask'+'.png'
       exifDiff = exif.compareexif(startFileName,destFileName)
       analysis = analysis if analysis is not None else {}
       analysis['exifdiff'] = exifDiff
       return maskname,mask, analysis

    def getNodeNames(self):
      return self.G.get_nodes()
      
    def getSoftware(self):
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return Software(e['softwareName'],e['softwareVersion'],'editable' in e and e['editable'] == 'no')

    def isEditableEdge(self,start,end):
      e = self.G.get_edge(start,end)
      return 'editable' not in e or e['editable'] == 'yes'

    def connect(self,destination,mod=Modification('Donor',''), software=None,invert=False, sendNotifications=True):
       """ Given a image node name, connect the new node to the end of the currently selected node.
            Create the mask, inverting the mask if requested.
            Send a notification to the register caller if requested.
            Return an error message on failure, otherwise return None
       """
       if self.start is None:
          return
       try:
         maskname, mask, analysis = self._compareImages(self.start,destination,invert=invert)
         if len(mod.arguments)>0:
            analysis['arguments'] = mod.arguments
         self.end = destination
         im = self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname, \
              inputmaskpathname=mod.inputmaskpathname, \
              op=mod.operationName,description=mod.additionalInfo, \
              editable='yes', \
              softwareName=('' if software is None else software.name), \
              softwareVersion=('' if software is None else software.version), \
              **analysis)
         if (self.notify is not None and sendNotifications):
            self.notify(mod)
         return None
       except ValueError, msg:
         return msg

    def addNextImage(self, pathname, img, invert=False, mod=Modification('',''), software=None, sendNotifications=True):
       """ Given a image file name and  PIL Image, add the image to the project, copying into the project directory if necessary.
            Connect the new image node to the end of the currently selected edge.  A node is selected, not an edge, then connect
            to the currently selected node.  Create the mask, inverting the mask if requested.
            Send a notification to the register caller if requested.
            Return an error message on failure, otherwise return None
       """
       if (self.end is not None):
          self.start = self.end
       destination = self.G.add_node(pathname, seriesname=self.getSeriesName(), image=img)
       try:
         maskname, mask, analysis = self._compareImages(self.start,destination,invert=invert)
         if len(mod.arguments)>0:
            analysis['arguments'] = mod.arguments
         self.end = destination
         im= self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname, \
              inputmaskpathname=mod.inputmaskpathname, \
              op=mod.operationName,description=mod.additionalInfo, \
              editable='no' if software.internal else 'yes', \
              softwareName=('' if software is None else software.name), \
              softwareVersion=('' if software is None else software.version), \
              **analysis)
         if (self.notify is not None and sendNotifications):
            self.notify(mod)
         return None
       except ValueError, msg:
         return msg

    def getSeriesName(self):
       """ A Series is the prefix of the first image node """
       if (self.start is None):
          None
       startNode = self.G.get_node(self.start)
       suffix = None
       if (startNode.has_key('seriesname')):
         suffix = startNode['seriesname']
       if (self.end is not None):
          endNode = self.G.get_node(self.end)
          if (endNode.has_key('seriesname')):
            suffix = startNode['seriesname']
       return suffix

    def getName(self):
     return self.G.get_name()

    def startImageName(self):
      return self.start if self.start is not None else ""
    
    def nextImageName(self):
      return self.end if self.end is not None else ""

    def undo(self):
       """ Undo the last graph edit """
       self.start = None
       self.end = None
       self.G.undo()

    def select(self,edge):
      self.start= edge[0]
      self.end = edge[1]

    def startNew(self,imgpathname):
       """ Inititalize the ProjectModel with a new project given the pathname to a base image file in a project directory """
       projectFile = imgpathname[0:imgpathname.rfind(".")] + ".json"
       self.G = ImageGraph(projectFile)
       self.addImagesFromDir(os.path.split(imgpathname)[0],baseImageFileName=os.path.split(imgpathname)[0])

    def load(self,pathname):
       """ Load the ProjectModel with a new project/graph given the pathname to a JSON file in a project directory """
       # Historically, the JSON was used instead of the project directory as a project since the tool cannot control the content of directory
       self.G.load(pathname)
       self.start = None
       self.end = None
       self._setup()

    def _setup(self):
       n = self.G.get_nodes()
       if (len(n) > 0):
           self.start = n[0]
           s = self.G.successors(n[0])
           if (len(s) > 0):
              self.end = s[0]
           else:
              p = self.G.predecessors(n[0])
              if (len(p)>0):
                 self.start = p[0]
                 self.end = n[0]

    def saveas(self,pathname):
       self.G.saveas(pathname)

    def save(self):
       self.G.save()

    def getDescription(self):
       if (self.start is None or self.end is None):
          return None
       edge = self.G.get_edge(self.start, self.end)
       if edge is not None:
          return Modification(edge['op'],edge['description'], \
            inputmaskpathname=self.G.get_inputmaskpathname(self.start,self.end), \
            arguments = edge['arguments'] if 'arguments' in edge else {})
       return None

    def getImage(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'));
       return self.G.get_image(name)[0]

    def getImageAndName(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'));
       return self.G.get_image(name)

    def startImage(self):
       return self.getImage(self.start)

    def nextImage(self):
       return self.getImage(self.end)

    def maskImage(self):
       if (self.end is None):
           dim = (250,250,3) if self.start is None else self.getImage(self.start).size
           return Image.fromarray(np.zeros(dim).astype('uint8'));
       return self.G.get_edge_mask(self.start,self.end)

    def maskStats(self):
       if self.end is None:
          return ''
       edge = self.G.get_edge(self.start,self.end)
       if edge is None:
         return ''
       stat_names = ['ssim','psnr','username','shape change']
       return '  '.join([ key + ': ' + str(value) for key,value in edge.items() if key in stat_names ])

    def currentImage(self):
       if self.end is not None:
          return self.getImageAndName(self.end)
       elif self.start is not None:
          return self.getImageAndName(self.start)
       return None,None

    def selectImage(self,name):
      self.start = name
      self.end = None

    def selectEdge(self, start, end):
      self.start = start
      self.end = end

    def remove(self):
       """ Remove the selected node or edge """
       if (self.start is not None and self.end is not None):
           self.G.remove_edge(self.start, self.end)
           self.end = None
       else:
         name = self.start if self.end is None else self.end
         p = self.G.predecessors(self.start) if self.end is None else [self.start]
         self.G.remove(name, None)
         self.start = p[0] if len(p) > 0  else None
         self.end = None

    def getProjectData(self, item):
        return self.G.getDataItem(item)

    def setProjectData(self,item, value):
        self.G.setDataItem(item,value)

    def getVersion(self):
      """ Return the graph/software versio n"""
      return self.G.getVersion()

    def getGraph(self):
      return self.G

    def validate(self):
       """ Return the list of errors from all validation rules on the graph. """
           
       total_errors = []
       for node in self.G.get_nodes():
         if not self.G.has_neighbors(node):
             total_errors.append((node,node,node + ' is not connected to other nodes'))

       for frm,to in self.G.get_edges():
          edge = self.G.get_edge(frm,to)
          op = edge['op'] 
          errors = graph_rules.run_rules(op,self.G,frm,to)
          if len(errors) > 0:
              total_errors.extend( [(frm,to,frm + ' => ' + to + ': ' + err) for err in errors])
       return total_errors

    def imageFromPlugin(self,filter,im, filename, **kwargs):
      """
        Create a new image from a plugin filter.  
        This method is given the plugin name, PIL Image, the full pathname of the image and any additional parameters
        required by the plugin (name/value pairs).
        The name of the resulting image contains the prefix of the input image file name plus an additional numeric index.
        If requested by the plugin (return True), the Exif is copied from the input image to the resulting image.
        The method resolves the donor parameter's name to the donor's image file name.
        If a donor is used, the method creates a Donor link from the donor image to the resulting image node.
        If an input mask file is used, the input mask file is moved into the project directory.
        Prior to calling the plugin, the output file is created and populated with the contents of the input file for convenience.
        The filter plugin must update or overwrite the contents.
        The method returns an error message upon failure, otherwise None.
      """
      op = plugins.getOperation(filter)
      suffixPos = filename.rfind('.')
      suffix = filename[suffixPos:]
      preferred = plugins.getPreferredSuffix(filter)
      if preferred is not None:
          suffix = preferred
      target = os.path.join(tempfile.gettempdir(),self.G.new_name(os.path.split(filename)[1],suffix=suffix))
      shutil.copy2(filename, target)
      copyExif = plugins.callPlugin(filter,im,filename,target,**kwargs)
      msg = None
      if copyExif:
        msg = exif.copyexif(filename,target)
      description = Modification(op[0],filter + ':' + op[2],op[1])
      if 'inputmaskpathname' in kwargs:
         description.inputmaskpathname = kwargs['inputmaskpathname']
      sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
      software = Software(op[3],op[4],internal=True)
      description.arguments = {k:v for k,v in kwargs.iteritems() if k != 'donor' and k != 'sendNotifications' and k != 'inputmaskpathname'}
      msg2 = self.addNextImage(target,None,mod=description,software=software,sendNotifications=sendNotifications)
      if msg2 is not None:
          if msg is None:
             msg = msg2
          else:
             msg = msg + "\n" + msg2
      os.remove(target)
      return msg

    def scanNextImageUnConnectedImage(self):
       """Scan for an image node with the same prefix as the currently select image node. 
          Scan in lexicographic order.
          Exlude images that have neighbors.
          Return None if a image nodee is not found.
       """
       selectionSet = [node for node in self.G.get_nodes() if not self.G.has_neighbors(node) and node != self.start]
       selectionSet.sort()
       if (len(selectionSet) > 0):
           matchNameSet = [name for name in selectionSet if name.startswith(self.start)]
           selectionSet = matchNameSet if len(matchNameSet) > 0 else selectionSet
       return selectionSet[0] if len(selectionSet) > 0 else None

    def scanNextImage(self):
      """
         Scan for a file with the same prefix as the currently select image node. 
         Scan in lexicographic order.
         Exlude image files with names ending in _mask or image files that are already imported.
         Return None if a file is not found.
      """

      if (self.start is None):
         return None,None

      suffix = self.start
      seriesName = self.getSeriesName()
      if seriesName is not None:
         suffix = seriesName

      def filterFunction (file):
         return not self.G.has_node(os.path.split(file[0:file.rfind('.')])[1]) and not(file.rfind('_mask')>0)

      def findFiles(dir, preFix, filterFunction):
         set= [os.path.abspath(os.path.join(dir,filename)) for filename in os.listdir(dir) if (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(dir,filename)))]
         set.sort()
         return set
      
      nfile = None
      for file in findFiles(self.G.dir,suffix, filterFunction):
         nfile = file
         break
      return tool_set.openImage(nfile) if nfile is not None else None,nfile

    def openImage(self,nfile):
      im = None
      if nfile is not None and nfile != '':
          im = tool_set.openImage(nfile)
      return nfile,im

    def export(self, location):
      self.G.create_archive(location)

    def exporttos3(self, location):
      import boto3
      path = self.G.create_archive(tempfile.gettempdir())
      s3 = boto3.client('s3','us-east-1')
      BUCKET = location.split('/')[0].strip()
      DIR= location.split('/')[1].strip()
      print 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1] 
      s3.upload_file(path, BUCKET, DIR + '/' + os.path.split(path)[1])
      os.remove(path)

    def export_path(self, location):
      if self.end is None and self.start is not None:
         self.G.create_path_archive(location,self.start)
      elif self.end is not None:
         self.G.create_path_archive(location,self.end)

