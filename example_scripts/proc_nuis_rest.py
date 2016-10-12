########################################################################################################################
#!/usr/bin/env python

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
import mypype.workflows.rest.centrality as cent

import nipype.interfaces.afni as afni  # afni
import nipype.interfaces.io as nio
import mypype.interfaces.fsl as myfsl
import nipype.workflows.fmri.fsl.preprocess as prpc
import mypype.workflows.rest.centrality as cent
import nipype.interfaces.utility as util

from nipype.workflows.fmri.fsl import create_resting_preproc as compcor

#import nipype.pipeline.server as server

########################################################################################################################
# INPUTS:
_BASE_DIR_='/opt/shared2/Autista_Modell1/'

_SUBJECTS_=\
[
's_2015042701_a5_ctr',
's_2015042704_a6_ctr',
's_2015042803_a7_ctr',
's_2015042805_a8_ctr',
's_2015042904_a14_ctr',
's_2015043002_a15_ctr',
's_2015043005_a17_ctr',
's_2015050403_a20_ctr',
's_2015050501_a51_ctr',
's_2015050504_a53_ctr',
's_2015050603_a55_ctr',
's_2015050702_a56_ctr',
's_2015042702_a60_vpa4',
's_2015042801_a61_vpa4',
's_2015042804_a62_vpa4',
's_2015042902_a63_vpa4',
's_2015042905_a64_vpa4',
's_2015043003_a65_vpa4',
's_2015050401_a66_vpa4',
's_2015050404_a73_vpa4',
's_2015050502_a74_vpa4',
's_2015050601_a75_vpa4',
's_2015050604_a77_vpa4',
's_2015050703_a78_vpa4',
's_2015042703_a25_vpa6',
's_2015042802_a26_vpa6',
's_2015042901_a27_vpa6',
's_2015042903_a28_vpa6',
's_2015043001_a29_vpa6',
's_2015043004_a32_vpa6',
's_2015050402_a33_vpa6',
's_2015050405_a34_vpa6',
's_2015050503_a36_vpa6',
's_2015050602_a35_vpa6',
's_2015050701_a79_vpa6',
's_2015050704_a80_vpa6'
]

# second-level input parameters
_REGRESSORS_=\
	dict(
		ctr=[1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
		vpa4=[0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
		vpa6=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1]
	)

_CONTRASTS_ = 	[
		['group mean', 'T',['ctr', 'vpa4', 'vpa6'],	[1,  1,  1]],
		['ctr>vpa4', 'T',['ctr', 'vpa4', 'vpa6'],	[1, -1,  0]],
		['ctr<vpa4', 'T', ['ctr', 'vpa4', 'vpa6'],	[-1, 1,  0]],
		['ctr>vpa6', 'T', ['ctr', 'vpa4', 'vpa6'],	[1,	 0, -1]],
		['ctr<vpa6', 'T', ['ctr', 'vpa4', 'vpa6'],	[-1, 0,  1]]
	]

_GROUPS_=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

# fMRI 1st level analysis input pars
_FWHM_=12
_TR_=3
_TIME_UNITS_='secs'

########################################################################################################################
# DataGrabber collecting data
########################################################################################################################

pipe = pe.Workflow('analysis_nuis_rest')
pipe.base_dir = _BASE_DIR_

datasource = pe.Node(nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct'], sort_filelist=False), name='01_grabData')
datasource.inputs.base_directory = _BASE_DIR_
datasource.inputs.template = '*'
datasource.inputs.field_template = dict(func=_BASE_DIR_ + '%s/epip_rest.nii.gz',
                                        struct=_BASE_DIR_ + '%s/gems_PD*AVG.nii.gz')
datasource.inputs.template_args = dict(func=[['subject_id']],
                                       struct=[['subject_id']])
datasource.inputs.subject_id = _SUBJECTS_

########################################################################################################################

"""
# INPUTS:
_BASE_DIR_='/opt/shared2/tests/resting/s_2016061702'

_FUNC_=\
[
#    "/opt/shared2/tests/resting/s_2016061702/epip_64x64_postproc_01__64x64_.nii",
#    "/opt/shared2/tests/resting/s_2016061702/epip_64x64_postproc_02__64x64_.nii"
    "/opt/shared2/tests/resting/s_2016061702/epip_96x96_postproc_01__96x96_.nii",
    "/opt/shared2/tests/resting/s_2016061702/epip_96x96_postproc_02__96x96_.nii"
]

_ANAT_=\
[
    "/opt/shared2/tests/resting/s_2016061702/gems_Bold_20160617_01__.nii",
    "/opt/shared2/tests/resting/s_2016061702/gems_Bold_20160617_01__.nii"
]

# fMRI 1st level analysis input pars
#_FWHM_=6
#_TR_=1.285 #64x64
_TR_=1.515 #96x96
_TIME_UNITS_='secs'
"""
########################################################################################################################


def process_rest(wf_name='proc_rest'):

	def get_element(list, index):
		return list[index];


	rest = pe.Workflow(wf_name)
	inputnode = pe.Node(interface=util.IdentityInterface(fields=['preprocessed_func','func_brain_mask']),name='inputspec')
	outputnode = pe.Node(interface=util.IdentityInterface(fields=['out']),
						 name='outputspec')

	########################################################################################################################
	# node for bandpass filter
	bandpass_filter = pe.MapNode(fsl.TemporalFilter(),  # TODO: into preprocess workflow
								 name='05_bandpass_filter_cc',
								 iterfield=['in_file'])

	#bandpass_filter.inputs.highpass_sigma = 100 / (2 * _TR_)
	#bandpass_filter.inputs.lowpass_sigma = 12.5 / (2 * _TR_)

	# 1. frequency band: 0.1-0.05 Hz
	# 2. frequency band: 0.05-0.02 Hz
	# 3. frequency band: 0.02-0.01 Hz
	# 4. frequency band: 0.01-0.002 Hz
	# 3. frequency band: 0.1-0.01 Hz # standard broadband

	bandpass_filter.iterables=[('highpass_sigma', [ 20/(2 * _TR_),	50/(2 * _TR_), 100/(2 * _TR_), 500/(2 * _TR_), 100/(2 * _TR_)]),
							   ('lowpass_sigma',  [ 10/(2 * _TR_),	20/(2 * _TR_), 50 /(2 * _TR_), 100/(2 * _TR_), 10 /(2 * _TR_)])]

	bandpass_filter.synchronize = True

	rest.connect(inputnode, 'preprocessed_func', bandpass_filter, 'in_file')
	#pipe.connect(changedim, 'out_file', bandpass_filter, 'in_file')

	########################################################################################################################
	# node for reho
	import mypype.workflows.rest.reho as reho
	reho = reho.create_reho(wf_name="06_reho_cc")
	reho.inputs.inputspec.cluster_size = 27
	rest.connect(bandpass_filter, 'out_file', reho, 'inputspec.rest_res_filt')
	rest.connect(inputnode, 'func_brain_mask', reho, 'inputspec.rest_mask')


	########################################################################################################################
	# smooth reho maps

	smooth = prpc.create_susan_smooth("08_smooth_reho_cc")
	smooth.inputs.inputnode.fwhm=12.
	#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???

	rest.connect(reho, 'outputspec.raw_reho_map', smooth, 'inputnode.in_files')
	rest.connect(inputnode, 'func_brain_mask', smooth, 'inputnode.mask_file')


	########################################################################################################################
	# compute centrality

	#graph=cent.create_resting_state_graphs(wf_name='07_centrality_cc', multipleTemplate=True)
	#graph.inputs.centrality_options.method_options=[True, True]
	#graph.inputs.inputspec.method_option=1
	#graph.get_node( "calculate_centrality").iterables=[('method_option', [0,1,2]),
	#												   ('threshold_option', [1,1,2]),
	#												   ('threshold', [0.3, 0.3,0.6])]
	#graph.get_node( "calculate_centrality").synchronize = True
	#graph.inputs.inputspec.template = '/opt/shared/etc/std/new/standard-wistar_5mm_brain_mask.nii.gz'
	#graph.inputs.inputspec.threshold=0.5
	#graph.inputs.inputspec.threshold_option=1
	#graph.inputs.inputspec.weight_options=[False, True]

	#rest.connect(bandpass_filter, 'out_file', graph, 'inputspec.subject')
	#rest.connect(inputnode, 'func_brain_mask', graph, 'inputspec.template')

	########################################################################################################################
	# get fisrt element of results

	#get_element=pe.MapNode(interface=util.Function(input_names = ['list','index'],
	#								   output_names = ['out'],
	#								   function = get_element),
	#								   name = 'get_element',
	#									  iterfield=['list'])
	#get_element.inputs.index=0
	#rest.connect(graph, 'outputspec.centrality_outputs', get_element, 'list')


	########################################################################################################################
	# smooth centrality maps

	#smoothc = prpc.create_susan_smooth("09_smooth_centrality_cc", separate_masks=True)
	#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???
	#smoothc.inputs.inputnode.fwhm=12.

	#rest.connect(inputnode, 'func_brain_mask', smoothc, 'inputnode.mask_file')
	#rest.connect(get_element, 'out', smoothc, 'inputnode.in_files')
	return rest

# pipe = pe.Workflow('test_nuis_96x96_multiband')
# pipe.base_dir = _BASE_DIR_

########################################################################################################################
########################################################################################################################
# node for processing of anatomical data
anatproc = wf.bet.ratbet.anatproc("03_anatproc")
#anatproc.inputs.inputspec.in_file=_ANAT_
pipe.connect(datasource, 'struct', anatproc, 'inputspec.in_file')

########################################################################################################################
# node for preprocessing of functional
preproc=prpr.func_preproc_fsl('04_preproc')
#pipe.connect(changedim, 'out_file', preproc, 'inputspec.in_file')
#preproc.inputs.inputspec.in_file=_FUNC_

pipe.connect(datasource, 'func', preproc, 'inputspec.in_file')
pipe.connect(anatproc, 'bet.outputspec.out_brain_mask', preproc, 'inputspec.anat_brain')

########################################################################################################################
# nodes to fix TR in header

getdim = pe.MapNode(interface=myfsl.utils.ImageInfo(), name="01_get_dim",  iterfield=['in_file'])
pipe.connect(preproc, 'outputspec.preprocessed_func', getdim, 'in_file')
changedim = pe.MapNode(myfsl.utils.ChangePixDim(), name="02_fixTR",
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

compcor=prpr.t_compcor(wf_name='045_compcor')
compcor.inputs.inputspec.num_noise_components = 6

pipe.connect(changedim, 'out_file', compcor, 'inputspec.func')

########################################################################################################################
# median angle correction

from mypype.workflows.preproc.median_angle import create_median_angle_correction

medang=create_median_angle_correction(name='046_medang')
medang.inputs.inputspec.target_angle=90

pipe.connect(changedim, 'out_file', medang, 'inputspec.subject')

########################################################################################################################
# median angle correction after compcor

medangcc=create_median_angle_correction(name='047_cc_medang')
medangcc.inputs.inputspec.target_angle=90

pipe.connect(compcor, 'outputspec.residual_file', medangcc, 'inputspec.subject')

########################################################################################################################
# continue processing with various nuisance corrections

# no nuisance correction
rest1=process_rest('rest_nonuis')
pipe.connect(changedim, 'out_file', rest1, 'inputspec.preprocessed_func')
pipe.connect(preproc, 'outputspec.func_brain_mask', rest1, 'inputspec.func_brain_mask')

# compcor
rest2=process_rest('rest_cc')
pipe.connect(compcor, 'outputspec.residual_file', rest2, 'inputspec.preprocessed_func')
pipe.connect(preproc, 'outputspec.func_brain_mask', rest2, 'inputspec.func_brain_mask')

# medang
rest3=process_rest('rest_mac')
pipe.connect(medang, 'outputspec.subject', rest3, 'inputspec.preprocessed_func')
pipe.connect(preproc, 'outputspec.func_brain_mask', rest3, 'inputspec.func_brain_mask')

# cc_medang
rest4=process_rest('rest_cc_mac')
pipe.connect(medangcc, 'outputspec.subject', rest4, 'inputspec.preprocessed_func')
pipe.connect(preproc, 'outputspec.func_brain_mask', rest4, 'inputspec.func_brain_mask')

#######################################################################################################################

## Mean

'''
"""

## fslmerge 4D -Tmean *.AVG

meanfunc = pe.MapNode(interface=fsl.ImageMaths(op_string='-Tmean',
                                                   suffix='_mean'),
                          iterfield=['in_file'],
                          name='meanfunc'

    pipe.connect(rest_nonuis,'out_file', meanfunc, 'in_file')

    )


'''



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


