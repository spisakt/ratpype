from nipype import config
from nipype.interfaces import spm, fsl

import nipype.interfaces.io as nio  # Data i/o
import nipype.interfaces.fsl as fsl  # fsl
import nipype.interfaces.utility as util  # utility
import nipype.pipeline.engine as pe  # pypeline engine
import nipype.algorithms.modelgen as model  # model generation
import nipype.algorithms.rapidart as ra  # artifact detection
import nipype.workflows.fmri.fsl.preprocess as preproc
import nipype.interfaces.afni as afni  # afni

def highpass_operand(high_pass_filter_cutoff, TR):
    return '-bptf %.10f -1' % (high_pass_filter_cutoff/(2*TR))

# TODO: parametrize size of ev-s and regressors

def get_subject_info(ev_file, confounders):
    from nipype.interfaces.base import Bunch

    def get_col(in_file, col):
        matrix = []

        with open(in_file, 'rU') as f:
            matrix = [filter(None, l.split()) for l in f]

        column = []
        for row in matrix:
            try:
                column.append(float(row[col]))
            except IndexError:
                # pass
                #column.append("")
                return column
        return column


    subjectinfo = Bunch(conditions=['whisker'],
                        onsets=[get_col(ev_file, 0)],
                        #onsets=[[1,10,20,30]],
                        durations=[get_col(ev_file, 1)],
                        #durations=[[1,1,1,1]],
                        amplitudes=[get_col(ev_file, 2)],
                        #amplitudes=[[1,1,1,1]],
                        tmod=None,
                        pmod=None,
                        regressor_names=['cc1', 'cc2', 'cc3', 'cc4', 'cc5', 'cc6'],
                        regressors=[get_col(confounders, 0),
                                    get_col(confounders, 1),
                                    get_col(confounders, 2),
                                    get_col(confounders, 3),
                                    get_col(confounders, 4),
                                    get_col(confounders, 5)]
                        )
    return subjectinfo

def run_palm(cope_file, design_file, contrast_file, group_file, mask_file,
                 cluster_threshold=2.3):
    import os
    from glob import glob
    from nipype.interfaces.base import CommandLine

    cmd = ("palm -i {cope_file} -m {mask_file} -d {design_file} -t {contrast_file} -eb {group_file} -T "
           "-fdr -noniiclass -twotail -logp -zstat")


    cl = CommandLine(cmd.format(cope_file=cope_file, mask_file=mask_file, design_file=design_file,
                                contrast_file=contrast_file,
                                group_file=group_file, cluster_threshold=cluster_threshold))
    results = cl.run(terminal_output='file')
    return [os.path.join(os.getcwd(), val) for val in sorted(glob('palm*'))]

def run_rand(cope_file, design_file, contrast_file, group_file, mask_file,
                 cluster_threshold=2.3, n=10000):


    import os
    from glob import glob
    from nipype.interfaces.base import CommandLine

    cmd = ("randomise -i {cope_file} -m {mask_file} -d {design_file} -t {contrast_file} -e {group_file} -T "
           "-c {cluster_threshold} -x -n {n}")

    cl = CommandLine(cmd.format(cope_file=cope_file, mask_file=mask_file, design_file=design_file,
                                contrast_file=contrast_file,
                                group_file=group_file, cluster_threshold=cluster_threshold, n=n))
    results = cl.run(terminal_output='file')
    return [os.path.join(os.getcwd(), val) for val in sorted(glob('rand*'))]

def run_rand_par(cope_file, design_file, contrast_file, group_file, mask_file,
                 cluster_threshold=2.3, n=10000):
    import os
    from glob import glob
    from nipype.interfaces.base import CommandLine

    cmd = ("randomise_parallel -i {cope_file} -o rand -m {mask_file} -d {design_file} -t {contrast_file} -e {group_file} -T "
           "-c {cluster_threshold} -x -n {n}")

    cl = CommandLine(cmd.format(cope_file=cope_file, mask_file=mask_file, design_file=design_file,
                                contrast_file=contrast_file,
                                group_file=group_file, cluster_threshold=cluster_threshold, n=n))
    results = cl.run(terminal_output='file')
    return [os.path.join(os.getcwd(), val) for val in sorted(glob('rand*'))]


def modelfit_fsl(wf_name='modelfit'):

    """

    Fit 1st level GLM using FSL routines

    Usage (TODO)

    modelfit.inputs.inputspec.fwhm = 12
    modelfit.inputs.inputspec.brain_mask = ['/opt/shared2/nipype-test/testblock/example_func_brain_mask.nii.gz', '/opt/shared2/nipype-test/testblock/example_func_brain_mask.nii.gz']

    modelfit.inputs.inputspec.input_units = 'secs'
    modelfit.inputs.inputspec.in_file = ['/opt/shared2/nipype-test/testblock/mc_data_brain.nii.gz', '/opt/shared2/nipype-test/testblock/mc_data_brain.nii.gz']
    modelfit.inputs.inputspec.TR = 2
    modelfit.inputs.inputspec.high_pass_filter_cutoff = 100 #sigma in TR
    modelfit.inputs.inputspec.event_files = ['/opt/shared2/nipype-test/testblock/a']

    cont1 = ['whisker', 'T', ['a', 'a'], [1.0, 0.0]]
    cont2 = ['-whisker', 'T', ['a', 'a'], [-1.0, 0.0]]
    cont3 = ['Task','F', [cont1, cont2]]
    contrasts = [cont1]

    modelfit.inputs.inputspec.contrasts = contrasts #TODO: change condition names

    modelfit.inputs.inputspec.bases_function = {'dgamma': {'derivs':  True}}
    modelfit.inputs.inputspec.model_serial_correlations = True


    #modelfit.write_graph('graph.dot');
    modelfit.write_graph('graph.dot', graph2use='colored');
    x=modelfit.run()
    #x=modelfit.run(plugin='MultiProc', plugin_args={'n_procs': 8})

    server.serve_content(modelfit)
    """

    modelfit = pe.Workflow(name=wf_name)

    """
        Set up a node to define all inputs required for the preprocessing workflow

    """

    inputnode = pe.Node(
        interface=util.IdentityInterface(fields=['in_file', 'ev_file', 'confounders', 'contrasts', 'high_pass_filter_cutoff', 'fwhm',
                                                 'interscan_interval', 'TR', 'input_units',
                                                 'bases_function', 'model_serial_correlations', 'brain_mask'],
                                         mandatory_inputs=True), name='inputspec')

    #TODO: eliminate brain mask


    #inputnode.iterables=[('high_pass_filter_cutoff', [30, 60, 90, 120, 500])]

    """
        Set up a node to define outputs for the preprocessing workflow

    """

    outputnode = pe.Node(interface=util.IdentityInterface(fields=['zstats', 'zfstats', 'copes', 'varcopes'],
                                                          mandatory_inputs=True),
                         name='outputspec')

    # collect subject info

    getsubjectinfo = pe.MapNode(util.Function(input_names=['ev_file', 'confounders'],
                                   output_names=['subject_info'],
                                   function=get_subject_info),
                          name='getsubjectinfo', iterfield=['confounders'])

    # nipype.algorithms.modelgen.SpecifyModel to generate design information.

    modelspec = pe.MapNode(interface=model.SpecifyModel(), name="modelspec", iterfield=['subject_info'])

    # smooth #TODO: move into preproc pipeline

    smooth = preproc.create_susan_smooth("smooth")
    #smooth.get_node( "smooth").iterables=[('fwhm', [6., 8., 10., 12., 14., 16.])]


    toSigma = pe.Node(interface=util.Function(input_names=['high_pass_filter_cutoff', 'TR'],
                                                 output_names=['high_pass_filter_opstring'],
                                                 function=highpass_operand),
                         name='toSigma')

    highpass = pe.MapNode(interface=fsl.ImageMaths(suffix='_tempfilt', op_string=''),
                          iterfield=['in_file'],
                          name='highpass')

    # Use nipype.interfaces.fsl.Level1Design to generate a run specific fsf file for analysis

    level1design = pe.MapNode(interface=fsl.Level1Design(), name="level1design", iterfield='session_info')

    # Use nipype.interfaces.fsl.FEATModel to generate a run specific mat file for use by FILMGLS

    modelgen = pe.MapNode(interface=fsl.FEATModel(), name='modelgen',
                          iterfield=['fsf_file', 'ev_files'])

    # Use nipype.interfaces.fsl.FILMGLS to estimate a model specified by a mat file and a functional run

    modelestimate = pe.MapNode(interface=fsl.FILMGLS(smooth_autocorr=True,
                                                     mask_size=5,
                                                     threshold=200),
                               name='modelestimate',
                               #iterfield=['design_file', 'in_file'])
                                iterfield=['in_file', 'design_file'])

    # Use nipype.interfaces.fsl.ContrastMgr to generate contrast estimates

    conestimate = pe.MapNode(interface=fsl.ContrastMgr(), name='conestimate',
                             iterfield=['param_estimates',
                                        'sigmasquareds',
                                        'corrections',
                                        'dof_file',
                                        'tcon_file'])



    modelfit.connect([
        (inputnode, smooth, [('in_file', 'inputnode.in_files'),
                             ('fwhm', 'inputnode.fwhm'),    # in iterable
                             ('brain_mask', 'inputnode.mask_file')]),
        (smooth, highpass, [('outputnode.smoothed_files', 'in_file')]),

        (inputnode, toSigma, [('high_pass_filter_cutoff', 'high_pass_filter_cutoff')]),
        (inputnode, toSigma, [('TR', 'TR')]),
        (toSigma, highpass, [('high_pass_filter_opstring', 'op_string')]),

        (inputnode, getsubjectinfo, [('ev_file', 'ev_file'),
                                     ('confounders', 'confounders')]),
        (getsubjectinfo, modelspec, [('subject_info', 'subject_info')]),

        (highpass, modelspec, [('out_file', 'functional_runs')]),
        (highpass, modelestimate, [('out_file', 'in_file')]),
        (inputnode, modelspec, [('input_units', 'input_units'),
                                ('TR', 'time_repetition'),
                                ('high_pass_filter_cutoff', 'high_pass_filter_cutoff'),
                                ]),
        (inputnode, level1design, [('TR', 'interscan_interval'),
                                   ('model_serial_correlations', 'model_serial_correlations'),
                                   ('bases_function', 'bases'),
                                   ('contrasts', 'contrasts')]),
        (modelspec, level1design, [('session_info', 'session_info')]),
        (level1design, modelgen, [('fsf_files', 'fsf_file'),
                                  ('ev_files', 'ev_files')]),
        (modelgen, modelestimate, [('design_file', 'design_file')]),
        (modelgen, conestimate, [('con_file', 'tcon_file')]),
        (modelestimate, conestimate, [('param_estimates', 'param_estimates'),
                                      ('sigmasquareds', 'sigmasquareds'),
                                      ('corrections', 'corrections'),
                                      ('dof_file', 'dof_file')]),
        (conestimate, outputnode, [('zstats','zstats'),
                                   ('zfstats','zfstats'),
                                   ('copes', 'copes'),
                                   ('varcopes','varcopes')])
    ])

    return modelfit

def modelfit_2ndlevel(wf_name='2nd_level_modelfit', method='flameo', standardize=True): #TODO: standardization in sepatae workflow!

    #method is one of 'flameo' or 'palm' or 'randomise' or 'randomise_parallel'

    model = pe.Workflow(name=wf_name)

    """
        Set up a node to define all inputs required for the preprocessing workflow

    """

    inputnode = pe.Node(
        interface=util.IdentityInterface(
            fields=['copes', 'varcopes', 'func2anat_mat', 'std_brain', 'anat_to_std_warp', 'std_brain_mask', 'regressors', 'contrasts', 'groups'], # TODO: groups!!
            mandatory_inputs=True), name='inputspec')

    """
        Set up a node to define outputs for the preprocessing workflow

    """

    outputnode = pe.Node(interface=util.IdentityInterface(fields=['zstats'],
                                                          mandatory_inputs=True),
                         name='outputspec')


    ###################################################################################################
    # merge copes
    copemerge = pe.Node(interface=fsl.Merge(dimension='t'),
                        name="copemerge")

    # standardize copes and varcopes
    if (standardize):

        applyWarpCope = pe.MapNode(interface=fsl.ApplyWarp(interp='sinc'), name="warp_cope",
                               iterfield=['in_file', 'field_file', 'premat'])


        model.connect(inputnode, 'func2anat_mat', applyWarpCope, 'premat')
        model.connect(inputnode, 'copes', applyWarpCope, 'in_file')
        model.connect(inputnode, 'std_brain', applyWarpCope, 'ref_file')
        model.connect(inputnode, 'anat_to_std_warp', applyWarpCope, 'field_file')
        model.connect(applyWarpCope, 'out_file', copemerge, 'in_files')
    else:
        model.connect(inputnode, 'copes', copemerge, 'in_files')




    if (method=='flameo'): # same for varcopes if flameo

        varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),
                               name="varcopemerge")

        if (standardize):
            applyWarpVarcope = pe.MapNode(interface=fsl.ApplyWarp(interp='sinc'), name="warp_varcope",
                                       iterfield=['in_file', 'field_file', premat])

            model.connect(inputnode, 'func2anat_mat', applyWarpVarcope, 'premat')
            model.connect(inputnode, 'varcopes', applyWarpVarcope, 'in_file')
            model.connect(inputnode, 'std_brain', applyWarpVarcope, 'ref_file')
            model.connect(inputnode, 'anat_to_std_warp', applyWarpVarcope, 'field_file')

            model.connect(applyWarpVarcope, 'out_file', varcopemerge, 'in_files')
        else:
            model.connect(inputnode, 'varcopes', varcopemerge, 'in_files')


    #level2model = pe.Node(interface=fsl.L2Model(num_copes=35),
    #                     name='l2model')

    level2model=pe.Node(interface=fsl.MultipleRegressDesign(), name='design')

    model.connect(inputnode, 'regressors', level2model, 'regressors')
    model.connect(inputnode, 'contrasts', level2model, 'contrasts')
    model.connect(inputnode, 'groups', level2model, 'groups')

    if (method == 'flameo'):
        flameo = pe.Node(interface=fsl.FLAMEO(run_mode='fe'), name="flameo")

        model.connect([
            (inputnode, flameo, [('std_brain_mask', 'mask_file')]),
            (copemerge, flameo, [('merged_file', 'cope_file')]),
            (varcopemerge, flameo, [('merged_file', 'var_cope_file')]),
            (level2model, flameo, [('design_mat', 'design_file'),
                                   ('design_con', 't_con_file'),
                                   ('design_grp', 'cov_split_file')]),
            (flameo, outputnode, [('zstats', 'zstats')])
                      ])
    elif (method == 'palm'):
        palm = pe.Node(util.Function(input_names=['cope_file', 'design_file', 'contrast_file',
                                          'group_file', 'mask_file', 'cluster_threshold'],
                             output_names=['palm_outputs'],
                             function=run_palm),
                    name='palm')

        model.connect([
            (inputnode, palm, [('std_brain_mask', 'mask_file')]),
            (copemerge, palm, [('merged_file', 'cope_file')]),
            (level2model, palm, [('design_mat', 'design_file'),
                                   ('design_con', 'contrast_file'),
                                   ('design_grp', 'group_file')]),
            (palm, outputnode, [('palm_outputs', 'zstats')])
            ])
        palm.inputs.cluster_threshold = 2.3 #TODO: make parametrizable
        palm.plugin_args = {'sbatch_args': '-p om_all_nodes -N1 -c2 --mem=10G', 'overwrite': True}
    elif (method == 'randomise'):
        rand=pe.Node(util.Function(input_names=['cope_file', 'design_file', 'contrast_file',
                                          'group_file', 'mask_file', 'cluster_threshold', 'n'],
                             output_names=['palm_outputs'],
                             function=run_rand),
                    name='randomise')

        model.connect([
            (inputnode, rand, [('std_brain_mask', 'mask_file')]),
            (copemerge, rand, [('merged_file', 'cope_file')]),
            (level2model, rand, [('design_mat', 'design_file'),
                                   ('design_con', 'contrast_file'),
                                   ('design_grp', 'group_file')]),
            (rand, outputnode, [('palm_outputs', 'zstats')])
            ])
        rand.inputs.cluster_threshold = 2.3 #TODO: make parametrizable
        rand.inputs.n=1000
        #rand.plugin_args = {'sbatch_args': '-p om_all_nodes -N1 -c2 --mem=10G', 'overwrite': True}
    elif (method == 'randomise_parallel'):
        rand = pe.Node(util.Function(input_names=['cope_file', 'design_file', 'contrast_file',
                                                  'group_file', 'mask_file', 'cluster_threshold', 'n'],
                                     output_names=['palm_outputs'],
                                     function=run_rand_par),
                       name='randomise')

        model.connect([
            (inputnode, rand, [('std_brain_mask', 'mask_file')]),
            (copemerge, rand, [('merged_file', 'cope_file')]),
            (level2model, rand, [('design_mat', 'design_file'),
                                 ('design_con', 'contrast_file'),
                                 ('design_grp', 'group_file')]),
            (rand, outputnode, [('palm_outputs', 'zstats')])
        ])
        rand.inputs.cluster_threshold = 2.3  # TODO: make parametrizable
        rand.inputs.n = 1000
        #rand.plugin_args = {'sbatch_args': '-p om_all_nodes -N1 -c2 --mem=10G', 'overwrite': True}

    else:
        print('Error: No such 2nd-level statistical model method: ' + method)

    return model