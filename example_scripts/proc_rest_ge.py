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
import nipype.interfaces.io as nio
import mypype.interfaces.fsl as myfsl
import nipype.workflows.fmri.fsl.preprocess as prpc
import mypype.workflows.rest.centrality as cent
import nipype.interfaces.utility as util

from nipype.workflows.fmri.fsl import create_resting_preproc as compcor

import nipype.pipeline.server as server

def get_element(list, index):
	return list[index];

########################################################################################################################
#!/usr/bin/env python

########################################################################################################################
# INPUTS:
_BASE_DIR_='/opt/shared2/Altatos_study_2/'

_SUBJECTS_=\
[
's_2016032901_a01_iso',
's_2016040502_a02_iso',
's_2016033103_a03_iso',
's_2016032904_a04_iso',
's_2016040505_a05_iso',
's_2016033106_a06_iso',
's_2016040401_a07_iso',
's_2016033002_a08_iso',
's_2016040603_a09_iso',
's_2016040404_a10_iso',
's_2016033005_a11_iso',
's_2016040606_a12_iso',
's_2016040501_a01_med',
's_2016033102_a02_med',
's_2016032903_a03_med',
's_2016040504_a04_med',
's_2016033105_a05_med',
's_2016032906_a06_med',
's_2016040601_a07_med',
's_2016040402_a08_med',
's_2016033003_a09_med',
's_2016040506_a06_ipm',
's_2016033001_a07_ipm',
's_2016040602_a08_ipm',
's_2016040403_a09_ipm',
's_2016033004_a10_ipm',
's_2016040605_a11_ipm',
's_2016040406_a12_ipm'
]

# second-level input parameters
_REGRESSORS_=\
	dict(
		iso=[1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
		med=[0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
		ipm=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1]
	)

_CONTRASTS_ = 	[
		#['group mean', 'T',['ctr', 'vpa4', 'vpa6'],	[1,  1,  1]],
		['iso>med', 'T',['iso', 'med', 'ipm'],	[1, -1,  0]],
		['iso<med', 'T', ['iso', 'med', 'ipm'],	[-1, 1,  0]],
		['iso>ipm', 'T', ['iso', 'med', 'ipm'],	[1,  0, -1]],
		['iso<ipm', 'T', ['iso', 'med', 'ipm'],	[-1, 0,  1]],
		['med>ipm', 'T', ['iso', 'med', 'ipm'], [0, 1, -1]],
		['med<ipm', 'T', ['iso', 'med', 'ipm'], [0, -1, 1]]
	]

_GROUPS_=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

# fMRI 1st level analysis input pars
_FWHM_=12
_TR_=3
_TIME_UNITS_='secs'

########################################################################################################################
# DataGrabber collecting data
########################################################################################################################

pipe = pe.Workflow('analysis_rest_ge')
pipe.base_dir = _BASE_DIR_

datasource = pe.Node(nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct'], sort_filelist=False), name='01_grabData')
datasource.inputs.base_directory = _BASE_DIR_
datasource.inputs.template = '*'
datasource.inputs.field_template = dict(func=_BASE_DIR_ + '%s/epip*_rest_ge_*.nii',
                                        struct=_BASE_DIR_ + '%s/gems_*_02*.nii')
datasource.inputs.template_args = dict(func=[['subject_id']],
                                       struct=[['subject_id']])
datasource.inputs.subject_id = _SUBJECTS_

########################################################################################################################
# node for processing of anatomical data
anatproc = wf.bet.ratbet.anatproc("02_anatproc")
pipe.connect(datasource, 'struct', anatproc, 'inputspec.in_file')

########################################################################################################################
# todo sink bet and reg

########################################################################################################################
# node for preprocessing of functional
preproc=prpr.func_preproc_fsl('03_preproc')
anatproc.get_node('bet').get_node('bet').inputs.frac=0.65
anatproc.get_node('bet').get_node('bet').inputs.vertical_gradient=0.1
anatproc.get_node('bet').get_node('bet2').inputs.frac=0.5
anatproc.get_node('bet').get_node('bet2').inputs.vertical_gradient=0.1

pipe.connect(datasource, 'func', preproc, 'inputspec.in_file')
pipe.connect(anatproc, 'bet.outputspec.out_brain_mask', preproc, 'inputspec.anat_brain')
########################################################################################################################
# nodes to fix TR in header
getdim = pe.MapNode(interface=myfsl.utils.ImageInfo(), name="04_get_dim",  iterfield=['in_file'])
pipe.connect(preproc, 'outputspec.preprocessed_func', getdim, 'in_file')

changedim = pe.MapNode(myfsl.utils.ChangePixDim(), name="05_fixTR",
						   iterfield=['in_file',
									  'xdim',
									  'ydim',
									  'zdim',])
changedim.inputs.tdim=_TR_
pipe.connect(preproc, 'outputspec.preprocessed_func', changedim, 'in_file')
pipe.connect(getdim, 'out_pixdim1', changedim, 'xdim')
pipe.connect(getdim, 'out_pixdim2', changedim, 'ydim')
pipe.connect(getdim, 'out_pixdim3', changedim, 'zdim')

########################################################################################################################
# node for compcor correction
#compcor=prpr.t_compcor(wf_name='06_compcor')
#compcor.inputs.inputspec.num_noise_components = 6

#pipe.connect(changedim, 'out_file', compcor, 'inputspec.func')

########################################################################################################################
# median angle correction

from mypype.workflows.preproc.median_angle import create_median_angle_correction

medang=create_median_angle_correction()
medang.inputs.inputspec.target_angle=90

pipe.connect(changedim, 'out_file', medang, 'inputspec.subject')


########################################################################################################################
# node for bandpass filter
bandpass_filter = pe.MapNode(fsl.TemporalFilter(),  # TODO: into preprocess workflow
							 name='07_bandpass_filter',
							 iterfield=['in_file'])

bandpass_filter.inputs.highpass_sigma = 100 / (2 * _TR_)
bandpass_filter.inputs.lowpass_sigma = 12.5 / (2 * _TR_)
#pipe.connect(compcor, 'outputspec.residual_file', bandpass_filter, 'in_file')
pipe.connect(medang, 'outputspec.subject', bandpass_filter, 'in_file')

########################################################################################################################
# node for reho
reho = reho.create_reho(wf_name="08_reho")
reho.inputs.inputspec.cluster_size = 27
pipe.connect(bandpass_filter, 'out_file', reho, 'inputspec.rest_res_filt')
pipe.connect(preproc, 'outputspec.func_brain_mask', reho, 'inputspec.rest_mask')

########################################################################################################################
# get_zscore
#from CPAC.utils import get_zscore

zscore_reho=cent.get_zscore('reho',wf_name='Ztrans_reho')
pipe.connect(reho, 'outputspec.raw_reho_map', zscore_reho, 'inputspec.input_file')
pipe.connect(preproc, 'outputspec.func_brain_mask', zscore_reho, 'inputspec.mask_file')

########################################################################################################################
# smooth reho maps

smooth = prpc.create_susan_smooth("smooth_reho")
smooth.inputs.inputnode.fwhm=12.
#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???

pipe.connect(reho, 'outputspec.raw_reho_map', smooth, 'inputnode.in_files')
pipe.connect(preproc, 'outputspec.func_brain_mask', smooth, 'inputnode.mask_file')

########################################################################################################################
# smooth reho Z maps

smoothz = prpc.create_susan_smooth("smooth_reho_z")
smoothz.inputs.inputnode.fwhm=12.
#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???

pipe.connect(zscore_reho, 'outputspec.z_score_img', smoothz, 'inputnode.in_files')
pipe.connect(preproc, 'outputspec.func_brain_mask', smoothz, 'inputnode.mask_file')

########################################################################################################################
# permutation-test for ReHo

groupmodelfit=model.modelfit_2ndlevel("09_permutation_test_reho",method='randomise_parallel')
groupmodelfit.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
groupmodelfit.inputs.inputspec.std_brain_mask = '/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'

groupmodelfit.inputs.inputspec.regressors=_REGRESSORS_
groupmodelfit.inputs.inputspec.contrasts=_CONTRASTS_
groupmodelfit.inputs.inputspec.groups=_GROUPS_

pipe.connect(smooth, 'outputnode.smoothed_files', groupmodelfit, 'inputspec.copes')
pipe.connect(preproc, 'outputspec.func2anat_mat', groupmodelfit, 'inputspec.func2anat_mat')
pipe.connect(anatproc, 'outputspec.out_warpfield', groupmodelfit, 'inputspec.anat_to_std_warp')

########################################################################################################################
# permutation-test for ReHo Z-score

groupmodelfitz=model.modelfit_2ndlevel("09_permutation_test_reho_z",method='randomise_parallel')
groupmodelfitz.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
groupmodelfitz.inputs.inputspec.std_brain_mask = '/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'

groupmodelfitz.inputs.inputspec.regressors=_REGRESSORS_
groupmodelfitz.inputs.inputspec.contrasts=_CONTRASTS_
groupmodelfitz.inputs.inputspec.groups=_GROUPS_

pipe.connect(smoothz, 'outputnode.smoothed_files', groupmodelfitz, 'inputspec.copes')
pipe.connect(preproc, 'outputspec.func2anat_mat', groupmodelfitz, 'inputspec.func2anat_mat')
pipe.connect(anatproc, 'outputspec.out_warpfield', groupmodelfitz, 'inputspec.anat_to_std_warp')

########################################################################################################################
# compute eigenvector centrality

graph=cent.create_resting_state_graphs(wf_name='10_centrality', multipleTemplate=True)
#graph.inputs.centrality_options.method_options=[True, True]
#graph.inputs.inputspec.method_option=1
graph.get_node( "calculate_centrality").iterables=[('method_option', [0,1,2]),
												   ('threshold_option', [1,1,2]),
												   ('threshold', [0.3, 0.3,0.6])]
graph.get_node( "calculate_centrality").synchronize = True
#graph.inputs.inputspec.template = '/opt/shared/etc/std/new/standard-wistar_5mm_brain_mask.nii.gz'
#graph.inputs.inputspec.threshold=0.5
#graph.inputs.inputspec.threshold_option=1
graph.inputs.inputspec.weight_options=[False, True]

pipe.connect(bandpass_filter, 'out_file', graph, 'inputspec.subject')
pipe.connect(preproc, 'outputspec.func_brain_mask', graph, 'inputspec.template')

########################################################################################################################
# get fisrt element of results

get_element=pe.MapNode(interface=util.Function(input_names = ['list','index'],
								   output_names = ['out'],
								   function = get_element),
                                   name = 'get_element',
                                      iterfield=['list'])
get_element.inputs.index=0
pipe.connect(graph, 'outputspec.centrality_outputs', get_element, 'list')

copg = pe.MapNode(interface=fsl.CopyGeom(), name="copy_geom",
				   iterfield=['in_file', 'dest_file'])


pipe.connect(get_element, 'out', copg, 'dest_file')
pipe.connect(preproc, 'outputspec.func_brain_mask', copg, 'in_file')

########################################################################################################################
# get_zscore
#from CPAC.utils import get_zscore

zscore_cent=cent.get_zscore('cent',wf_name='Ztrans_cent')

pipe.connect(preproc, 'outputspec.func_brain_mask', zscore_cent, 'inputspec.mask_file')
pipe.connect(copg, 'out_file', zscore_cent, 'inputspec.input_file')


########################################################################################################################
# mult 100

mult100=pe.MapNode(interface=fsl.ImageMaths(op_string= '-mul 100'), name="mult_100",
				   iterfield=['in_file'])

pipe.connect(copg, 'out_file', mult100, 'in_file')

########################################################################################################################
# smooth centrality maps
smoothc = prpc.create_susan_smooth("11_smooth_centrality", separate_masks=True)
#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???
smoothc.inputs.inputnode.fwhm=12.

#pipe.connect(zscore, 'outputspec.z_score_img', smooth, 'inputnode.in_files')
pipe.connect(preproc, 'outputspec.func_brain_mask', smoothc, 'inputnode.mask_file')
#pipe.connect(get_element, 'out', smoothc, 'inputnode.in_files')
pipe.connect(mult100, 'out_file', smoothc, 'inputnode.in_files')

########################################################################################################################
# smooth centrality Z maps
smoothcz = prpc.create_susan_smooth("11_smooth_centrality_z", separate_masks=True)
#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???
smoothcz.inputs.inputnode.fwhm=12.

#pipe.connect(zscore, 'outputspec.z_score_img', smooth, 'inputnode.in_files')
pipe.connect(preproc, 'outputspec.func_brain_mask', smoothcz, 'inputnode.mask_file')
#pipe.connect(get_element, 'out', smoothc, 'inputnode.in_files')
pipe.connect(zscore_cent, 'outputspec.z_score_img', smoothcz, 'inputnode.in_files')

########################################################################################################################
# permutation-test for centrality

groupmodelfitc=model.modelfit_2ndlevel("12_permutation_test_centrality",method='randomise_parallel', standardize=True)
groupmodelfitc.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
groupmodelfitc.inputs.inputspec.std_brain_mask = '/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'

groupmodelfitc.inputs.inputspec.regressors=_REGRESSORS_
groupmodelfitc.inputs.inputspec.contrasts=_CONTRASTS_
groupmodelfitc.inputs.inputspec.groups=_GROUPS_

pipe.connect(smoothc, 'outputnode.smoothed_files', groupmodelfitc, 'inputspec.copes')
pipe.connect(preproc, 'outputspec.func2anat_mat', groupmodelfitc, 'inputspec.func2anat_mat')
pipe.connect(anatproc, 'outputspec.out_warpfield', groupmodelfitc, 'inputspec.anat_to_std_warp')

########################################################################################################################
# permutation-test for centrality

groupmodelfitcz=model.modelfit_2ndlevel("12_permutation_test_centrality_z",method='randomise_parallel', standardize=True)
groupmodelfitcz.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
groupmodelfitcz.inputs.inputspec.std_brain_mask = '/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz'

groupmodelfitcz.inputs.inputspec.regressors=_REGRESSORS_
groupmodelfitcz.inputs.inputspec.contrasts=_CONTRASTS_
groupmodelfitcz.inputs.inputspec.groups=_GROUPS_

pipe.connect(smoothcz, 'outputnode.smoothed_files', groupmodelfitcz, 'inputspec.copes')
pipe.connect(preproc, 'outputspec.func2anat_mat', groupmodelfitcz, 'inputspec.func2anat_mat')
pipe.connect(anatproc, 'outputspec.out_warpfield', groupmodelfitcz, 'inputspec.anat_to_std_warp')







########################################################################################################################
# Nodes for QC

png_bet = pe.MapNode(interface=fsl.Slicer(), name='png_bet',
                           iterfield=['in_file'])
png_bet.inputs.image_width = 1750
png_bet.inputs.all_axial = True
pipe.connect(anatproc, 'outputspec.out_brain', png_bet, 'in_file')

substitutions = [('trait_added', '')] # bugfix?
regex_subs = [
	('.*/trait_added', ''),
    ('mapflow/_qc_bet.*/s', 's'),
	('/bet/.*.png', '.png')
]
qc_bet = pe.MapNode(nio.DataSink(infields=['bet'
                                              ],
                                    parameterization=False), name='qc_bet',
                      iterfield=['container',
                                 'bet'
                                 ]
                       )

qc_bet.inputs.container = _SUBJECTS_
qc_bet.inputs.regexp_substitutions = regex_subs
pipe.connect(png_bet, 'out_file', qc_bet, 'bet')
#################
png_reg = pe.MapNode(interface=fsl.Slicer(), name='png_reganat',
					 iterfield=['in_file'])
png_reg.inputs.image_width = 1750
png_reg.inputs.all_axial = True
png_reg.inputs.image_edges='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
#png_reg.inputs.threshold_edges=-70
#png_reg.inputs.dither_edges=True
pipe.connect(anatproc, 'outputspec.out_nonlin_brain', png_reg, 'in_file')

substitutions = [('trait_added', '')] # bugfix?
regex_subs = [
	('.*/trait_added', ''),
    ('mapflow/_qc_reg.*/s', 's'),
	('/reg/.*.png', '.png')
]
qc_reg = pe.MapNode(nio.DataSink(infields=['reg'
                                              ],
                                    parameterization=False), name='qc_reganat',
                      iterfield=['container',
                                 'reg'
                                 ]
                       )
qc_reg.inputs.container = _SUBJECTS_
qc_reg.inputs.regexp_substitutions = regex_subs
pipe.connect(png_reg, 'out_file', qc_reg, 'reg')

#################
applyWarpExfunc = pe.MapNode(interface=fsl.ApplyWarp(interp='sinc'), name="warp_exfunc",
						   iterfield=['in_file', 'field_file', 'premat'])

applyWarpExfunc.inputs.ref_file='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'

pipe.connect(preproc, 'outputspec.func2anat_mat', applyWarpExfunc, 'premat')
pipe.connect(preproc, 'outputspec.example_func', applyWarpExfunc, 'in_file')
pipe.connect(anatproc, 'outputspec.out_warpfield', applyWarpExfunc, 'field_file')

png_regf = pe.MapNode(interface=fsl.Slicer(), name='png_regfunc',
					 iterfield=['in_file'])
png_regf.inputs.image_width = 1750
png_regf.inputs.all_axial = True
png_regf.inputs.image_edges='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz'
#png_reg.inputs.threshold_edges=-70
#png_reg.inputs.dither_edges=True
pipe.connect(applyWarpExfunc, 'out_file', png_regf, 'in_file')


substitutions = [('trait_added', '')] # bugfix?
regex_subs = [
	('.*/trait_added', ''),
    ('mapflow/_qc_reg.*/s', 's'),
	('/reg/.*.png', '.png')
]


qc_regf = pe.MapNode(nio.DataSink(infields=['reg'
                                              ],
                                    parameterization=False), name='qc_regfunc',
                      iterfield=['container',
                                 'reg'
                                 ]
                       )
qc_regf.inputs.container = _SUBJECTS_
qc_regf.inputs.regexp_substitutions = regex_subs
pipe.connect(png_regf, 'out_file', qc_regf, 'reg')

###############

substitutions = [('trait_added', '')] # bugfix?
regex_subs = [
	('trait_added', ''),
    ('mapflow/_qc_motion.*/s', 's'),
	('/mot/.*.png', '.png')
]

qc_mot = pe.MapNode(nio.DataSink(infields=['mot'
											],
								  parameterization=False), name='qc_motion',
					 iterfield=['container',
								'mot'
								]
					 )
qc_mot.inputs.container = _SUBJECTS_
qc_mot.inputs.regexp_substitutions = regex_subs
pipe.connect(preproc, 'outputspec.motion_plots', qc_mot, 'mot')


########################################################################################################################
















########################################################################################################################
########################################################################################################################
pipe.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
pipe.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
pipe.write_graph('graph.dot', graph2use='colored');
########################################################################################################################
x=pipe.run(plugin='SGE', plugin_args=dict(template='/opt/shared/etc/conf/sgetemplate.sh', qsub_args='-q nipype -V -cwd'))
#x=pipe.run(plugin='SGEGraph', plugin_args={'template' : '/opt/shared/etc/conf/sgetemplate.sh','dont_resubmit_completed_jobs': True})
#x=pipe.run()
########################################################################################################################
########################################################################################################################








