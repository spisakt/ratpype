# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""The fsl module provides classes for interfacing with the `FSL
<http://www.fmrib.ox.ac.uk/fsl/index.html>`_ command line tools.  This
was written to work with FSL version 4.1.4.

Examples
--------
See the docstrings of the individual classes for examples.

    Change directory to provide relative paths for doctests
    >>> import os
    >>> filepath = os.path.dirname( os.path.realpath( __file__ ) )
    >>> datadir = os.path.realpath(os.path.join(filepath, '../../testing/data'))
    >>> os.chdir(datadir)
"""

#import os
#from glob import glob
#import warnings
#import tempfile

#import numpy as np

#from .base import FSLCommand, FSLCommandInputSpec, Info
#from nipype.interfaces.base import (traits, TraitedSpec, OutputMultiPath, File,
#                    CommandLine, CommandLineInputSpec, isdefined)
#from nipype.interfaces.utils.filemanip import (load_json, save_json, split_filename,
#                                fname_presuffix)

#warn = warnings.warn
#warnings.filterwarnings('always', category=UserWarning)



from nipype.interfaces.fsl.utils import *


def run_resample(in_file, like):
    import os
    from glob import glob
    from nipype.interfaces.base import CommandLine

    #cmd = ("palm -i {cope_file} -m {mask_file} -d {design_file} -t {contrast_file} -eb {group_file} -T "
    #   "-fdr -noniiclass -twotail -logp -zstat")
    cmd = ("rg_realign {in_file} {like} resampled trf.mat")

    cl = CommandLine(cmd.format(in_file=in_file, like=like))
    results = cl.run(terminal_output='file')
    return os.path.join(os.getcwd(), 'trf.mat')


class ChangePixDimInputSpec(FSLCommandInputSpec):
    xdim = traits.Float(12, position=1, argstr='%.6f',
                                   desc='voxel size in x dimension', mandatory=True)
    ydim = traits.Float(12,position=2, argstr='%.6f',
                                   desc='voxel size in y dimension', mandatory=True)
    zdim = traits.Float(12,position=3, argstr='%.6f',
                                   desc='voxel size in z dimension', mandatory=True)
    tdim = traits.Float(position=4, argstr='%.6f',
                                   desc='voxel size in t dimension')

    in_file = File(exists=True,
                   desc='input file',
                   argstr='%s', position=1, mandatory=True) #hack: position

    out_file = File(exists=False,
                   desc='output file',
                   argstr='%s', position=0)
    


class ChangePixDimOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc='rescaled image')

class ChangePixDim(FSLCommand):
    """ Use fslchpixdim to change voxel size in image header
    Currently modifies input (TODO: create separate output image?)

    """
    _cmd = 'fslchpixdim'
    input_spec = ChangePixDimInputSpec
    output_spec = ChangePixDimOutputSpec

    def _run_interface(self, runtime):
        # cp input_image output_image
        from shutil import copyfile
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file,
                                                  suffix='_rescaled')
        self.inputs.out_file = self._gen_fname( self.inputs.out_file)
        print("Copying " + self.inputs.in_file + " to " + self.inputs.out_file)
        copyfile(self.inputs.in_file, self.inputs.out_file)
        #self.inputs.in_file = self.inputs.out_file
        runtime = super(ChangePixDim, self)._run_interface(runtime)
        return runtime


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['out_file'] = self.inputs.out_file

        outputs['out_file'] = os.path.abspath(outputs['out_file'])
        return outputs


 

class ImageInfoInputSpec(FSLCommandInputSpec):

    in_file = File(exists=True,
                   desc='input file',
                   argstr='%s', position=0, mandatory=True) 

class ImageInfoOutputSpec(TraitedSpec):
    out_data_type = traits.Any(desc='info output')
    out_dim1 = traits.Float(desc='info output')
    out_dim2 = traits.Float(desc='info output')
    out_dim3 = traits.Float(desc='info output')
    out_dim4 = traits.Float(desc='info output')
    out_datatype = traits.Float(desc='info output')
    out_pixdim1 = traits.Float(desc='info output')
    out_pixdim2 = traits.Float(desc='info output')
    out_pixdim3 = traits.Float(desc='info output')
    out_pixdim4 = traits.Float(desc='info output')
    out_cal_max = traits.Float(desc='info output')
    out_cal_min = traits.Float(desc='info output')
    out_file_type = traits.Any(desc='info output')
    
class ImageInfo(FSLCommand):
    """ Image information by fslinfo

    """
    _cmd = 'fslinfo'
    input_spec = ImageInfoInputSpec
    output_spec = ImageInfoOutputSpec

    def _format_arg(self, name, trait_spec, value):
        return super(ImageInfo, self)._format_arg(name, trait_spec, value)

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()

        # local caching for backward compatibility
        outfile = os.path.join(os.getcwd(), 'image_info.json')
        if runtime is None:
            try:
                print('json')
                json=load_json(outfile)
                #outputs.out_data_type = json['out_data_type']
                outputs.out_dim1 = json['out_dim1']
                outputs.out_dim2 = json['out_dim2']
                outputs.out_dim3 = json['out_dim3']
                outputs.out_dim4 = json['out_dim4']
                outputs.out_datatype = json['out_datatype']
                outputs.out_pixdim1 = json['out_pixdim1']
                outputs.out_pixdim2 = json['out_pixdim2']
                outputs.out_pixdim3 = json['out_pixdim3']
                outputs.out_pixdim4 = json['out_pixdim4']
                outputs.out_cal_max = json['out_cal_max']
                outputs.out_cal_min = json['out_cal_min']
                outputs.out_file_type = json['out_file_type']
            except IOError:
                return self.run().outputs
        else:

            for line in runtime.stdout.split('\n'):
                tokens=line.split()
                if (len(tokens)>1):
                    tag=tokens[0]
                    value=tokens[1]
                    if (tag=='data_type'):
                        outputs.out_data_type=value
                    elif (tag=='dim1'):
                        outputs.out_dim1 = float(value)
                    elif (tag=='dim2'):
                        outputs.out_dim2 = float(value)
                    elif (tag=='dim3'):
                        outputs.out_dim3 = float(value)
                    elif (tag=='dim4'):
                        outputs.out_dim4 = float(value)
                    elif (tag=='datatype'):
                        outputs.out_datatype = float(value)
                    elif (tag=='pixdim1'):
                        outputs.out_pixdim1 = float(value)
                    elif (tag=='pixdim2'):
                        outputs.out_pixdim2 = float(value)
                    elif (tag=='pixdim3'):
                        outputs.out_pixdim3 = float(value)
                    elif (tag=='pixdim4'):
                        outputs.out_pixdim4 = float(value)
                    elif (tag=='cal_max'):
                        outputs.out_cal_max = float(value)
                    elif (tag=='cal_min'):
                        outputs.out_cal_min = float(value)
                    elif (tag=='file_type'):
                        outputs.out_file_type =value

            save_json(outfile, dict(info=outputs.out_data_type))
            save_json(outfile, dict(info=outputs.out_dim1))
            save_json(outfile, dict(info=outputs.out_dim2))
            save_json(outfile, dict(info=outputs.out_dim3))
            save_json(outfile, dict(info=outputs.out_dim4))
            save_json(outfile, dict(info=outputs.out_datatype))
            save_json(outfile, dict(info=outputs.out_pixdim1))
            save_json(outfile, dict(info=outputs.out_pixdim2))
            save_json(outfile, dict(info=outputs.out_pixdim3))
            save_json(outfile, dict(info=outputs.out_pixdim4))
            save_json(outfile, dict(info=outputs.out_cal_max))
            save_json(outfile, dict(info=outputs.out_cal_min ))
            save_json(outfile, dict(info=outputs.out_file_type))

        return outputs



class Reorient2StdInputSpec(Reorient2StdInputSpec):
    in_file = File(exists=True, mandatory=True, argstr="%s")
    out_file = File(genfile=True, hash_files=False, argstr="%s")


class Reorient2StdOutputSpec(Reorient2StdOutputSpec):
    out_file = File()


class Reorient2Std(Reorient2Std):
    """fslreorient2std is a tool for reorienting the image to match the
    approximate orientation of the standard template images (MNI152).


    Examples
    --------

    >>> reorient = Reorient2Std()
    >>> reorient.inputs.in_file = "functional.nii"
    >>> res = reorient.run() # doctest: +SKIP


    """
    _cmd = 'fslinfo'
    input_spec = Reorient2StdInputSpec
    output_spec = Reorient2StdOutputSpec

    def _gen_filename(self, name):
        if name == 'out_file':
            return self._gen_fname(self.inputs.in_file,
                                   suffix="_reoriented")
        return None

    def _list_outputs(self):
        outputs = self.output_spec().get()
        if not isdefined(self.inputs.out_file):
            outputs['out_file'] = self._gen_filename('out_file')
        else:
            outputs['out_file'] = os.path.abspath(self.inputs.out_file)
        return outputs



class PtoZInputSpec(FSLCommandInputSpec):
    p_val = traits.Float(12, position=1, argstr='%.6f',
                                   desc='p-value to convert', mandatory=True)
    resels = traits.Float(12, position=2, argstr='-g %.6f',
                                   desc='use GRF maximum-height theory instead of Gaussian pdf (based on resels output of FSL smoothest)', mandatory=False)
    twotail = traits.Bool(
        argstr="-2", desc='use 2-tailed conversion (default is 1-tailed)')


class PtoZOutputSpec(TraitedSpec):
    z_score = traits.Float(desc='Z-score')


class PtoZ(FSLCommand):
    """PtoZ is a tool for converting P value to Z score in an uncorrected or corrected manner.


    Examples
    --------

    >>> ptoz = PtoZ()
    >>> ptoz.inputs.p_val = 0.05
    >>> ptoz.inputs.
    >>> res = ptoz.run() # doctest: +SKIP


    """
    _cmd = 'ptoz'
    input_spec = PtoZInputSpec
    output_spec = PtoZOutputSpec

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        outputs.z_score = float(runtime.stdout)
        return outputs


class ZtoPInputSpec(FSLCommandInputSpec):
    z_score = traits.Float(12, position=1, argstr='%.6f',
                                   desc='Z-score to convert', mandatory=True)
    twotail = traits.Bool(
        argstr="-2", desc='use 2-tailed conversion (default is 1-tailed)')


class ZtoPOutputSpec(TraitedSpec):
    p_val = traits.Float(desc='P-value')


class ZtoP(FSLCommand):
    """ZtoP is a tool for converting Z score to P value (uncorrected).


    Examples
    --------

    >>> ztop = ZtoP()
    >>> ztop.inputs.z_score = 2.3
    >>> res = ztop.run() # doctest: +SKIP


    """
    _cmd = 'ztop'
    input_spec = ZtoPInputSpec
    output_spec = ZtoPOutputSpec

    def aggregate_outputs(self, runtime=None, needed_outputs=None):
        outputs = self._outputs()
        outputs.p_val = float(runtime.stdout)
        return outputs

