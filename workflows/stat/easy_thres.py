import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
import mypype.interfaces.fsl.utils as myutils
import nipype.interfaces.utility as util


def threshold(wf_name, correction="uncorrected"):
    """
    Workflow for carrying out uncorrected, cluster-based and voxel-based thresholding
    (following FSL terminology)
    and colour activation overlaying

    Parameters
    ----------
    wf_name : string
        Workflow name

    Returns
    -------
    easy_thresh : object
        Easy thresh workflow object

    Notes
    -----

    `Source <https://github.com/FCP-INDI/C-PAC/blob/master/CPAC/easy_thresh/easy_thresh.py>`_
    Modifyed by Tamas Spisak for Preclinical use
    Added: uncorrected and voxel corrected thresholding

    Workflow Inputs::

        inputspec.z_stats : string (nifti file)
            z_score stats output for t or f contrast from flameo

        inputspec.merge_mask : string (nifti file)
            mask generated from 4D Merged derivative file

        inputspec.z_threshold : float
            Z Statistic threshold value for cluster thresholding. It is used to
            determine what level of activation would be statistically significant.
            Increasing this will result in higher estimates of required effect.

        inputspec.p_threshold : float
            Probability threshold for cluster thresholding.

        inputspec.paramerters : string (tuple)
            tuple containing which MNI and FSLDIR path information

    Workflow Outputs::

        outputspec.cluster_threshold : string (nifti files)
           the thresholded Z statistic image for each t contrast

        outputspec.cluster_index : string (nifti files)
            image of clusters for each t contrast; the values
            in the clusters are the index numbers as used
            in the cluster list.

        outputspec.overlay_threshold : string (nifti files)
            3D color rendered stats overlay image for t contrast
            After reloading this image, use the Statistics Color
            Rendering GUI to reload the color look-up-table

        outputspec.overlay_rendered_image : string (nifti files)
           2D color rendered stats overlay picture for each t contrast

        outputspec.cluster_localmax_txt : string (text files)
            local maxima text file, defines the coordinates of maximum value
            in the cluster


    Order of commands in case of cluster correction:

    - Estimate smoothness of the image::

        smoothest --mask= merge_mask.nii.gz --zstat=.../flameo/stats/zstat1.nii.gz

        arguments
        --mask  :  brain mask volume
        --zstat :  filename of zstat/zfstat image

    - Create mask. For details see `fslmaths <http://www.fmrib.ox.ac.uk/fslcourse/lectures/practicals/intro/index.htm#fslutils>`_::

        fslmaths ../flameo/stats/zstat1.nii.gz
                 -mas merge_mask.nii.gz
                 zstat1_mask.nii.gz

        arguments
        -mas   : use (following image>0) to mask current image

    - Copy Geometry image dimensions, voxel dimensions, voxel dimensions units string, image orientation/origin or qform/sform info) from one image to another::

        fslcpgeom MNI152_T1_2mm_brain.nii.gz zstat1_mask.nii.gz

    - Cluster based thresholding. For details see `FEAT <http://www.fmrib.ox.ac.uk/fsl/feat5/detail.html#poststats>`_::

        cluster --dlh = 0.0023683100
                --in = zstat1_mask.nii.gz
                --oindex = zstat1_cluster_index.nii.gz
                --olmax = zstat1_cluster_localmax.txt
                --othresh = zstat1_cluster_threshold.nii.gz
                --pthresh = 0.0500000000
                --thresh = 2.3000000000
                --volume = 197071

        arguments
        --in    :    filename of input volume
        --dlh   :    smoothness estimate = sqrt(det(Lambda))
        --oindex  :  filename for output of cluster index
        --othresh :  filename for output of thresholded image
        --olmax   :  filename for output of local maxima text file
        --volume  :  number of voxels in the mask
        --pthresh :  p-threshold for clusters
        --thresh  :  threshold for input volume

     Z statistic image is thresholded to show which voxels or clusters of voxels are activated at a particular significance level.
     A Z statistic threshold is used to define contiguous clusters. Then each cluster's estimated significance level (from GRF-theory)
     is compared with the cluster probability threshold. Significant clusters are then used to mask the original Z statistic image.

    High Level Workflow Graph:

    .. image:: ../images/easy_thresh.dot.png
       :width: 800


    Detailed Workflow Graph:

    .. image:: ../images/easy_thresh_detailed.dot.png
       :width: 800

    TODO: Order of commands in case of voxel correction and uncorrected

    Examples
    --------

    >>> import easy_thresh
    >>> preproc = easy_thresh.easy_thresh("new_workflow")
    >>> preproc.inputs.inputspec.z_stats= 'flameo/stats/zstat1.nii.gz'
    >>> preproc.inputs.inputspec.merge_mask = 'merge_mask/alff_Z_fn2standard_merged_mask.nii.gz'
    >>> preproc.inputs.inputspec.z_threshold = 2.3
    >>> preproc.inputs.inputspec.p_threshold = 0.05
    >>> preporc.run()  -- SKIP doctest

    """

    easy_thresh = pe.Workflow(name=wf_name)

    outputnode = pe.Node(util.IdentityInterface(fields=['thres_zstat',
                                                    'overlay_threshold']),
                         name='outputspec')



    if (correction=='uncorrected'):
        inputnode = pe.Node(util.IdentityInterface(fields=['z_stats',
                                                           'mask',
                                                           'p_threshold']),
                             name='inputspec')

        # run clustering after fixing stats header for talspace
        zstat_mask = pe.MapNode(interface=fsl.MultiImageMaths(),
                                  name='zstat_mask',
                                  iterfield=['in_file', 'operand_files'])
        #operations to perform
        #-mas use (following image>0) to mask current image
        zstat_mask.inputs.op_string = '-mas %s'

        easy_thresh.connect(inputnode, 'z_stats', zstat_mask, 'in_file')
        easy_thresh.connect(inputnode, 'mask', zstat_mask, 'operand_files')

        ptoz=pe.Node(interface=myutils.PtoZ(), name='PtoZ')

        easy_thresh.connect(inputnode, 'p_threshold', ptoz, 'p_val' )

        thres=pe.MapNode(interface=fsl.Threshold(), name='ThresholdUncorr',
                          iterfield=['in_file'])

        easy_thresh.connect(zstat_mask, 'out_file', thres, 'in_file' )
        easy_thresh.connect(ptoz, 'z_score', thres, 'thresh' )

        easy_thresh.connect(thres, 'out_file', outputnode, 'thres_zstat' )
        easy_thresh.connect(ptoz, 'z_score', outputnode, 'overlay_threshold' )

    elif (correction=='voxel'):
        inputnode = pe.Node(util.IdentityInterface(fields=['z_stats',
                                                           'mask',
                                                           'p_threshold']),
                             name='inputspec')
         # run clustering after fixing stats header for talspace
        zstat_mask = pe.MapNode(interface=fsl.MultiImageMaths(),
                                  name='zstat_mask',
                                  iterfield=['in_file', 'operand_files'])
        #operations to perform
        #-mas use (following image>0) to mask current image
        zstat_mask.inputs.op_string = '-mas %s'

        easy_thresh.connect(inputnode, 'z_stats', zstat_mask, 'in_file')
        easy_thresh.connect(inputnode, 'mask', zstat_mask, 'operand_files')

        # estimate image smoothness
        smooth_estimate = pe.MapNode(interface=fsl.SmoothEstimate(),
                                        name='smooth_estimate',
                                        iterfield=['zstat_file', 'mask_file'])

        easy_thresh.connect(zstat_mask, 'out_file', smooth_estimate, 'zstat_file' )
        easy_thresh.connect(inputnode, 'mask', smooth_estimate, 'mask_file' )

        ptoz=pe.MapNode(interface=myutils.PtoZ(), name='PtoZ',
                          iterfield=['resels'])

        easy_thresh.connect(inputnode, 'p_threshold', ptoz, 'p_val' )
        easy_thresh.connect(smooth_estimate, 'resels', ptoz, 'resels' )


        thres=pe.MapNode(interface=fsl.Threshold(), name='ThresholdVoxel',
                          iterfield=['in_file', 'thresh'])
        thres._interface._suffix='vox'

        easy_thresh.connect(zstat_mask, 'out_file', thres, 'in_file' )
        easy_thresh.connect(ptoz, 'z_score', thres, 'thresh' )

        easy_thresh.connect(thres, 'out_file', outputnode, 'thres_zstat' )
        easy_thresh.connect(ptoz, 'z_score', outputnode, 'overlay_threshold' )

    elif (correction=='tfce'):

        print('Not good!!!')
        #TODO

        inputnode = pe.Node(util.IdentityInterface(fields=['z_stats',
                                                           'mask',
                                                           'p_threshold']),
                            name='inputspec')

        zstat_mask = pe.MapNode(interface=fsl.MultiImageMaths(),
                                  name='zstat_mask',
                                  iterfield=['in_file', 'operand_files'])
        #operations to perform
        #-mas use (following image>0) to mask current image
        zstat_mask.inputs.op_string = '-mas %s'

        easy_thresh.connect(inputnode, 'z_stats', zstat_mask, 'in_file')
        easy_thresh.connect(inputnode, 'mask', zstat_mask, 'operand_files')

        # tfce-corerction
        op_string = '-tfce 2 0.5 6'
        tfce = pe.MapNode(interface=fsl.ImageMaths(suffix='_tfce', op_string=op_string),
                              iterfield=['in_file'],
                              name='tfce')

        easy_thresh.connect(zstat_mask, 'out_file', tfce, 'in_file')

        # estimate image smoothness
        smooth_estimate = pe.MapNode(interface=fsl.SmoothEstimate(),
                                     name='smooth_estimate',
                                     iterfield=['zstat_file', 'mask_file'])

        easy_thresh.connect(tfce, 'out_file', smooth_estimate, 'zstat_file')
        easy_thresh.connect(inputnode, 'mask', smooth_estimate, 'mask_file')

        ptoz = pe.MapNode(interface=myutils.PtoZ(), name='PtoZ',
                          iterfield=['resels'])

        easy_thresh.connect(inputnode, 'p_threshold', ptoz, 'p_val')
        easy_thresh.connect(smooth_estimate, 'resels', ptoz, 'resels')

        thres = pe.MapNode(interface=fsl.Threshold(), name='ThresholdVoxel',
                           iterfield=['in_file', 'thresh'])

        easy_thresh.connect(tfce, 'out_file', thres, 'in_file')
        easy_thresh.connect(ptoz, 'z_score', thres, 'thresh')

        easy_thresh.connect(thres, 'out_file', outputnode, 'thres_zstat')
        easy_thresh.connect(ptoz, 'z_score', outputnode, 'overlay_threshold')

        print('Not implemented!')

    elif (correction=='cluster'):

        inputnode = pe.Node(util.IdentityInterface(fields=['z_stats',
                                                           'mask',
                                                           'z_threshold',
                                                           'p_threshold']),
                             name='inputspec')

        # run clustering
        zstat_mask = pe.MapNode(interface=fsl.MultiImageMaths(),
                                  name='zstat_mask',
                                  iterfield=['in_file', 'operand_files'])
        #operations to perform
        #-mas use (following image>0) to mask current image
        zstat_mask.inputs.op_string = '-mas %s'

        easy_thresh.connect(inputnode, 'z_stats', zstat_mask, 'in_file')
        easy_thresh.connect(inputnode, 'mask', zstat_mask, 'operand_files')

        # estimate image smoothness
        smooth_estimate = pe.MapNode(interface=fsl.SmoothEstimate(),
                                        name='smooth_estimate',
                                        iterfield=['zstat_file', 'mask_file'])

        easy_thresh.connect(zstat_mask, 'out_file', smooth_estimate, 'zstat_file' )
        easy_thresh.connect(inputnode, 'mask', smooth_estimate, 'mask_file' )

         ##cluster-based thresholding
        #After carrying out the initial statistical test, the resulting
        #Z statistic image is then normally thresholded to show which voxels or
        #clusters of voxels are activated at a particular significance level.
        #A Z statistic threshold is used to define contiguous clusters.
        #Then each cluster's estimated significance level (from GRF-theory) is
        #compared with the cluster probability threshold. Significant clusters
        #are then used to mask the original Z statistic image for later production
        #of colour blobs.This method of thresholding is an alternative to
        #Voxel-based correction, and is normally more sensitive to activation.
    #    cluster = pe.MapNode(interface=fsl.Cluster(),
    #                            name='cluster',
    #                            iterfield=['in_file', 'volume', 'dlh'])
    #    #output of cluster index (in size order)
    #    cluster.inputs.out_index_file = True
    #    #thresholded image
    #    cluster.inputs.out_threshold_file = True
    #    #local maxima text file
    #    #defines the cluster cordinates
    #    cluster.inputs.out_localmax_txt_file = True

        cluster = pe.MapNode(interface=fsl.Cluster(out_pval_file='pval.nii.gz', out_threshold_file='thres_clust_zstat.nii.gz'), name='ThresholdClust',
                          iterfield=['in_file', 'dlh', 'volume'])

        easy_thresh.connect(zstat_mask, 'out_file', cluster, 'in_file')
        easy_thresh.connect(inputnode, 'z_threshold', cluster, 'threshold')
        easy_thresh.connect(inputnode, 'p_threshold', cluster, 'pthreshold')
        easy_thresh.connect(smooth_estimate, 'volume', cluster, 'volume')
        easy_thresh.connect(smooth_estimate, 'dlh', cluster, 'dlh')

        easy_thresh.connect(cluster, 'threshold_file', outputnode, 'thres_zstat' )
        easy_thresh.connect(inputnode, 'z_threshold', outputnode, 'overlay_threshold' )
    else:
        print("Error: invalid thresholding correction mode: " + correction)

    return easy_thresh




def overlay(wf_name='overlay', samethres=True):
    """

    samethres: use False in case of voxel-based thresholding, where ptoz must be a mapnode (also in case of TFCE corr)

    - Get the maximum intensity value of the output thresholded image. This used is while rendering the Z statistic image::

        fslstats zstat1_cluster_threshold.nii.gz -R

        arguments
        -R  : output <min intensity> <max intensity>

    - Rendering. For details see `FEAT <http://www.fmrib.ox.ac.uk/fsl/feat5/detail.html#poststats>`_::

        overlay 1 0 MNI152_T1_2mm_brain.nii.gz
               -a zstat1_cluster_threshold.nii.gz
               2.30 15.67
               zstat1_cluster_threshold_overlay.nii.gz

        slicer zstat1_cluster_threshold_overlay.nii.gz
               -L  -A 750
               zstat1_cluster_threshold_overlay.png

      The Z statistic range selected for rendering is automatically calculated by default,
      to run from red (minimum Z statistic after thresholding) to yellow (maximum Z statistic, here
      maximum intensity).
    """
    overl=pe.Workflow(name=wf_name)


    inputnode = pe.Node(util.IdentityInterface(fields=['stat_image',
                                                       'threshold',
                                                       'bg_image']),
                             name='inputspec')

    outputnode = pe.Node(util.IdentityInterface(fields=['overlay_threshold',
                                                        'rendered_image']),
                         name='outputspec')

    #max and minimum intensity values
    image_stats = pe.MapNode(interface=fsl.ImageStats(),
                             name='image_stats',
                             iterfield=['in_file'])
    image_stats.inputs.op_string = '-p 100'


    #create tuple of z_threshold and max intensity value of threshold file
    if (samethres):
        create_tuple = pe.MapNode(util.Function(input_names=['infile_a', 'infile_b'],
                                            output_names=['out_file'],
                                            function=get_tuple),
                                            name='create_tuple',
                                            iterfield=['infile_b'], nested=True)
    else:
        create_tuple = pe.MapNode(util.Function(input_names=['infile_a', 'infile_b'],
                                                output_names=['out_file'],
                                                function=get_tuple),
                                  name='create_tuple',
                                  iterfield=['infile_a', 'infile_b'], nested=True)


    #colour activation overlaying
    overlay = pe.MapNode(interface=fsl.Overlay(),
                            name='overlay',
                            iterfield=['stat_image', 'stat_thresh', 'background_image'])
    overlay.inputs.transparency = True
    overlay.inputs.auto_thresh_bg = True
    overlay.inputs.out_type = 'float'


    #colour rendering
    slicer = pe.MapNode(interface=fsl.Slicer(), name='slicer',
                           iterfield=['in_file'])
    #set max picture width
    slicer.inputs.image_width = 1750
    # set output all axial slices into one picture
    slicer.inputs.all_axial = True


    overl.connect(inputnode, 'stat_image', image_stats, 'in_file')

    overl.connect(image_stats, 'out_stat', create_tuple, 'infile_b')
    overl.connect(inputnode, 'threshold', create_tuple, 'infile_a')

    overl.connect(inputnode, 'stat_image', overlay, 'stat_image')
    overl.connect(create_tuple, 'out_file', overlay, 'stat_thresh')

    overl.connect(inputnode, 'bg_image', overlay, 'background_image')

    overl.connect(overlay, 'out_file', slicer, 'in_file')

    overl.connect(overlay, 'out_file', outputnode, 'overlay_threshold')
    overl.connect(slicer, 'out_file', outputnode, 'rendered_image')

    return overl

def easy_thres(wf_name='threshold', modes=set(['uncorrected', 'voxel', 'tfce', 'cluster'])):

    """
    Perform various types of thresholding for statistical parametric images
    Also produces rendered png images

    TODO: cluster extent and mass based thresholding

    Parameters
    ----------
    modes:  which thresholding to produce
            set containing any of the following strings: 'uncorrected', 'voxel', 'tfce', 'cluster'
            default: set('uncorrected', 'voxel', 'tfce', 'cluster')

    input fields:
    'z_stats',
    'bg_image'
    'mask',
     'z_threshold',
     'p_threshold'

    """

    thr = pe.Workflow(name=wf_name)

    inputnode = pe.Node(util.IdentityInterface(fields=['z_stats',
                                                       'bg_image',
                                                       'mask'
                                                       ]),
                        name='inputspec')

    outputnode = pe.Node(util.IdentityInterface(fields=['thres_uncorr_zstat',
                                                        'thres_clust_zstat',
                                                        'thres_tfce_zstat',
                                                        'thres_vox_zstat',
                                                        'rendered_thres_uncorr_image',
                                                        'rendered_thres_clust_image',
                                                        'rendered_thres_tfce_image',
                                                        'rendered_thres_vox_image'
                                                        ]),
                         name='outputspec')

    if ('uncorrected' in modes):
        ########################################################################################################################
        # threshold individual statistical activation maps
        threshold_uncorr = threshold('thresholdUncorr', correction='uncorrected')
        threshold_uncorr.inputs.inputspec.p_threshold = 0.01
        render_uncorr = overlay('renderUncor')

        thr.connect(inputnode, 'z_stats', threshold_uncorr, 'inputspec.z_stats')
        thr.connect(inputnode, 'mask', threshold_uncorr, 'inputspec.mask')
        thr.connect(inputnode, 'bg_image', render_uncorr, 'inputspec.bg_image')
        thr.connect(threshold_uncorr, 'outputspec.thres_zstat', render_uncorr, 'inputspec.stat_image')
        thr.connect(threshold_uncorr, 'outputspec.overlay_threshold', render_uncorr, 'inputspec.threshold')
        thr.connect(threshold_uncorr, 'outputspec.thres_zstat', outputnode, 'thres_uncorr_zstat')
        thr.connect(render_uncorr, 'outputspec.rendered_image', outputnode, 'rendered_thres_uncorr_image')

        ########################################################################################################################
    if ('cluster' in modes):
        threshold_clust = threshold('thresholdClust', correction='cluster')
        threshold_clust.inputs.inputspec.p_threshold = 0.05
        threshold_clust.inputs.inputspec.z_threshold = 2.3
        render_clust = overlay('renderClust')

        thr.connect(inputnode, 'mask', threshold_clust, 'inputspec.mask')
        thr.connect(inputnode, 'z_stats', threshold_clust, 'inputspec.z_stats')
        thr.connect(inputnode, 'bg_image', render_clust, 'inputspec.bg_image')
        thr.connect(threshold_clust, 'outputspec.thres_zstat', render_clust, 'inputspec.stat_image')
        thr.connect(threshold_clust, 'outputspec.overlay_threshold', render_clust, 'inputspec.threshold')
        thr.connect(threshold_clust, 'outputspec.thres_zstat', outputnode, 'thres_clust_zstat')
        thr.connect(render_clust, 'outputspec.rendered_image', outputnode, 'rendered_thres_clust_image')

        ########################################################################################################################
    if ('voxel' in modes):
        threshold_vox = threshold('thresholdVox', correction='voxel')
        threshold_vox.inputs.inputspec.p_threshold = 0.05
        render_vox = overlay('renderVox', samethres=False)

        thr.connect(inputnode, 'mask', threshold_vox, 'inputspec.mask')
        thr.connect(inputnode, 'z_stats', threshold_vox, 'inputspec.z_stats')
        thr.connect(inputnode, 'bg_image', render_vox, 'inputspec.bg_image')
        thr.connect(threshold_vox, 'outputspec.thres_zstat', render_vox, 'inputspec.stat_image')
        thr.connect(threshold_vox, 'outputspec.overlay_threshold', render_vox, 'inputspec.threshold')
        thr.connect(threshold_vox, 'outputspec.thres_zstat', outputnode, 'thres_vox_zstat')
        thr.connect(render_vox, 'outputspec.rendered_image', outputnode, 'rendered_thres_vox_image')

        ########################################################################################################################
    if ('tfce' in modes):
        threshold_tfce = threshold('thresholdTFCE', correction='tfce')
        threshold_tfce.inputs.inputspec.p_threshold = 0.05
        render_tfce = overlay('renderTFCE', samethres=False)

        thr.connect(inputnode, 'mask', threshold_tfce, 'inputspec.mask')
        thr.connect(inputnode, 'z_stats', threshold_tfce, 'inputspec.z_stats')
        thr.connect(inputnode, 'bg_image', render_tfce, 'inputspec.bg_image')
        thr.connect(threshold_tfce, 'outputspec.thres_zstat', render_tfce, 'inputspec.stat_image')
        thr.connect(threshold_tfce, 'outputspec.overlay_threshold', render_tfce, 'inputspec.threshold')
        thr.connect(threshold_tfce, 'outputspec.thres_zstat', outputnode, 'thres_tfce_zstat')
        thr.connect(render_tfce, 'outputspec.rendered_image', outputnode, 'rendered_thres_tfce_image')
        ########################################################################################################################

    return thr


def get_tuple(infile_a, infile_b):

    """
    Simple method to return tuple of z_threhsold
    maximum intensity values of Zstatistic image
    for input to the overlay.

    Parameters
    ----------
    z_theshold : float
        z threshold value
    intensity_stat : tuple of float values
        minimum and maximum intensity values

    Returns
    -------
    img_min_max : tuple (float)
        tuple of zthreshold and maximum intensity
        value of z statistic image

    """
    out_file = (infile_a, infile_b)
    return out_file
