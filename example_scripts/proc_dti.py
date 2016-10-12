#!/usr/bin/env python

print('Hello Python')

import sys

sys.path.append("/opt/shared/bin/python")

import nipype.pipeline.engine as pe  # pypeline engine
import nipype.interfaces.fsl as fsl  # for fsl interfaces
import nipype.interfaces.io as nio  # for datasink
import mypype.workflows.bet.ratbet as bet
import mypype.workflows.dti.ratdti as dti
import mypype.workflows as wf

import nipype.pipeline.server as server

in_gems = '/opt/shared2/nipype-test/dti_2015052601_m0_ctr_a4_11/gems_PD-T1_avg8_40deg_20150526_01_anatomy.nii-AVG.nii.gz'
in_dti = '/opt/shared2/nipype-test/dti_2015052601_m0_ctr_a4_11/epip_diffusion_shots3_res300_20150526_01_ctr_functional_original.nii'
in_bvecs = '/opt/shared2/nipype-test/bvecs_6atlag_30irany'
in_bvals = '/opt/shared2/nipype-test/bvals_6atlag_30irany'

pipe = pe.Workflow('testworkflow')
pipe.base_dir = '/opt/shared2/nipype-test/'

# node for gems

anatproc = wf.bet.ratbet.anatproc()
anatproc.inputs.inputspec.in_file = in_gems

# dti2anat

dti2anat = wf.bet.ratbet.reg2anat(onlyResample=False)
dti2anat.inputs.inputspec.in_file = in_dti  # fslroi -> 3D

# node for mask resampling

resample = pe.MapNode(interface=fsl.ApplyXfm(), name='resample_mask', iterfield=['in_file', 'in_matrix_file'])
resample.inputs.reference = in_dti  # fslroi -> 3D

# node for dti

dti = wf.dti.ratdti.ratdti()
dti.inputs.inputspec.in_file = in_dti
dti.inputs.inputspec.in_bvals = in_bvals
dti.inputs.inputspec.in_bvecs = in_bvecs

# data sink to save brain extracted image and mask

datasink = pe.Node(nio.DataSink(), name="sinker")
datasink.base_directory = "/opt/shared2/nipype-test/dti_2015052601_m0_ctr_a4_11/"  # filebase(in_gems)

# connects

pipe.connect(anatproc, 'bet.outputspec.out_brain', dti2anat, 'inputspec.in_anat')

pipe.connect(anatproc, 'bet.outputspec.out_brain_mask', resample, 'in_file')
pipe.connect(dti2anat, 'outputspec.out_inv_mat', resample, 'in_matrix_file')

pipe.connect(resample, 'out_file', dti, 'inputspec.in_mask')

# pipe.connect(resample, 'out_file', dti, 'inputspec.in_mask')

# datasink connects

pipe.connect(anatproc, 'standardization.outputspec.out_nonlin_head', datasink, 'anatproc.reg.out_nonlin_head')
pipe.connect(anatproc, 'standardization.outputspec.out_nonlin_brain', datasink, 'anatproc.reg.out_nonlin_brain')
pipe.connect(anatproc, 'standardization.outputspec.out_warpfield', datasink, 'anatproc.reg.out_warpfield')
pipe.connect(anatproc, 'standardization.outputspec.out_lin_brain', datasink, 'anatproc.reg.out_lin_brain')
pipe.connect(anatproc, 'bet.outputspec.out_head', datasink, 'anatproc.bet.out_head')
pipe.connect(anatproc, 'bet.outputspec.out_brain', datasink, 'anatproc.bet.out_brain')
pipe.connect(anatproc, 'bet.outputspec.out_brain_mask', datasink, 'anatproc.bet.out_brain_mask')
# pipe.connect(dti, 'DtiFit.outputs.FA', datasink, 'dti.out_FA')
# pipe.connect(dti, 'DtiFit.outputs.MD', datasink, 'dti.out_MD')
# pipe.connect(dti, 'DtiFit.outputs.AD', datasink, 'dti.out_AD')
# pipe.connect(dti, 'DtiFit.outputs.RD', datasink, 'dti.out_DR')
# pipe.connect(dti, 'DtiFit.outputs.MO', datasink, 'dti.out_MO')


pipe.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
pipe.write_graph('graph.dot', graph2use='colored');
pipe.run()
server.serve_content(pipe)
#pipe.run() #plugin='SGE')

#pipe.write_graph('testpipeline-graph.dot',graph2use='colored');

