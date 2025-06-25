"""
C/C++ Function Slicer Package

A Python package for performing program slicing on C/C++ functions using tree-sitter.
"""

from .models import SliceType, ParameterSliceResult, Variable, Statement
from .slicer_core import CFunctionSlicer
from .output_utils import (
    print_slice_result, save_slice_to_file, save_combined_slice_to_file,
    print_parameter_slice_result, save_parameter_slice_to_file
)

__version__ = "1.0.0"
__all__ = [
    "SliceType",
    "ParameterSliceResult", 
    "Variable",
    "Statement",
    "CFunctionSlicer",
    "print_slice_result",
    "save_slice_to_file", 
    "save_combined_slice_to_file",
    "print_parameter_slice_result",
    "save_parameter_slice_to_file"
] 