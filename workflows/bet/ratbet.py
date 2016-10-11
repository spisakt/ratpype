



 # imports
import nipype.interfaces.utility as util 
import nipype.pipeline.engine as pe          # pypeline engine
import mypype.interfaces.fsl as myfsl
import nipype.interfaces.fsl as fsl
from nipype.interfaces.utility import Function




def mult10(in_val):
    return in_val * 10  # TODO: make parametrizable

def div2(in_val):
    return in_val / 2.8


def upscale(name='upscale'):
	""" ...
	
	"""
	
	upscaler = pe.Workflow(name=name)


	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file'], mandatory_inputs=True),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_file'], mandatory_inputs=True),
                         name='outputspec')

		

	"""
    	Set up a node to read voxel size

    	"""

	getdim = pe.MapNode(interface=myfsl.utils.ImageInfo(), name="get_dim",  iterfield=['in_file'])

	"""
    	Multiple voxel size by 10

    	"""

	mult10x = pe.MapNode(name='mult10x',
               interface=Function(input_names=['in_val'],
                                  output_names=['out_val'],
                                  function=mult10),
						 iterfield=['in_val'])

	mult10y = pe.MapNode(name='mult10y',
               interface=Function(input_names=['in_val'],
                                  output_names=['out_val'],
                                  function=mult10),
						 iterfield=['in_val'])

	mult10z = pe.MapNode(name='mult10z',
               interface=Function(input_names=['in_val'],
                                  output_names=['out_val'],
                                  function=mult10),
						 iterfield=['in_val'])


	"""
    	Set up a node to change voxel size

    	"""

	changedim = pe.MapNode(myfsl.utils.ChangePixDim(), name="upscale",
						   iterfield=['in_file',
									  'xdim',
									  'ydim',
									  'zdim'])


	upscaler.connect(inputnode, 'in_file', getdim, 'in_file')
	upscaler.connect(inputnode, 'in_file', changedim, 'in_file')

	upscaler.connect(getdim, 'out_pixdim1', mult10x, 'in_val')
	upscaler.connect(getdim, 'out_pixdim2', mult10y, 'in_val')
	upscaler.connect(getdim, 'out_pixdim3', mult10z, 'in_val')

	upscaler.connect(mult10x, 'out_val', changedim, 'xdim')
	upscaler.connect(mult10y, 'out_val', changedim, 'ydim')
	upscaler.connect(mult10z, 'out_val', changedim, 'zdim')
	upscaler.connect(changedim, 'out_file', outputnode, 'out_file')

	return upscaler


def ratbet(name='bet', swapscale=True):
	"""
		swapscale: do upscaling and reorientation
	
	"""
	
	bet = pe.Workflow(name=name)

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file']),
                            name='inputspec', mandatory_inputs=True)

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_brain', 'out_brain_mask', 'out_head']),
                         name='outputspec', mandatory_inputs=True)

		

	# swapper
	
	reorient = pe.MapNode(interface=fsl.utils.SwapDimensions(new_dims=("RL", "AP", "IS")),
						  name='reorient',
						  iterfield=['in_file'])


	# upscale

	upscaler = upscale()

	# scaley
	
	getdim = pe.MapNode(interface=myfsl.utils.ImageInfo(), name="get_dim", iterfield=['in_file'])
	div = pe.MapNode(interface=Function(
		input_names=['in_val'],
		output_names=['out_val'],
		function=div2),
		name='divDim', iterfield=['in_val'])
	scale_y = pe.MapNode(myfsl.utils.ChangePixDim(), name="scale_y", iterfield=['in_file', 'xdim', 'ydim', 'zdim'])

	# bet
	fslbet = pe.MapNode(interface=fsl.BET(frac=0.6, vertical_gradient=0), name="bet", iterfield=['in_file'])
	fslbet2 = pe.MapNode(interface=fsl.BET(frac=0.35, vertical_gradient=0.25, mask=True), name="bet2", iterfield=['in_file'])
									# frac=0.3
	# descaley

	rescale_y = pe.MapNode(myfsl.utils.ChangePixDim(), name="rescale_y", iterfield=['in_file', 'xdim', 'ydim', 'zdim'])
	rescale_y_mask = pe.MapNode(myfsl.utils.ChangePixDim(), name="rescale_y_mask", iterfield=['in_file', 'xdim', 'ydim', 'zdim']) # TODO: no new node, 'iterable' instead?

	
	if (swapscale==True):
		bet.connect(inputnode, 'in_file', reorient, 'in_file')
		bet.connect(reorient, 'out_file', upscaler, 'inputspec.in_file')
		bet.connect(upscaler, 'outputspec.out_file', getdim, 'in_file')
		bet.connect(reorient, 'out_file', scale_y, 'in_file')
		bet.connect(getdim, 'out_pixdim1', scale_y, 'xdim')
		bet.connect(getdim, 'out_pixdim2', div, 'in_val')
		bet.connect(div, 'out_val', scale_y, 'ydim')
		bet.connect(getdim, 'out_pixdim3', scale_y, 'zdim')
	else:
		bet.connect(inputnode, 'in_file', getdim, 'in_file')
		bet.connect(inputnode, 'in_file', scale_y, 'in_file')

	bet.connect(scale_y, 'out_file', fslbet, 'in_file')
	bet.connect(fslbet, 'out_file', fslbet2, 'in_file')

	bet.connect(fslbet2, 'out_file', rescale_y, 'in_file')
	bet.connect(getdim, 'out_pixdim1', rescale_y, 'xdim')
	bet.connect(getdim, 'out_pixdim2', rescale_y, 'ydim')
	bet.connect(getdim, 'out_pixdim3', rescale_y, 'zdim')

	bet.connect(fslbet2, 'mask_file', rescale_y_mask, 'in_file')
	bet.connect(getdim, 'out_pixdim1', rescale_y_mask, 'xdim')
	bet.connect(getdim, 'out_pixdim2', rescale_y_mask, 'ydim')
	bet.connect(getdim, 'out_pixdim3', rescale_y_mask, 'zdim')


	bet.connect(rescale_y, 'out_file', outputnode, 'out_brain')
	bet.connect(rescale_y_mask, 'out_file', outputnode, 'out_brain_mask')
	bet.connect(upscaler, 'outputspec.out_file', outputnode, 'out_head')

	return bet


def reg2std(name='standardization'):
	

	"""
		Linear and non-linear standardization for structural rat MRI images
		Input: upscaled data
	
	"""
	
	reg = pe.Workflow(name=name)

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file_head', 'in_file_brain'], mandatory_inputs=True),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_nonlin_head', 'out_nonlin_brain', 'out_warpfield', 'out_lin_brain'], mandatory_inputs=True),
                         name='outputspec')



	"""
		Node for linear (12-param) reg
		flirt -in $in -ref $std -dof 12 -omat $omat -bins 256 -cost $type -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -interp trilinear
	"""
	flirt=pe.MapNode(interface=fsl.FLIRT(reference='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz',
										 dof=12,
										 bins=256,
										 cost='corratio',
										 interp='trilinear'),
					 name='linear_standardization',
					 iterfield=['in_file']) #out_matrix_file?, searchr?

	"""
		Non-linear reg
		fnirt --in=$in --ref=$std --aff=$init --iout=$out --miter=2,3 --infwhm=4,1 --reffwhm=2,0 --subsamp=8,1 --estint=1,1 --applyrefmask=1,1 --applyinmask=0,0 --lambda=200,500 --warpres=10,10,10 --intmod=global_non_linear --refmask=$refmask --fout=$warpingfield --interp=spline
	"""
	#TODO: parametrize standard template
	fnirt=pe.MapNode(interface=fsl.FNIRT( \
			ref_file='/opt/shared/etc/std/new/standard-wistar_2mm_brain.nii.gz', \
			refmask_file='/opt/shared/etc/std/new/standard-wistar_2mm_brain_mask.nii.gz', \
			max_nonlin_iter=[2,3], \
			in_fwhm=[2,0], \
			ref_fwhm=[2,0], \
			subsampling_scheme=[8,1],\
			apply_intensity_mapping=[1,1],\
			apply_refmask=[1,1],\
			apply_inmask=[0,0],\
			regularization_lambda=[200,500],\
			warp_resolution=(10,10,10),\
			intensity_mapping_model='global_non_linear_with_bias',\
			field_file=True),
		name='nonlinear_standardization',
	iterfield=['in_file', 'affine_file' ])
	
	"""
		Non-linear reg
		fnirt --in=$in --ref=$std --aff=$init --iout=$out --miter=2,3 --infwhm=4,1 --reffwhm=2,0 --subsamp=8,1 --estint=1,1 --applyrefmask=1,1 --applyinmask=0,0 --lambda=200,500 --warpres=10,10,10 --intmod=global_non_linear --refmask=$refmask --fout=$warpingfield --interp=spline
	"""

	applyWarp=pe.MapNode(interface=fsl.ApplyWarp(), name="warp_brain",
						 iterfield=['in_file', 'ref_file', 'field_file'])
	

	# TODO applywarp: brain

	reg.connect(inputnode, "in_file_brain", flirt, "in_file")
	reg.connect(flirt, "out_file", outputnode, "out_lin_brain")

	reg.connect(inputnode, "in_file_head", fnirt, "in_file")
	reg.connect(flirt, "out_matrix_file", fnirt, "affine_file")

	reg.connect(inputnode, "in_file_brain", applyWarp, "in_file")
	reg.connect(fnirt, "warped_file", applyWarp, "ref_file")
	reg.connect(fnirt, "field_file", applyWarp, "field_file")

	reg.connect(fnirt, "warped_file", outputnode, "out_nonlin_head")
	reg.connect(applyWarp, "out_file", outputnode, "out_nonlin_brain")
	reg.connect(fnirt, "field_file", outputnode, "out_warpfield")

	return reg


def anatproc(name='anatproc'):
	

	"""
		Linear and non-linear registration for structural rat MRI images
		Input: upscaled data
	
	"""
	
	anatproc = pe.Workflow(name=name)

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file', 'out_dir'],  mandatory_inputs=True),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_nonlin_head', 'out_nonlin_brain', 'out_warpfield', 'out_lin_brain', 'out_head', 'out_brain', 'out_brain_mask'], mandatory_inputs=True),
                         name='outputspec')

	"""
    	Correct for motion and merge

    	"""
	# todo


	"""
    	Upscale and bet

    	"""
	bet=ratbet()	
	
	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""

	register=reg2std()

	anatproc.connect(inputnode, "in_file", bet, "inputspec.in_file")
	anatproc.connect(bet, "outputspec.out_head", register, "inputspec.in_file_head")
	anatproc.connect(bet, "outputspec.out_brain", register, "inputspec.in_file_brain")
	
	# datasink
	anatproc.connect(inputnode, 'out_dir', outputnode, 'base_directory')
	anatproc.connect(register, 'outputspec.out_nonlin_head', outputnode, 'out_nonlin_head')
	anatproc.connect(register, 'outputspec.out_nonlin_brain', outputnode, 'out_nonlin_brain')
	anatproc.connect(register, 'outputspec.out_warpfield', outputnode, 'out_warpfield')
	anatproc.connect(register, 'outputspec.out_lin_brain', outputnode, 'out_lin_brain')
	anatproc.connect(bet, 'outputspec.out_head', outputnode, 'out_head')
	anatproc.connect(bet, 'outputspec.out_brain', outputnode, 'out_brain')
	anatproc.connect(bet, 'outputspec.out_brain_mask', outputnode, 'out_brain_mask')

	return anatproc

def reg2anat(name='registration', onlyResample=True):

	"""
		Finding the transformation which fits an arbitrary input image to an anatomical image.
		If images are different only in voxel size, onlyResample=T should be applied.
		If onlyResample=F, rigid-body registration will be performed.
		Input: upscaled image, upscaled anatomical image
		Output transformation matrix
	
	"""

	reg=pe.Workflow(name=name)
	reg.base_dir='.'

	"""
    	Set up a node to define all inputs required for the preprocessing workflow

   	"""

	inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file', 'in_anat'], mandatory_inputs=True),
                            name='inputspec')

	"""
    	Set up a node to define outputs for the preprocessing workflow

    	"""


        outputnode = pe.Node(interface=util.IdentityInterface(fields=['out_mat', 'out_inv_mat']),
                         name='outputspec')


	if (onlyResample == False):
		flirt=pe.MapNode(interface=fsl.FLIRT(dof=6, bins=256, interp='trilinear'),
						 name='linear_registration',
						 iterfield=['in_file', 'reference'])
		invertMat=pe.MapNode(interface=fsl.ConvertXFM(invert_xfm = True),
							 name='invert_matrix',
							 iterfield=['in_file'])

		reg.connect(inputnode, 'in_file', flirt, 'in_file')
		reg.connect(inputnode, 'in_anat', flirt, 'reference')
		reg.connect(flirt, 'out_matrix_file', outputnode, 'out_mat')
		reg.connect(flirt, 'out_matrix_file', invertMat, 'in_file')
		reg.connect(invertMat, 'out_file', outputnode, 'out_inv_mat')
	else:
		print('Not implemented!') # TODO




	return reg







