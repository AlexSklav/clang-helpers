# -*- encoding: utf-8 -*-
from .clang_core import (STD_INT_TYPE, STD_INT_KIND, get_stdint_type, _get_argument_type, open_cpp_source,
                         extract_class_declarations, extract_method_signatures, extract_method_signature)

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
