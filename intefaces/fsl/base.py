# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""The fsl module provides classes for interfacing with the `FSL
<http://www.fmrib.ox.ac.uk/fsl/index.html>`_ command line tools.  This
was written to work with FSL version 4.1.4.

These are the base tools for working with FSL.
Preprocessing tools are found in fsl/preprocess.py
Model tools are found in fsl/model.py
DTI tools are found in fsl/dti.py

XXX Make this doc current!

Currently these tools are supported:

* BET v2.1: brain extraction
* FAST v4.1: segmentation and bias correction
* FLIRT v5.5: linear registration
* MCFLIRT: motion correction
* FNIRT v1.0: non-linear warp

Examples
--------
See the docstrings of the individual classes for examples.

"""

from glob import glob
import os
import warnings
from nipype.utils.filemanip import fname_presuffix, split_filename, copyfile
from nipype.interfaces.base import (traits, isdefined,
                                    CommandLine, CommandLineInputSpec, TraitedSpec,
                                    File, Directory, InputMultiPath, OutputMultiPath)
from nipype.interfaces.fsl.base import (FSLCommand, Info, check_fsl, no_fsl, no_fsl_course_data)

warn = warnings.warn
warnings.filterwarnings('always', category=UserWarning)


# FSLCommand =

class Test(object):
    """Test class for writing interface.

    """

    ftypes = {'NIFTI': '.nii',
              'NIFTI_PAIR': '.img',
              'NIFTI_GZ': '.nii.gz',
              'NIFTI_PAIR_GZ': '.img.gz'}

    @staticmethod
    def hello_nipype():
        """Hello Nipype test function
        """
        return 'Hello Nipype!'


class Info(Info):
    """Handle fsl output type and version information.
    
    Inherits from nipype.interfaces.fsl.Info.

    version refers to the version of fsl on the system

    output type refers to the type of file fsl defaults to writing
    eg, NIFTI, NIFTI_GZ

    (Wraps nipype class, standard image modified)

    """

    ftypes = {'NIFTI': '.nii',
              'NIFTI_PAIR': '.img',
              'NIFTI_GZ': '.nii.gz',
              'NIFTI_PAIR_GZ': '.img.gz'}

    @staticmethod
    def standard_image(img_name=None):
        '''Grab an image from the standard location.

        Returns a list of standard images if called without arguments.

        Could be made more fancy to allow for more relocatability'''

        stdpath = '/opt/shared/etc/std/new'  # TODO: get it from environment variable
        if img_name is None:
            return [filename.replace(stdpath + '/', '')
                    for filename in glob(os.path.join(stdpath, '*nii*'))]
        return os.path.join(stdpath, img_name)
