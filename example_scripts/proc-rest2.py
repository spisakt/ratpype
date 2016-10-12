import sys
sys.path.append("/opt/shared/bin/python")

import nipype.pipeline.engine as pe  # pypeline engine
import nipype.interfaces.fsl as fsl  # for fsl interfaces
import nipype.interfaces.io as nio  # for datasink
import mypype.workflows.stat.modelfit as model
import mypype.workflows.stat.easy_thres as thres
import mypype.workflows.preproc.preproc as prpr
import mypype.workflows.rest.reho as reho
import mypype.workflows.rest.centrality as cent
import mypype.workflows as wf
import nipype.interfaces.afni as afni  # afni
import nipype.interfaces.io as nio
import mypype.interfaces.fsl as myfsl
import nipype.workflows.fmri.fsl.preprocess as prpc
import nipype.interfaces.utility as util

from nipype.workflows.fmri.fsl import create_resting_preproc as compcor

import nipype.pipeline.server as server

def get_element(list, index):
	return list[index];

########################################################################################################################
#!/usr/bin/env python

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
#'s_2015042703_a25_vpa6',
#'s_2015042802_a26_vpa6',
#'s_2015042901_a27_vpa6',
#'s_2015042903_a28_vpa6',
#'s_2015043001_a29_vpa6',
#'s_2015043004_a32_vpa6',
#'s_2015050402_a33_vpa6',
#'s_2015050405_a34_vpa6',
#'s_2015050503_a36_vpa6',
#'s_2015050602_a35_vpa6',
#'s_2015050701_a79_vpa6',
#'s_2015050704_a80_vpa6'
]

# second-level input parameters
_REGRESSORS_=\
	dict(
		ctr=[1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0]#,0,0,0,0,0,0,0,0,0,0,0,0],
		vpa4=[0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1]#,0,0,0,0,0,0,0,0,0,0,0,0],
		vpa6=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]#,1,1,1,1,1,1,1,1,1,1,1,1]
	)

#_CONTRASTS_ = 	[
#		['group mean', 'T',['ctr', 'vpa4', 'vpa6'],	[1,  1,  1]],
#		['ctr>vpa4', 'T',['ctr', 'vpa4', 'vpa6'],	[1, -1,  0]],
#		['ctr<vpa4', 'T', ['ctr', 'vpa4', 'vpa6'],	[-1, 1,  0]],
#		['ctr>vpa6', 'T', ['ctr', 'vpa4', 'vpa6'],	[1,	 0, -1]],
#		['ctr<vpa6', 'T', ['ctr', 'vpa4', 'vpa6'],	[-1, 0,  1]]
#	]

_CONTRASTS_ = 	[
		['group mean', 'T',['ctr', 'vpa4', 'vpa6'],	[1,  1,  1]],
		['ctr>vpa4', 'T',['ctr', 'vpa4', 'vpa6'],	[1, -1,  0]],
		['ctr<vpa4', 'T', ['ctr', 'vpa4', 'vpa6'],	[-1, 1,  0]]
	]

_GROUPS_=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

# fMRI 1st level analysis input pars
_FWHM_=12
_TR_=3
_TIME_UNITS_='secs'

########################################################################################################################
# DataGrabber collecting data
########################################################################################################################

pipe = pe.Workflow('analysis_rest_EC_p0001_medang')
pipe.base_dir = _BASE_DIR_

datasource = pe.Node(nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct'], sort_filelist=False), name='01_grabData')
datasource.inputs.base_directory = _BASE_DIR_
datasource.inputs.template = '*'
datasource.inputs.field_template = dict(func=_BASE_DIR_ + '%s/proc_rest/reg/mc_data_brain_cc2standard.nii.gz',
                                        struct=_BASE_DIR_ + '%s/gems_PD*AVG.nii.gz')
datasource.inputs.template_args = dict(func=[['subject_id']],
                                       struct=[['subject_id']])
datasource.inputs.subject_id = _SUBJECTS_

########################################################################################################################
# nodes to fix TR in header
getdim = pe.MapNode(interface=myfsl.utils.ImageInfo(), name="01_get_dim",  iterfield=['in_file'])
pipe.connect(datasource, 'func', getdim, 'in_file')

changedim = pe.MapNode(myfsl.utils.ChangePixDim(), name="05_fixTR",
						   iterfield=['in_file',
									  'xdim',
									  'ydim',
									  'zdim',])
changedim.inputs.tdim=_TR_
pipe.connect(datasource, 'func', changedim, 'in_file')
pipe.connect(getdim, 'out_pixdim1', changedim, 'xdim')
pipe.connect(getdim, 'out_pixdim2', changedim, 'ydim')
pipe.connect(getdim, 'out_pixdim3', changedim, 'zdim')

########################################################################################################################
# median angle correction

from mypype.workflows.preproc.median_angle import create_median_angle_correction

medang=create_median_angle_correction()
medang.inputs.inputspec.target_angle=66

pipe.connect(changedim, 'out_file', )

########################################################################################################################
# node for bandpass filter
bandpass_filter = pe.MapNode(fsl.TemporalFilter(),  # TODO: into preprocess workflow
							 name='07_bandpass_filter',
							 iterfield=['in_file'])

bandpass_filter.inputs.highpass_sigma = 100 / (2 * _TR_)
bandpass_filter.inputs.lowpass_sigma = 12.5 / (2 * _TR_)
#pipe.connect(changedim, 'out_file', bandpass_filter, 'in_file')
pipe.connect(medang, 'subject', bandpass_filter, 'in_file')

########################################################################################################################
# calculate_centrality

graph=cent.create_resting_state_graphs(wf_name='08_centrality')
#graph.inputs.centrality_options.method_options=[True, True]
#graph.inputs.inputspec.method_option=1
graph.get_node( "calculate_centrality").iterables=[('method_option', [1,1,1]),
												   ('threshold_option', [0,0,2]),
												   ('threshold', [0.5, 0.1, 0.6])]
graph.get_node( "calculate_centrality").synchronize = True
graph.inputs.inputspec.template = '/opt/shared2/Autista_Modell1/gm-mask-5mm.nii.gz'
#graph.inputs.inputspec.template = '/opt/shared/etc/std/new/standard-wistar_5mm_brain_mask.nii.gz'
#graph.inputs.inputspec.threshold=0.5
#graph.inputs.inputspec.threshold_option=1
graph.inputs.inputspec.weight_options=[False, True]

pipe.connect(bandpass_filter, 'out_file', graph, 'inputspec.subject')

########################################################################################################################
# get fisrt element of results

get_element=pe.MapNode(interface=util.Function(input_names = ['list','index'],
								   output_names = ['out'],
								   function = get_element),
                                   name = 'get_element',
                                      iterfield=['list'])
get_element.inputs.index=0
pipe.connect(graph, 'outputspec.centrality_outputs', get_element, 'list')

########################################################################################################################
# get_zscore
#from CPAC.utils import get_zscore

#zscore=cent.get_zscore('EC',wf_name='Z')
#zscore.inputs.inputspec.mask_file='/opt/shared2/Autista_Modell1/gm-mask-5mm.nii.gz'
#pipe.connect(get_element, 'out', zscore, 'inputspec.input_file')


########################################################################################################################
# smooth centrality maps
smooth = prpc.create_susan_smooth("smooth_centrality_s10", separate_masks=False)
#smooth.get_node( "smooth").iterables=[('fwhm', [4., 6., 8., 10., 12., 14.])] #TODO: to sigma???
smooth.inputs.inputnode.fwhm=12.
smooth.inputs.inputnode.mask_file='/opt/shared2/Autista_Modell1/gm-mask-5mm.nii.gz'

#pipe.connect(zscore, 'outputspec.z_score_img', smooth, 'inputnode.in_files')
pipe.connect(get_element, 'out', smooth, 'inputnode.in_files')

########################################################################################################################
# permutation-test for centrality

groupmodelfit=model.modelfit_2ndlevel("09_permutation_test_s12_v4",method='randomise_parallel', standardize=False)
groupmodelfit.inputs.inputspec.std_brain = '/opt/shared/etc/std/new/standard-wistar_5mm_brain.nii.gz'
groupmodelfit.inputs.inputspec.std_brain_mask = '/opt/shared2/Autista_Modell1/gm-mask-5mm.nii.gz'

groupmodelfit.inputs.inputspec.regressors=_REGRESSORS_
groupmodelfit.inputs.inputspec.contrasts=_CONTRASTS_
groupmodelfit.inputs.inputspec.groups=_GROUPS_

pipe.connect(smooth, 'outputnode.smoothed_files', groupmodelfit, 'inputspec.copes')

########################################################################################################################
# seed-based correlation maps



########################################################################################################################
########################################################################################################################
pipe.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
pipe.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
pipe.write_graph('graph.dot', graph2use='colored');
########################################################################################################################
x=pipe.run(plugin='SGE', plugin_args=dict(template='/opt/shared/etc/conf/sgetemplate.sh', qsub_args='-q nipype -V -cwd'))
#x=pipe.run(plugin='SGEGraph', plugin_args={'template' : '/opt/shared/etc/conf/sgetemplate.sh','dont_resubmit_completed_jobs': True})
#x=pipe.run(plugin='MultiProc')
#x=pipe.run()
########################################################################################################################
########################################################################################################################







