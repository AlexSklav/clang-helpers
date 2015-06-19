'''
Functions to extract a `pandas.DataFrame` describing the return type and
arguments of the methods of a class.

See `get_clang_methods_frame(class_cursor)`.
'''
from collections import OrderedDict

import pandas as pd
from clang.cindex import CursorKind, TypeKind


def resolve_array_type(arg_type):
    declaration = arg_type.get_declaration()
    array_children = list(declaration.get_children())
    array_fields = OrderedDict([(c.displayname, c)
                                for c in array_children if
                                c.displayname])
    length_type = array_fields['length'].type.get_canonical().kind
    atom_type = (array_fields['data'].type.get_pointee()
                 .get_canonical().kind)
    return pd.Series(
        OrderedDict([('length_type', length_type),
                     ('atom_type', atom_type)]))


def _get_c_type_info(clang_type):
    if clang_type.kind == TypeKind.POINTER:
        atom_type = clang_type.get_pointee().get_canonical().kind
        ndims = 1
    elif clang_type.kind == TypeKind.RECORD:
        array_type = resolve_array_type(clang_type)
        atom_type = array_type.atom_type
        ndims = 1
    else:
        atom_type = clang_type.get_canonical().kind
        ndims = 0
    return pd.Series([atom_type, ndims], index=['atom_type', 'ndims'])


def get_clang_method_frame(method_cursor):
    definition = method_cursor.get_definition()
    return_type = _get_c_type_info(definition.result_type)
    name = method_cursor.displayname[:method_cursor.displayname
                                     .index('(')]

    frames = []

    for i, a in enumerate(definition.get_arguments()):
        frame = pd.DataFrame([_get_c_type_info(a.type)])
        frame.insert(0, 'arg_i', i)
        frame.insert(1, 'arg_name', a.displayname)
        frames.append(frame)

    if len(frames):
        clang_sig_info = pd.concat(frames)
        clang_sig_info.insert(0, 'method_name', name)
        clang_sig_info.insert(1, 'return_atom_type',
                              return_type.atom_type)
        clang_sig_info.insert(2, 'return_ndims', return_type.ndims)
        clang_sig_info.insert(3, 'arg_count', clang_sig_info.shape[0])
    else:
        clang_sig_info = pd.DataFrame([[name, return_type.atom_type,
                                        return_type.ndims, 0]],
                                      columns=['method_name',
                                               'return_atom_type',
                                               'return_ndims',
                                               'arg_count'])
    return clang_sig_info


def get_clang_methods_frame(class_cursor):
    frames = []

    for m in class_cursor.get_children():
        if m.kind == CursorKind.CXX_METHOD:
            frame = get_clang_method_frame(m)
            frames.append(frame)

    return pd.concat(frames)[['method_name', 'return_atom_type',
                              'return_ndims', 'arg_count', 'arg_i',
                              'arg_name',
                              'atom_type']].reset_index(drop=True)