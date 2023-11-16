"""
Functions to extract a `pandas.DataFrame` describing the return type and
arguments of the methods of a class.

See `get_clang_methods_frame(class_cursor)`.
"""
import numpy as np
import pandas as pd

from typing import Optional
from clang.cindex import CursorKind, TypeKind
from .clang_core import STD_INT_TYPE


def underscore_to_camelcase(value: str) -> str:
    """Convert underscore-separated string to camelCase."""
    return ''.join(x.capitalize() if x else '_' for x in value.split('_'))


def resolve_array_type(arg_type: CursorKind.__class__) -> dict:
    """
    Resolve array type.

    Parameters
    ----------
    arg_type : Cursor
        Type of the array argument.

    Returns
    -------
    pd.Series
        Series containing resolved array type information.
    """
    declaration = arg_type.get_declaration()
    array_children = list(declaration.get_children())
    array_fields = {c.displayname: c for c in array_children if c.displayname}
    length_type = array_fields['length'].type.get_canonical().kind
    atom_type = array_fields['data'].type.get_pointee().get_canonical().kind
    return {'length_type': length_type, 'atom_type': atom_type}


def _get_c_type_info(clang_type: TypeKind.__class__, name=None) -> dict:
    if clang_type.kind == TypeKind.POINTER:
        atom_type = clang_type.get_pointee().get_canonical().kind
        ndims = 1
    elif clang_type.kind == TypeKind.RECORD:
        array_type = resolve_array_type(clang_type)
        atom_type = array_type['atom_type']
        ndims = 1
    elif clang_type.kind == TypeKind.ELABORATED:
        # Some arrays are hidden in elaborated, so make sure to catch them
        return _get_c_type_info(clang_type.get_canonical())
    else:
        atom_type = clang_type.get_canonical().kind
        ndims = 0
    return {'atom_type': atom_type, 'ndims': ndims}


def get_clang_method_frame(method_cursor) -> pd.DataFrame:
    definition = method_cursor.get_definition()
    if definition is None:
        # `get_definition()` returns `None` for pure virtual C++ methods.
        # For the case of pure virtual methods, the definition is the method
        # cursor itself.
        definition = method_cursor

    name = method_cursor.displayname[:method_cursor.displayname.index('(')]

    return_type = _get_c_type_info(definition.result_type, name)

    frames = []

    for i, a in enumerate(definition.get_arguments()):
        c_type_info = _get_c_type_info(a.type, name)
        c_type_info.update({'arg_i': i, 'arg_name': a.displayname})
        frames.append(pd.DataFrame(c_type_info, index=[0]))

    if len(frames):
        clang_sig_info = pd.concat(frames, ignore_index=True)
        clang_sig_info['method_name'] = name
        clang_sig_info['return_atom_type'] = return_type['atom_type']
        clang_sig_info['return_ndims'] = return_type['ndims']
        clang_sig_info['arg_count'] = clang_sig_info.shape[0]
    else:
        clang_sig_info = pd.DataFrame([[name, return_type['atom_type'], return_type['ndims'], 0]],
                                      columns=['method_name', 'return_atom_type', 'return_ndims', 'arg_count'])

    return clang_sig_info


def get_clang_methods_frame(class_cursor, std_types: Optional[bool] = True) -> pd.DataFrame:
    """
    Get DataFrame containing Clang methods.

    Parameters
    ----------
    class_cursor: Cursor
        Clang cursor for the class.
    std_types: bool, Optional
        Include standard types, by default True.

    Returns
    -------
    pd.DataFrame
        DataFrame containing Clang methods.
    """

    frames = [get_clang_method_frame(m) for m in class_cursor.get_children() if m.kind == CursorKind.CXX_METHOD]
    # from pprint import pprint
    # pprint([m.displayname for m in class_cursor.get_children() if m.kind == CursorKind.CXX_METHOD])

    if frames:
        result = pd.concat(frames, ignore_index=True)
        result = result.replace(np.nan, None)

        if 'atom_type' not in result.columns:
            result['arg_i'] = None
            result['arg_name'] = None
            result['atom_type'] = None
            result['ndims'] = None

        if std_types:
            # Replace clang type instances with standard C type names.
            result.loc[:, 'return_atom_type'] = result.return_atom_type.map(STD_INT_TYPE)
            result.loc[result.arg_count > 0, 'atom_type'] = result.loc[result.arg_count > 0, 'atom_type'].map(STD_INT_TYPE)

        result['camel_name'] = result.method_name.map(underscore_to_camelcase)
        method_i = {method: i for i, method in enumerate(result.method_name.unique())}
        result['method_i'] = result.method_name.map(method_i)

        return result.loc[:, ['method_i', 'method_name', 'camel_name', 'return_atom_type', 'return_ndims',
                              'arg_count', 'arg_i', 'arg_name', 'atom_type', 'ndims']].reset_index(drop=True)
