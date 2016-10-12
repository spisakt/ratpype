from nipype import config
from nipype.interfaces import spm, fsl

import nipype.interfaces.io as nio  # Data i/o
import nipype.interfaces.fsl as fsl  # fsl
import nipype.interfaces.afni as afni  # afni
import nipype.interfaces.utility as util  # utility
import nipype.pipeline.engine as pe  # pypeline engine
import nipype.algorithms.modelgen as model  # model generation
import nipype.algorithms.rapidart as ra  # artifact detection
import nipype.workflows.fmri.fsl.preprocess as preproc
from nipype.algorithms.misc import TSNR
import mypype.interfaces.fsl as myfsl


import mypype.workflows.bet.ratbet as mine

def extract_noise_components(realigned_file, noise_mask_file, num_components):
    """Derive components most reflective of physiological noise
    """
    import os
    from nibabel import load
    import numpy as np
    import scipy as sp
    imgseries = load(realigned_file)
    components = None
    mask = load(noise_mask_file).get_data()
    voxel_timecourses = imgseries.get_data()[mask > 0]
    voxel_timecourses[np.isnan(np.sum(voxel_timecourses, axis=1)), :] = 0
    # remove mean and normalize by variance
    # voxel_timecourses.shape == [nvoxels, time]
    X = voxel_timecourses.T
    stdX = np.std(X, axis=0)
    stdX[stdX == 0] = 1.
    stdX[np.isnan(stdX)] = 1.
    stdX[np.isinf(stdX)] = 1.
    X = (X - np.mean(X, axis=0))/stdX
    u, _, _ = sp.linalg.svd(X, full_matrices=False)
    if components is None:
        components = u[:, :num_components]
    else:
        components = np.hstack((components, u[:, :num_components]))
    components_file = os.path.join(os.getcwd(), 'noise_components.txt')
    np.savetxt(components_file, components, fmt="%.10f")
    return components_file

def getthreshop(thresh):
    return ['-thr %.10f -Tmin -bin' % (0.1 * val[1]) for val in thresh]


def pickfirst(files):
    if isinstance(files, list):
        return files[0]
    else:
        return files


def pickmiddle(files):
    from nibabel import load
    import numpy as np
    middlevol = []
    for f in files:
        middlevol.append(int(np.ceil(load(f).shape[3] / 2)))
    return middlevol


def pickvol(filenames, fileidx, which):
    from nibabel import load
    import numpy as np
    if which.lower() == 'first':
        idx = 0
    elif which.lower() == 'middle':
        idx = int(np.ceil(load(filenames[fileidx]).shape[3] / 2))
    elif which.lower() == 'last':
        idx = load(filenames[fileidx]).shape[3] - 1
    else:
        raise Exception('unknown value for volume selection : %s' % which)
    return idx


def getbtthresh(medianvals):
    return [0.75 * val for val in medianvals]


def chooseindex(fwhm):
    if fwhm < 1:
        return [0]
    else:
        return [1]


def getmeanscale(medianvals):
    return ['-mul %.10f' % (10000. / val) for val in medianvals]


def getusans(x):
    return [[tuple([val[0], 0.75 * val[1]])] for val in x]

tolist = lambda x: [x]
highpass_operand = lambda x: '-bptf %.10f -1' % x


def func_preproc_fsl(wf_name='func_preproc'):



    featpreproc = pe.Workflow(name=wf_name)

    """
        Set up a node to define all inputs required for the preprocessing workflow

    """

    inputnode = pe.Node(interface=util.IdentityInterface(fields=['in_file', 'anat_brain'],
                                         mandatory_inputs=True), name='inputspec')


    # preprocessed_func: upscaled, brain-extracted and motion corrected functional data
    outputnode = pe.Node(interface=util.IdentityInterface(fields=['preprocessed_func',
                                                                  'example_func',
                                                                  'func_brain_mask',
                                                                  'motion_plots',
                                                                  'func2anat_mat'],
                                                          mandatory_inputs=True),
                         name='outputspec')

    """
        Reorient data to match Paxinos

    """

    reorient = pe.MapNode(interface=fsl.utils.SwapDimensions(new_dims=("RL", "AP", "IS")),
                          name='reorient',
                          iterfield=['in_file'])
    featpreproc.connect(inputnode, 'in_file', reorient, 'in_file')

    """
    Upscale data to human range

    """

    upscaler =mine.upscale()
    featpreproc.connect(reorient, 'out_file', upscaler, 'inputspec.in_file')

    """
    Convert functional images to float representation. Since there can
    be more than one functional run we use a MapNode to convert each
    run.
    """

    img2float = pe.MapNode(interface=fsl.ImageMaths(out_data_type='float',
                                                    op_string='',
                                                    suffix='_dtype'),
                           iterfield=['in_file'],
                           name='img2float')
    featpreproc.connect(upscaler, 'outputspec.out_file', img2float, 'in_file')

    """
    Extract the first volume of the first run as the reference
    """

    extract_ref = pe.MapNode(interface=fsl.ExtractROI(t_size=1),
                             iterfield=['in_file', 't_min'],
                             name='extractref')

    featpreproc.connect(img2float, 'out_file', extract_ref, 'in_file')
    featpreproc.connect(img2float, ('out_file', pickmiddle), extract_ref, 't_min')
    featpreproc.connect(extract_ref, 'roi_file', outputnode, 'example_func')

    """
    Realign the functional runs to the reference (1st volume of first run)
    """

    motion_correct = pe.MapNode(interface=fsl.MCFLIRT(save_mats=True,
                                                      save_plots=True),
                                name='motioncorr',
                                iterfield=['in_file', 'ref_file'])
    featpreproc.connect(img2float, 'out_file', motion_correct, 'in_file')
    featpreproc.connect(extract_ref, 'roi_file', motion_correct, 'ref_file')
    featpreproc.connect(motion_correct, 'par_file', outputnode, 'motion_parameters')
    featpreproc.connect(motion_correct, 'out_file', outputnode, 'realigned_files')

    """
    Plot the estimated motion parameters
    """

    plot_motion = pe.MapNode(interface=fsl.PlotMotionParams(in_source='fsl'),
                             name='plot_motion',
                             iterfield=['in_file'])
    plot_motion.iterables = ('plot_type', ['displacement', 'rotations', 'translations'])
    featpreproc.connect(motion_correct, 'par_file', plot_motion, 'in_file')
    featpreproc.connect(plot_motion, 'out_file', outputnode, 'motion_plots')

    """
    Extract the mean volume of the first functional run
    """

    meanfunc = pe.MapNode(interface=fsl.ImageMaths(op_string='-Tmean',
                                                   suffix='_mean'),
                          iterfield=['in_file'],
                          name='meanfunc')
    featpreproc.connect(motion_correct, 'out_file', meanfunc, 'in_file')

    """
    estimate func2anat matrix
    """
    f2a = pe.MapNode(util.Function(input_names=['in_file', 'like'],
                                   output_names=['out_mat'],
                                   function=myfsl.utils.run_resample),
                     name='func2anat',
                     iterfield=['in_file', 'like'])

    featpreproc.connect(meanfunc, 'out_file', f2a, 'in_file')
    featpreproc.connect(inputnode, 'anat_brain', f2a, 'like')
    featpreproc.connect(f2a, 'out_mat', outputnode, 'func2anat_mat')

    """
    Invert func2anat matrix
    """

    invertmat= pe.MapNode(interface=fsl.ConvertXFM(invert_xfm=True),
                            iterfield=['in_file'],
                            name='invertmat'
                            )

    featpreproc.connect(f2a, 'out_mat', invertmat, 'in_file')

    """
    Resample the anatomical brain mask to the space of functional image
    """

    resamplemask = pe.MapNode(interface=fsl.ApplyXfm(interp='nearestneighbour'),
                              iterfield=['reference', 'in_file', 'in_matrix_file'],
                              name='resamplemask')

    featpreproc.connect(inputnode, 'anat_brain', resamplemask, 'in_file')
    featpreproc.connect(meanfunc, 'out_file', resamplemask, 'reference')
    featpreproc.connect(invertmat, 'out_file', resamplemask, 'in_matrix_file')

    """
    Mask the functional runs with the resampled mask
    """

    maskfunc = pe.MapNode(interface=fsl.ImageMaths(suffix='_bet',
                                                   op_string='-mas'),
                          iterfield=['in_file', 'in_file2'],
                          name='maskfunc')
    featpreproc.connect(motion_correct, 'out_file', maskfunc, 'in_file')
    featpreproc.connect(resamplemask, 'out_file', maskfunc, 'in_file2')

    """
    Determine the 2nd and 98th percentile intensities of each functional run
    """

    getthresh = pe.MapNode(interface=fsl.ImageStats(op_string='-p 2 -p 98'),
                           iterfield=['in_file'],
                           name='getthreshold')
    featpreproc.connect(maskfunc, 'out_file', getthresh, 'in_file')

    """
    Threshold the first run of the functional data at 10% of the 98th percentile
    """

    threshold = pe.MapNode(interface=fsl.ImageMaths(out_data_type='char',
                                                    suffix='_thresh'),
                           iterfield=['in_file', 'op_string'],
                           name='threshold')
    featpreproc.connect(maskfunc, 'out_file', threshold, 'in_file')

    """
    Define a function to get 10% of the intensity
    """

    featpreproc.connect(getthresh, ('out_stat', getthreshop), threshold, 'op_string')
    featpreproc.connect(threshold, 'out_file', outputnode, 'func_brain_mask')

    #"""
    #Determine the median value of the functional runs using the mask
    #"""

    #medianval = pe.MapNode(interface=fsl.ImageStats(op_string='-k %s -p 50'),
    #                       iterfield=['in_file', 'mask_file'],
    #                       name='medianval')
    #featpreproc.connect(motion_correct, 'out_file', medianval, 'in_file')
    #featpreproc.connect(threshold, 'out_file', medianval, 'mask_file')

    #"""
    #Dilate the mask
    #"""

    #dilatemask = pe.MapNode(interface=fsl.ImageMaths(suffix='_dil',
    #                                                 op_string='-dilF'),
    #                        iterfield=['in_file'],
    #                        name='dilatemask')
    #featpreproc.connect(threshold, 'out_file', dilatemask, 'in_file')

    """
    Mask the motion corrected functional runs with the dilated mask
    """

    maskfunc2 = pe.MapNode(interface=fsl.ImageMaths(suffix='_mask',
                                                    op_string='-mas'),
                           iterfield=['in_file', 'in_file2'],
                           name='maskfunc2')
    featpreproc.connect(motion_correct, 'out_file', maskfunc2, 'in_file')
    featpreproc.connect(threshold, 'out_file', maskfunc2, 'in_file2')
    #featpreproc.connect(dilatemask, 'out_file', maskfunc2, 'in_file2')

    featpreproc.connect(maskfunc2, 'out_file', outputnode, 'preprocessed_func')


    return featpreproc

def t_compcor(wf_name="t_compcor"):

    cc = pe.Workflow(name=wf_name)

    # Define nodes
    inputnode = pe.Node(interface=util.IdentityInterface(fields=['func',
                                                                 'num_noise_components'
                                                                 ]),
                        name='inputspec')
    outputnode = pe.Node(interface=util.IdentityInterface(fields=[
        'noise_mask_file',
        'noise_components',
        'residual_file'
    ]),
        name='outputspec')


    tsnr = pe.MapNode(TSNR(regress_poly=2), name='tsnr', iterfield=['in_file'])
    getthresh = pe.MapNode(interface=fsl.ImageStats(op_string='-p 98'),
                           name='getthreshold', iterfield=['in_file'])
    threshold_stddev = pe.MapNode(fsl.Threshold(), name='threshold', iterfield=['in_file', 'thresh'])
    compcor = pe.MapNode(util.Function(input_names=['realigned_file',
                                                 'noise_mask_file',
                                                 'num_components'],
                                     output_names=['noise_components'],
                                     function=extract_noise_components),
                       name='compcorr',
                         iterfield=['realigned_file', 'noise_mask_file'])
    remove_noise = pe.MapNode(fsl.FilterRegressor(filter_all=True),
                           name='remove_noise',
                              iterfield=['in_file', 'design_file'])

    cc.connect(inputnode, 'func', tsnr, 'in_file')
    cc.connect(tsnr, 'stddev_file', threshold_stddev, 'in_file')
    cc.connect(tsnr, 'stddev_file', getthresh, 'in_file')
    cc.connect(getthresh, 'out_stat', threshold_stddev, 'thresh')
    cc.connect(inputnode, 'func', compcor, 'realigned_file')
    cc.connect(threshold_stddev, 'out_file', compcor, 'noise_mask_file')
    cc.connect(inputnode, 'num_noise_components', compcor, 'num_components')
    cc.connect(tsnr, 'detrended_file', remove_noise, 'in_file')
    cc.connect(compcor, 'noise_components', remove_noise, 'design_file')
    cc.connect(compcor, 'noise_components', outputnode, 'noise_components')
    cc.connect(remove_noise, 'out_file', outputnode, 'residual_file')
    cc.connect(threshold_stddev, 'out_file', outputnode, 'noise_mask_file')

    return cc;

