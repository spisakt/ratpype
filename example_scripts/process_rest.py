import sys
sys.path.append("/opt/shared/bin/python")

import nipype.pipeline.engine as pe  # pypeline engine
import nipype.interfaces.fsl as fsl  # for fsl interfaces
import nipype.interfaces.io as nio  # for datasink
import mypype.workflows.stat.modelfit as model
import mypype.workflows.stat.easy_thres as thres
import mypype.workflows.preproc.preproc as prpr
import mypype.workflows.rest.reho as reho
import mypype.workflows as wf
import nipype.interfaces.afni as afni  # afni

from nipype.workflows.fmri.fsl import create_resting_preproc as compcor

import nipype.pipeline.server as server
########################################################################################################################
#
# _INPUT_ is a python script with a DataGrabber Node, which provides the following variables
# _FUNC_ : vector containing fMRI data files
# _STRUCT_: vector containing structural data files
# _SUBJECTS_: vector containing subject id's
#
########################################################################################################################
execfile("_INPUT_")

pipe = pe.Workflow('analysis_SGE')
pipe.base_dir = _BASE_DIR_

########################################################################################################################
# node for processing of anatomical data
anatproc = wf.bet.ratbet.anatproc("anatproc")
anatproc.inputs.inputspec.in_file = _STRUCT_
########################################################################################################################
# todo sink bet and reg



########################################################################################################################
# node for preprocessing of functional
preproc=prpr.func_preproc_fsl('preproc')
preproc.inputs.inputspec.in_file=_FUNC_
pipe.connect(anatproc, 'bet.outputspec.out_brain_mask', preproc, 'inputspec.anat_brain_mask')
#preproc.inputs.inputspec.anat_brain_mask='/opt/shared2/Altatos_study_2/analysis/anatproc/bet/rescale_y_mask/mapflow/_rescale_y_mask0/gems_Bold_20160406_01_newdims_rescaled_brain_brain_mask_rescaled.nii.gz'

########################################################################################################################
# node for compcor correction
compcor=prpr.t_compcor()
compcor.inputs.inputspec.num_noise_components = 6

pipe.connect(preproc, 'outputspec.preprocessed_func', compcor, 'inputspec.func')

datasink1 = pe.Node(nio.DataSink(), name='ccsink')
datasink1.inputs.base_directory = _BASE_DIR_
datasink1.container=_SUBJECTS_
#pipe.connect(compcor, 'outputspec.noise_components', datasink1, 'compcor')

bandpass_filter = pe.MapNode(fsl.TemporalFilter(), # TODO: into preprocess workflow
                          name='bandpass_filter',
                             iterfield=['in_file'])

bandpass_filter.inputs.highpass_sigma=100/(2*_TR_)
bandpass_filter.inputs.lowpass_sigma=12.5/(2*_TR_)
pipe.connect(compcor, 'outputspec.residual_file', bandpass_filter, 'in_file')

reho=reho.create_reho()
reho.inputs.inputspec.cluster_size = 27
pipe.connect(bandpass_filter, 'out_file', reho, 'inputspec.rest_res_filt')
pipe.connect(preproc, 'outputspec.func_brain_mask', reho, 'inputspec.rest_mask')

resample_reho = pe.MapNode(interface=afni.Resample(outputtype="NIFTI"),
                                iterfield=['master', 'in_file'],
                                name='resample_reho')

pipe.connect(reho, 'outputspec.raw_reho_map', resample_reho, 'in_file')
pipe.connect(anatproc, 'outputspec.out_brain', resample_reho, 'master')

applyWarpReho = pe.MapNode(interface=fsl.ApplyWarp(interp='sinc'), name="warp_reho",
                           iterfield=['in_file', 'field_file'])

applyWarpReho.inputs.ref_file='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'

pipe.connect(resample_reho, 'out_file', applyWarpReho, 'in_file')
pipe.connect(anatproc, 'outputspec.out_warpfield', applyWarpReho, 'field_file')

########################################################################################################################
# node for fitting glm model: 1st level
modelfit=model.modelfit_fsl("modelfit")
modelfit.inputs.inputspec.fwhm = _FWHM_
modelfit.inputs.inputspec.input_units = _TIME_UNITS_
modelfit.inputs.inputspec.TR = _TR_
modelfit.inputs.inputspec.high_pass_filter_cutoff = _HIGHPASS_
modelfit.inputs.inputspec.ev_file = _EVENT_FILES_
modelfit.inputs.inputspec.contrasts = _CONTRASTS_
modelfit.inputs.inputspec.bases_function = _BASIS_FUNC_
modelfit.inputs.inputspec.model_serial_correlations = _MODEL_SERIAL_CORR_
pipe.connect(preproc, 'outputspec.preprocessed_func', modelfit, 'inputspec.in_file')
pipe.connect(preproc, 'outputspec.func_brain_mask', modelfit, 'inputspec.brain_mask')
pipe.connect(compcor, 'outputspec.noise_components', modelfit, 'inputspec.confounders')
########################################################################################################################
# threshold individual statistical activation maps

###################

threshold=thres.easy_thres(modes=set(['uncorrected', 'voxel','cluster']))

pipe.connect(preproc, 'outputspec.example_func', threshold, 'inputspec.bg_image')
pipe.connect(preproc, 'outputspec.func_brain_mask', threshold, 'inputspec.mask')
pipe.connect(modelfit, 'outputspec.zstats', threshold, 'inputspec.z_stats')

########################################################################################################################
# Nodes for collecting results
substitutions = [('trait_added', '')] # bugfix?
regex_subs = [
    ('act-design/.*', 'act/design.png'),
    ('act-bg_image/.*', 'act/bg_image.nii.gz'),
    ('act-unthres/.*','act/zstat.nii.gz'),
    ('act-uncorr/.*', 'act/thres_uncorr_zstat.nii.gz'),
    ('act-clust/.*', 'act/thres_clust_zstat.nii.gz'),
    ('act-vox/.*', 'act/thres_vox_zstat.nii.gz'),
    #('act-tfce/.*', 'act/thres_tfce_zstat.nii.gz'),
    ('act-png-uncorr/.*', 'act/rendered_thres_uncorr.png'),
    ('act-png-clust/.*', 'act/rendered_thres_clust.png'),
    #('act-png-tfce/.*', 'act/rendered_thres_tfce.png'),
    ('act-png-vox/.*', 'act/rendered_thres_vox.png'),
    ('qc-motion/.*', 'qc/mc_displacement.png'),
]
sinkzstat = pe.MapNode(nio.DataSink(infields=['res.act-design',
                                              'res.act-bg_image',
                                              'res.act-unthres',
                                              'res.act-clust',
                                              'res.act-vox',
                                              'res.act-uncorr',
                                              #'res.act-tfce',
                                              'res.act-png-uncorr',
                                              'res.act-png-clust',
                                              #'res.act-png-tfce',
                                              'res.act-png-vox',
                                              'res.qc-motion'
                                              ],
                                    parameterization=False), name='sink_zstat',
                      iterfield=['container',
                                 'res.act-design',
                                 'res.act-bg_image',
                                 'res.act-unthres',
                                 'res.act-clust',
                                 'res.act-vox',
                                 'res.act-uncorr',
                                 #'res.act-tfce',
                                 'res.act-png-uncorr',
                                 'res.act-png-clust',
                                 #'res.act-png-tfce',
                                 'res.act-png-vox',
                                 'res.qc-motion'
                                 ]
                       )
sinkzstat.inputs.base_directory = _BASE_DIR_
sinkzstat.inputs.container = _SUBJECTS_
sinkzstat.inputs.substitutions = substitutions
sinkzstat.inputs.regexp_substitutions = regex_subs
pipe.connect(preproc, 'outputspec.example_func', sinkzstat, 'res.act-bg_image')
pipe.connect(modelfit, 'modelgen.design_image', sinkzstat, 'res.act-design')
pipe.connect(modelfit, 'outputspec.zstats', sinkzstat, 'res.act-unthres')
pipe.connect(threshold, 'outputspec.thres_uncorr_zstat', sinkzstat, 'res.act-uncorr')
pipe.connect(threshold, 'outputspec.thres_clust_zstat', sinkzstat, 'res.act-clust')
#pipe.connect(threshold, 'outputspec.thres_tfce_zstat', sinkzstat, 'res.act-tfce')
pipe.connect(threshold, 'outputspec.thres_vox_zstat', sinkzstat, 'res.act-vox')
pipe.connect(threshold, 'outputspec.rendered_thres_uncorr_image', sinkzstat, 'res.act-png-uncorr')
pipe.connect(threshold, 'outputspec.rendered_thres_clust_image', sinkzstat, 'res.act-png-clust')
#pipe.connect(threshold, 'outputspec.rendered_thres_tfce_image', sinkzstat, 'res.act-png-tfce')
pipe.connect(threshold, 'outputspec.rendered_thres_vox_image', sinkzstat, 'res.act-png-vox')
pipe.connect(preproc, 'outputspec.motion_plots', sinkzstat, 'res.qc-motionrot')
#pipe.connect(threshold, 'outputspec.rendered_thres_vox_image', sinkzstat, 'res.act-png-vox')
########################################################################################################################
# Do second-level analysis

groupmodelfit=model.modelfit_2ndlevel_fsl()
groupmodelfit.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
groupmodelfit.inputs.inputspec.std_brain_mask = '/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'
groupmodelfit.inputs.inputspec.num_copes=34

pipe.connect(modelfit, 'outputspec.copes', groupmodelfit, 'inputspec.copes')
pipe.connect(modelfit, 'outputspec.varcopes', groupmodelfit, 'inputspec.varcopes')
pipe.connect(anatproc, 'outputspec.out_brain', groupmodelfit, 'inputspec.anat_file')
pipe.connect(anatproc, 'outputspec.out_warpfield', groupmodelfit, 'inputspec.anat_to_std_warp')
########################################################################################################################
#threshold 2nd level results
threshold2nd=thres.easy_thres(modes=set(['uncorrected', 'voxel','cluster']), wf_name='threshold_second_level')
threshold2nd.inputs.inputspec.bg_image='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
threshold2nd.inputs.inputspec.mask='/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'
pipe.connect(groupmodelfit, 'outputspec.zstats', threshold2nd, 'inputspec.z_stats')

########################################################################################################################

#preproc.write_graph('preproc.dot', graph2use='colored');
#modelfit.write_graph('modelfit.dot', graph2use='colored');
#threshold_uncorr.write_graph('threshold_uncorr.dot', graph2use='colored');
#threshold_clust.write_graph('threshold_clust.dot', graph2use='colored');
#threshold_vox.write_graph('threshold_vox.dot', graph2use='colored');
#anatproc.write_graph('anatproc.dot', graph2use='colored');

########################################################################################################################
# Run pipeline
########################################################################################################################
pipe.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
pipe.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
pipe.write_graph('graph.dot', graph2use='colored');

#x=pipe.run(plugin='SGE', plugin_args=dict(template='/opt/shared/etc/conf/sgetemplate.sh', qsub_args='-q nipype -V -cwd'))
#x=pipe.run(plugin='SGEGraph', plugin_args={'template' : '/opt/shared/etc/conf/sgetemplate.sh','dont_resubmit_completed_jobs': True})
#x=pipe.run(plugin='MultiProc')
x=pipe.run()
#
#server.serve_content(pipe)
