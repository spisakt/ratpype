
 # imports
import nipype.interfaces.utility as util 
import nipype.pipeline.engine as pe          # pypeline engine
import mypype.interfaces.fsl as myfsl
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.pipeline.server as nserver



def upscale(name='upscale'):
	""" ...
	
	"""
	
	upscaler = pe.Workflow(name=name)
	upscaler.base_dir = '.'

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file']),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_file']),
                         name='outputspec')

		

	"""
    	Set up a node to read voxel size

    	"""

	getdim = pe.Node(interface=myfsl.utils.ImageInfo(), name="get_dim")
	
	"""
    	Set up a node to change voxel size

    	"""

	changedim = pe.Node(myfsl.utils.ChangePixDim(), name="change_pixdim")


	upscaler.connect(inputnode, 'in_file', getdim, 'in_file')
	upscaler.connect(inputnode, 'in_file', changedim, 'in_file')
	upscaler.connect(getdim, ('out_pixdim1', mult10), changedim, 'xdim')
	upscaler.connect(getdim, ('out_pixdim2', mult10), changedim, 'ydim')
	upscaler.connect(getdim, ('out_pixdim3', mult10), changedim, 'zdim')
	upscaler.connect(changedim, 'out_file', outputnode, 'out_file')

	return upscaler
