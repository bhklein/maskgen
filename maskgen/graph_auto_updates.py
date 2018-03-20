# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import logging
from image_wrap import openImageFile,ImageWrapper
import numpy as np
from support import setPathValue ,getValue
import tool_set
import os
"""
Support functions for auto-updating journals created with older versions of the tool"
"""
def updateJournal(scModel):
    """
     Apply updates
     :param scModel: Opened project model
     :return: None. Updates JSON.
     @type scModel: ImageProjectModel
    """
    from collections import OrderedDict
    upgrades = scModel.getGraph().getDataItem('jt_upgrades')
    upgrades = upgrades if upgrades is not None else []
    gopLoader = scModel.gopLoader
    fixes = OrderedDict(
        [("0.3.1115", [_replace_oldops]),
         ("0.3.1213", [_fixQT, _fixUserName]),
         ("0.4.0101.8593b8f323", [_fixResize, _fixResolution]),
         ("0.4.0101.b4561b475b", [_fixCreator, _fixValidationTime]),
         ("0.4.0308.f7d9a62a7e", [_fixLabels]),
         ("0.4.0308.f7d9a62a7e", [_fixPasteSpliceMask]),
         ("0.4.0308.90e0ce497f", [_fixTransformCrop]),
         ("0.4.0308.adee798679", [_fixEdgeFiles, _fixBlend]),
         ("0.4.0308.db2133eadc", [_fixFileArgs]),
         ("0.4.0425.d3bc2f59e1", [_operationsChange1]),
         ("04.0621.3a5c9635ef", [_fixProvenanceCategory]),
         ("04.0720.415b6a5cc4", [_fixRANSAC, _fixHP]),
         ("04.0720.b0ec584b4e", [_fixInsertionST]),
         ("04.0810.546e996a36", [_fixVideoAudioOps]),
         ("04.0810.9381e76724", [_fixCopyST, _fixCompression]),
         ("0.4.0901.723277630c", [_fixFrameRate, _fixRaws]),
         ("0.4.1115.32eabae8e6", [_fixRecordMasInComposite]),
         ("0.4.1204.5291b06e59", [_addColor, _fixAudioOutput, _fixEmptyMask, _fixGlobal]),
         ("0.4.1231.03ad63e6bb", [_fixSeams]),
         ("0.5.0227.c5eeafdb2e", [_addColor256, _fixDescriptions]),
         ('0.5.0227.6d9889731b', [_fixPNGS]),
         ('0.5.0227.bf007ef4cd', [_fixTool])])
    versions= list(fixes.keys())
    # find the maximum match
    matched_versions = [versions.index(p) for p in upgrades if p in versions]
    if len(matched_versions) > 0:
        max_upgrade = max(matched_versions)
        # fix what is left
        fixes_needed = max_upgrade-len(versions) + 1
        if fixes_needed < 0:
            for id in fixes.keys()[fixes_needed:]:
                logging.getLogger('maskgen').info('Apply upgrade {}'.format(id))
                for fix in fixes[id]:
                    fix(scModel, gopLoader)
    #update to the max
    upgrades = fixes.keys()[-1:]
    if scModel.getGraph().getVersion() not in upgrades:
        upgrades.append(scModel.getGraph().getVersion())
    scModel.getGraph().setDataItem('jt_upgrades',upgrades,excludeUpdate=True)
    if scModel.getGraph().getDataItem('autopastecloneinputmask') is None:
        scModel.getGraph().setDataItem('autopastecloneinputmask','no')

def _fixPNGS(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    import glob
    import imghdr
    for png_file in glob.glob(os.path.join(os.path.abspath(scModel.get_dir()) , '*.png')):
        if imghdr.what(png_file) == 'tiff':
            openImageFile(png_file).save(png_file,format='PNG')


def _fixTool(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    summary = scModel.getProjectData('technicalsummary',default_value=scModel.getProjectData('technicalSummary'))
    scModel.setProjectData('technicalsummary',summary)
    description = scModel.getProjectData('projectdescription', default_value=scModel.getProjectData('projectDescription'))
    scModel.setProjectData('projectdescription', description)
    tool_name = 'jtui'
    if summary.lower().startswith('automate'):
        tool_name = 'jtproject'
    modifier_tools = [tool_name]
    #hasauto = False
    #for frm, to in scModel.getGraph().get_edges():
    #    edge = scModel.G.get_edge(frm, to)
    #    hasauto |= (getValue(edge,'automated',defaultValue='no') == 'yes')
    #if hasauto:
    #    modifier_tools.append('jtprocess')
    if scModel.getGraph().getDataItem('modifier_tools') is None:
        scModel.getGraph().setDataItem('creator_tool', tool_name)
        scModel.getGraph().setDataItem('modifier_tools', modifier_tools)



def _fixValidationTime(scModel,gopLoader):
    import time
    validationdate = scModel.getProjectData('validationdate')
    if validationdate is not None and len(validationdate) > 0:
        scModel.setProjectData('validationtime',time.strftime("%H:%M:%S"),excludeUpdate=True)

def _fixProvenanceCategory(scModel,gopLoader):
    from maskgen.graph_rules import  manipulationCategoryRule
    cat = scModel.getProjectData('manipulationcategory',default_value='')
    if cat is not None and cat.lower() == 'provenance':
        scModel.setProjectData('provenance','yes')
    else:
        scModel.setProjectData('provenance', 'no')
    scModel.setProjectData('manipulationcategory',manipulationCategoryRule(scModel,None))

def _updateEdgeHomography(edge):
    if 'RANSAC' in edge:
        value = edge.pop('RANSAC')
        if value == 'None' or value == 0 or value == '0':
            edge['homography'] = 'None'
        else:
            edge['homography'] = 'RANSAC-' + str(value)
        if 'Transform Selection' in edge and edge['Transform Selection'] == 'Skip':
            edge['homography'] = 'None'
        if 'sift_max_matches' in edge:
            edge['homography max matches'] = edge.pop('sift_max_matches')

def _addColor(scModel,gopLoader):
    scModel.assignColors()

def _addColor256(scModel, gopLoader):
    if len(scModel.getGraph().get_edges())>=256:
        scModel.assignColors()

def _fixHP(scModel,gopLoader):
    for nodename in scModel.getNodeNames():
        node= scModel.G.get_node(nodename)
        if 'HP' in node:
            node['Registered'] = node.pop('HP')

def _fixFrameRate(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        masks = edge['videomasks'] if 'videomasks' in edge else []
        for mask in masks:
            if 'rate' in mask:
                if type(mask['rate']) == list:
                    mask['rate'] = float(mask['rate'][0])
                elif mask['rate']<0:
                    mask['rate'] = float(mask['rate'])*1000.0

def _fixRANSAC(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        _updateEdgeHomography(edge)
        _updateEdgeHomography(args)
        if edge['op'] == 'Donor':
            edge['homography max matches'] = 20

def _fixRaws(scModel,gopLoader):
    if scModel.G.get_project_type()!= 'image':
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in [ 'OutputPng', 'Recapture'] and \
             'shape change' in edge and tool_set.toIntTuple(edge['shape change']) != (0,0):
            node = scModel.G.get_node(frm)
            file = os.path.join(scModel.get_dir(), node['file'])
            redo =  tool_set.fileType(file) == 'image' and \
                file.lower()[-3:] not in ['iff','tif','png','peg','jpeg','gif','pdf','bmp']
            node = scModel.G.get_node(to)
            file = os.path.join(scModel.get_dir(),node['file'])
            redo |= tool_set.fileType(file) == 'image' and \
                file.lower()[-3:] not in ['iff','tif','png','peg','jpeg','gif','pdf','bmp']
            if redo:
                scModel.select((frm,to))
                scModel.reproduceMask()

def _fixSeams(scModel,gopLoader):
    if scModel.G.get_project_type()!= 'image':
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in [ 'TransformSeamCarving'] and edge['softwareName'] == 'maskgen':
            bounds = getValue(edge,'arguments.percentage bounds')
            if  bounds is not None:
                edge['arguments'].pop('percentage bounds')
                edge['arguments']['percentage_width'] = float(bounds)/100.0
                edge['arguments']['percentage_height'] = float(bounds)/100.0
            keep  = getValue(edge, 'arguments.keepSize')
            if keep is not None:
                edge['arguments']['keep'] = 'yes' if keep == 'no' else 'no'
            mask =  getValue(edge,'inputmaskname')
            if mask is not None:
                try:
                    im = openImageFile(os.path.join(scModel.get_dir(),mask))
                    if im is not None:
                        oldmask = im.to_array()
                        newmask = np.zeros(oldmask.shape,dtype=np.uint8)
                        newmask[:,:,1] = oldmask[:,:,0]
                        newmask[:,:,0] = oldmask[:,:,1]
                        ImageWrapper(newmask).save(os.path.join(scModel.get_dir(),mask))
                except Exception as e:
                    logging.getLogger('maskgen').error('Seam Carve fix {} mask error {}'.format(mask,str(e)))

def _fixVideoAudioOps(scModel,gopLoader):
    groups = scModel.G.getDataItem('groups')
    if groups is None:
        groups = {}
    op_mapping = {
        'AudioPan':'AudioAmplify',
        'SelectFromFrames':'SelectRegionFromFrames',
        'ColorInterpolation':'ColorLUT'
    }
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in groups:
            ops = groups[edge['op']]
        else:
            ops = [edge['op']]
        for op in ops:
            if op in op_mapping:
                args = edge['arguments'] if 'arguments' in edge else dict()
                if len(ops) == 1:
                    edge['op'] = op_mapping[op]
                if 'chroma key insertion' in args:
                    args['key insertion'] = args.pop('chroma key insertion')
                if 'Left' in args:
                    args['Left Pan'] = args.pop('Left')
                if 'Right' in args:
                    args['Right Pan'] = args.pop('Right')
    newgroups = {}
    for k, v in groups.iteritems():
        newgroups[k] = [op_mapping[op] if op in op_mapping else op for op in v]
    scModel.G.setDataItem('groups', newgroups)

def _fixInsertionST(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        if 'Insertion Start Time' in args:
            args['Start Time'] = args.pop('Insertion Start Time')
        if 'Insertion End Time' in args:
            args['End Time'] = args.pop('Insertion End Time')

def _fixCompression(scModel,gopLoader):
    for nname in scModel.G.get_nodes():
        node = scModel.G.get_node(nname)
        if node['file'].endswith('_compressed.avi'):
            node['compressed'] = 'maskgen.video_tools.x264'

def _fixCopyST(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        if 'Copy Start Time' in args:
            args['Start Time'] = args.pop('Copy Start Time')
        if 'Copy End Time' in args:
            args['End Time'] = args.pop('Copy End Time')

def _operationsChange1(scModel,gopLoader):
    projecttype = scModel.G.getDataItem('projecttype')
    blur_type_mapping = {
        'AdditionalEffectFilterBlur':'Other',
        'AdditionalEffectFilterSmoothing':'Smooth',
        'FilterBlurMotion':'Motion',
        'AdditionalEffectFilterMedianSmoothing':'Median Smoothing',
    }
    laundering_type_mapping = {
        'AdditionalEffectFilterBlur': 'no',
        'AdditionalEffectFilterSmoothing': 'yes',
        'FilterBlurMotion': 'no',
        'AdditionalEffectFilterMedianSmoothing': 'yes',
    }
    fill_category_mapping = {
        'ColorFill': 'uniform color',
        'FillPattern': 'pattern',
        'FillPaintBucket': 'uniform color',
        'FillLocalRetouching': 'paint brush',
        'FillBackground': 'paint brush',
        'FillForeground': 'paint brush',
        'AdditionalEffectSoftEdgeBrushing': 'paint brush',
        'FillPaintBrushTool': 'paint brush'
    }
    source_mapping = {
        'ColorReplace': 'self',
        'ColorHue': 'other',
        'ColorMatch': 'self'
    }
    direction_mapping = {
        'ColorSaturation': 'increase',
        'ColorVibranceContentBoosting': 'increase',
        'IntensityDesaturate': 'decrease',
        'ColorVibranceReduction': 'decrease',
        'IntensityBrightness':'increase',
        'IntensityDodge':'increase',
        'IntensityHighlight':'increase',
        'IntensityLighten': 'increase',
        'IntensityDarken':'decrease',
        'IntensityBurn':'decrease'
        }
    noise_mapping = {
        'FilterBlurNoise': 'other',
        'AdditionalEffectFilterAddNoise': 'other'
    }
    op_mapping = {
        'AdditionalEffectAddLightSource':'ArtificialLighting',
        'ArtifactsCGIArtificialLighting':'ArtificialLighting',
        'AdditionalEffectFading':'Fading',
        'AdditionalEffectMosaic':'Mosaic',
        'AdditionalEffectReduceInterlaceFlicker':'ReduceInterlaceFlicker',
        'AdditionalEffectWarpStabilize':'WarpStabilize',
        'AdditionalEffectFilterBlur':'Blur',
        'AdditionalEffectFilterSmoothing':'Blur',
        'AdditionalEffectFilterMedianSmoothing':'Blur',
        'AdditionalEffectFilterSharpening':'Sharpening',
        'AdditionalEffectGradientEffect':'Gradient',
        'AdditionalEffectFilterAddNoise':'AddNoise',
        'FilterBlurNoise':'AddNoise',
        'AdditionalEffectSoftEdgeBrushing':'CGIFill',
        'FilterBlurMotion':'MotionBlur',
        'CreationFilterGT':'CreativeFilter',
        'ArtifactsCGIArtificialReflection':'ArtificialReflection',
        'ArtifactsCGIArtificialShadow':'ArtificialShadow',
        'ArtifactsCGIObjectCGI':'ObjectCGI',
        'ColorFill':'CGIFill',
        'ColorReplace':'Hue',
        'ColorHue':'Hue',
        'ColorMatch':'Hue',
        'ColorVibranceContentBoosting':'Vibrance',
        'ColorVibranceReduction':'Vibrance',
        'IntensityDesaturate':'Saturation',
        'ColorSaturation':'Saturation',
        'FillBackground':'CGIFill',
        'FillForeground':'CGIFill',
        'FillGradient':'Gradient',
        'FillPattern':'CGIFill',
        'FillPaintBrushTool':'CGIFill',
        'FillLocalRetouching':'CGIFill',
        'FillPaintBucket':'CGIFill',
        'FillContentAwareFill':'ContentAwareFill',
        'FilterCameraRawFilter':'CameraRawFilter',
        'FilterColorLUT':'ColorLUT',
        'IntensityBrightness':'Exposure',
        'IntensityDarken': 'Exposure',
        'IntensityLighten': 'Exposure',
        'IntensityHighlight': 'Exposure',
        'IntensityNormalization':'Normalization',
        'IntensityBurn': 'Exposure',
        'IntensityExposure':'Exposure',
        'IntensityDodge': 'Exposure',
        'IntensityLevels':'Levels',
        'IntensityContrast':'Contrast',
        'IntensityCurves':'Curves',
        'IntensityLuminosity':'Luminosity',
        'IntensityExposure': 'Exposure',
        'MarkupDigitalPenDraw':'DigitalPenDraw',
        'MarkupHandwriting':'Handwriting',
        'MarkupOverlayObject': 'OverlayObject',
        'MarkupOverlayText':'OverlayText',
        'AdditionalEffectAddTransitions':'AddTransitions'
    }
    groups = scModel.G.getDataItem('groups')
    if groups is None:
        groups = {}
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in groups:
            ops = groups[edge['op']]
        else:
            ops = [edge['op']]
        for op in ops:
            if op in blur_type_mapping:
                setPathValue(edge,'arguments.Blur Type', blur_type_mapping[op])
            if op in noise_mapping:
                setPathValue(edge, 'arguments.Noise Type', noise_mapping[op])
            if op in fill_category_mapping:
                setPathValue(edge,'arguments.Fill Category', fill_category_mapping[op])
            if op in laundering_type_mapping:
                setPathValue(edge,'arguments.Laundering', laundering_type_mapping[op])
            if op in direction_mapping:
                setPathValue(edge,'arguments.Direction', direction_mapping[op])
            if op in source_mapping:
                setPathValue(edge,'arguments.Source', source_mapping[op])
            if projecttype == 'video' and op == 'FilterBlurMotion':
                edge['op'] = 'MotionBlur'
            elif op in op_mapping and len(ops) == 1:
                edge['op'] = op_mapping[op]
        newgroups = {}
        for k,v in groups.iteritems():
            newgroups[k] = [op_mapping[op] if op in op_mapping else op for op in v]
        scModel.G.setDataItem('groups', newgroups)

def _pasteSpliceBlend(scModel,gopLoader):
    import copy
    from group_filter import GroupFilterLoader
    gfl = GroupFilterLoader()
    scModel.G.addEdgeFilePath('arguments.Final Image', 'inputmaskownership')
    grp = gfl.etGroup('PasteSpliceBlend')
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'pastemask'  in edge and edge['pastemask'] is not None:
            args = copy.copy(edge['arguments'])
            args['inputmaskname'] = os.path.joint(scModel.get_dir(),os.path.split(args['pastemask'])[1])
            args['Final Image'] = os.path.joint(scModel.get_dir(),scModel.G.get_node(to)['file'])
            donors = [pred for pred in scModel.G.predecessors() if pred != frm]
            if len(donors) > 0:
                args['donor'] = donors[0]
            args['sendNotifications'] = False
            mod = scModel.getModificationForEdge(frm,to,edge)
            scModel.imageFromGroup(grp, software=mod.software, **args)


def _fixColors(scModel,gopLoader):
    scModel.assignColors(scModel)

def _fixLabels(scModel,gopLoader):
    for node in scModel.getNodeNames():
        scModel.labelNodes(node)

def _fixFileArgs(scModel,gopLoader):
    #  add all the known file paths for now
    # rather than trying to find out which ones were actually used.
    scModel.G.addEdgeFilePath('arguments.XMP File Name','')
    scModel.G.addEdgeFilePath('arguments.qtfile', '')
    scModel.G.addEdgeFilePath('arguments.pastemask', '')
    scModel.G.addEdgeFilePath('arguments.PNG File Name', '')
    scModel.G.addEdgeFilePath('arguments.convolutionkernel', '')
    scModel.G.addEdgeFilePath('inputmaskname', 'inputmaskownership')
    scModel.G.addEdgeFilePath('selectmasks.mask', '')
    scModel.G.addEdgeFilePath('videomasks.videosegment', '')
    scModel.G.addNodeFilePath('compositemaskname', '')
    scModel.G.addNodeFilePath('donors.*', '')

def _fixEdgeFiles(scModel,gopLoader):
    import shutil
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'inputmaskname'  in edge and edge['inputmaskname'] is not None:
            edge['inputmaskname'] = os.path.split(edge['inputmaskname'])[1]
        arguments = edge['arguments'] if 'arguments' in edge  else None
        if arguments is not None:
            for id in ['XMP File Name','qtfile','pastemask','PNG File Name','convolutionkernel']:
                if id in arguments:
                   arguments[id] = os.path.split(arguments[id])[1]
                   fullfile = os.path.join('plugins/JpgFromCamera/QuantizationTables',arguments[id])
                   if os.path.exists(fullfile):
                       shutil.copy(fullfile,os.path.join(scModel.get_dir(),arguments[id]))

def _fixCreator(scModel,gopLoader):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    modifications = sorted(scModel.getDescriptions(), key=lambda mod: mod.ctime, reverse=False)
    if len(modifications) > 0:
       scModel.getGraph().setDataItem('creator',modifications[0].username,excludeUpdate=True)

def _fixLocalRotate(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'].lower() == 'transformrotate':
            tm = edge['transform matrix'] if 'transform matrix' in edge  else None
            sizeChange = tool_set.toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
            local = 'yes' if  tm is not  None and sizeChange == (0,0) else 'no'
            if 'arguments' not in edge:
                edge['arguments'] = {'local' : local}
            else:
                edge['arguments']['local']  = local
            if tm is None and  sizeChange == (0,0):
                if 'arguments' in edge and 'homography' in edge['arguments']:
                    edge['arguments'].pop('homography')
                scModel.reproduceMask(edge_id=(frm, to))

def _fixBlend(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'].lower() == 'blendhardlight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Hard Light'}
            else:
                edge['arguments']['mode']  = 'Hard Light'
        elif edge['op'].lower() == 'blendsoftlight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Soft Light'}
            else:
                edge['arguments']['mode']  = 'Soft Light'

def _fixTransformCrop(scModel,gopLoader):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TransformCrop':
            if 'location' not in edge or \
                edge['location'] == "(0, 0)":
                scModel.select((frm,to))
                try:
                    scModel.reproduceMask()
                except Exception as e:
                    'Failed repair of TransformCrop ' + frm + " to " + to + ": " + str(e)

def _fixResolution(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'scale'  in edge['arguments']:
            edge['arguments']['resolution'] = edge['arguments']['scale'].replace(':','x')

def _fixResize(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TransformResize':
            if 'arguments' not in edge:
                edge['arguments'] = {}
            if 'interpolation' not in edge['arguments']:
                edge['arguments']['interpolation']  = 'other'

def _fixPasteSpliceMask(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'PasteSplice':
            if 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                if 'arguments' not in edge:
                    edge['arguments']  = {}
                edge['arguments']['pastemask'] = edge['inputmaskname']
                edge.pop('inputmaskname')
                if 'inputmaskownership' in edge:
                    edge.pop('inputmaskownership')


def _fixUserName(scModel,gopLoader):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    if scModel.getGraph().getDataItem('username') is not None:
        scModel.getGraph().setDataItem('username',scModel.getGraph().getDataItem('username').lower())

def _fixQT(scModel,gopLoader):
    """
      :param scModel:
      :return:
      @type scModel: ImageProjectModel
      """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'QT File Name' in edge['arguments']:
            edge['arguments']['qtfile'] = os.path.split(edge['arguments']['QT File Name'])[1]
            edge['arguments'].pop('QT File Name')

def _fixTransforms(scModel,gopLoader):
    """
       Replace true value with  'yes'
       :param scModel: Opened project model
       :return: None. Updates JSON.
       @type scModel: ImageProjectModel
       """
    validatedby = scModel.getProjectData('validatedby')
    if  validatedby is not None and len(validatedby) > 0:
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in ['TransformContentAwareScale','TransformAffine','TransformDistort','TransformMove',
            'TransformScale','TransformShear','TransformSkew','TransformWarp'] and \
                'transform matrix' not in edge :
            scModel.select((frm,to))
            try:
               tool_set.forcedSiftAnalysis(edge,scModel.getImage(frm),scModel.getImage(to),scModel.maskImage(),
                                        linktype=scModel.getLinkType(frm,to))
            except Exception as e:
                logging.warning("Cannot fix SIFT transforms during upgrade: " + str(e))
                logging.warning("Transform not composed for link {} to {}".format( frm, to))

def _fixRecordMasInComposite(scModel,gopLoader):
    """
    Replace true value with  'yes'
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'true':
            edge['recordMaskInComposite'] = 'yes'
         op = gopLoader.getOperationWithGroups(edge['op'],fake=True)
         if op.category in ['Output','AntiForensic','Laundering']:
             edge['recordMaskInComposite'] = 'no'

def _fixGlobal(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = gopLoader.getOperationWithGroups(edge['op'],fake=True)
        if 'global' in edge and edge['global'] == 'yes' and "maskgen.tool_set.localTransformAnalysis" in op.analysisOperations:
            edge['global'] = 'no'

def _fixEmptyMask(scModel,gopLoader):
    import numpy as np
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'empty mask' not in edge and ('recordInCompositeMask' not in edge or edge['recordInCompositeMask'] == 'no') \
                and  'videomasks' not in edge:
            mask = scModel.G.get_edge_image(frm,to, 'maskname', returnNoneOnMissing=True)
            edge['empty mask'] = 'yes' if mask is None or np.all(mask == 255) else 'no'

def _fixAudioOutput(scModel,gopLoader):
    """
     Consolidate Audio Outputs
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if edge['op'] in ['OutputAIF','OutputWAV']:
             edge['op'] = 'OutputAudioPCM'
         elif edge['op'] in ['OutputM4']:
             edge['op'] = 'OutputAudioCompressed'
         if 'Start Time' in edge and edge['Start Time'] == '0':
             edge['Start Time'] = '00:00:00'


def _fixSeam(scModel,gopLoader):
    """
   Seam Carving is recorded in Composite
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if edge['op'] == 'TransformSeamCarving':
             edge['recordMaskInComposite'] = 'yes'


def _replace_oldops(scModel,gopLoader):
    """
    Replace selected operations
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        oldOp = currentLink['op']
        if oldOp == 'ColorBlendDissolve':
            currentLink['op'] = 'Blend'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['mode'] = 'Dissolve'
        elif oldOp == 'ColorBlendMultiply':
            currentLink['op'] = 'Blend'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['mode'] = 'Multiply'
        elif oldOp == 'ColorColorBalance':
            currentLink['op'] = 'ColorBalance'
        elif oldOp == 'ColorMatchColor':
            currentLink['op'] = 'ColorMatch'
        elif oldOp == 'ColorReplaceColor':
            currentLink['op'] = 'ColorReplace'
        elif oldOp == 'IntensityHardlight':
            currentLink['op'] = 'BlendHardlight'
        elif oldOp == 'IntensitySoftlight':
            currentLink['op'] = 'BlendSoftlight'
        elif oldOp == 'FillImageInterpolation':
            currentLink['op'] = 'ImageInterpolation'
        elif oldOp == 'ColorBlendColorBurn':
            currentLink['op'] = 'IntensityBurn'
        elif oldOp == 'FillInPainting':
            currentLink['op'] = 'MarkupDigitalPenDraw'
        elif oldOp == 'FillLocalRetouching':
            currentLink['op'] = 'PasteSampled'
            currentLink['recordMaskInComposite'] = 'yes'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['purpose'] = 'heal'

def _fixDescriptions(scModel, gopLoader):
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if 'plugin_name' not in currentLink:
            continue
        plugin_name  = currentLink['plugin_name']
        if plugin_name == 'GammaCollection':
            setPathValue(currentLink,'arguments.selection type', 'auto')
        elif plugin_name == 'MajickConstrastStretch':
            setPathValue(currentLink,'arguments.selection type', 'NA')
        elif plugin_name == 'MajickEqualization':
            setPathValue(currentLink, 'arguments.selection type', 'NA')
            setPathValue(currentLink,'description',plugin_name + ': Equalize histogram: https://www.imagemagick.org/Usage/color_mods/#equalize.')
        elif plugin_name == 'GaussianBlur' and getValue(currentLink,'arguments.Laundering') is not None:
            setPathValue(currentLink, 'arguments.Laundering', 'no')
        elif plugin_name == 'ManualGammaCorrection':
            setPathValue(currentLink, 'arguments.selection type', 'manual')
            setPathValue(currentLink, 'description',
                                  plugin_name + ': Level gamma adjustment  (https://www.imagemagick.org/script/command-line-options.php#gamma)')

