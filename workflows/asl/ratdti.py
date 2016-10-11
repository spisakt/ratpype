
 # imports
import nipype.interfaces.utility as util 
import nipype.pipeline.engine as pe          # pypeline engine
import mypype.interfaces.fsl as myfsl
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.pipeline.server as nserver



def ratdti(name='dti'):
	"""
		swapscale: do upscaling and reorientation
	
	"""
	
	dti = pe.Workflow(name=name)
	dti.base_dir = '.'

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file', 'in_bvals', 'in_bvecs', 'in_mask']),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""

        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_FA', 'out_MD', 'out_AD', 'out_RD', 'out_MO']),
                         name='outputspec')


	# eddy_correct
	
	eddy = pe.Node(interface= fsl.EddyCorrect(), name='eddy_correct')
	
	dti.connect(inputnode, 'in_file', eddy, 'in_file')
	
	
	# dti_fit

	dtifit = pe.Node(interface= fsl.DTIFit(), name='DtiFit')
	
	dti.connect(eddy, 'out_file', dtifit, 'dwi')
	dti.connect(inputnode, 'in_bvecs', dtifit, 'bvecs')
	dti.connect(inputnode, 'in_bvals', dtifit, 'bvals')
	dti.connect(inputnode, 'in_mask', dtifit, 'mask')


	dti.connect(dtifit, 'FA', outputnode, 'out_FA')
	dti.connect(dtifit, 'L1', outputnode, 'out_AD')
	dti.connect(dtifit, 'MD', outputnode, 'out_MD')
	# dti.connect(dtifit, 'L3', outputnode, 'out_RD')
	dti.connect(dtifit, 'MO', outputnode, 'out_MO')


	
	return dti










