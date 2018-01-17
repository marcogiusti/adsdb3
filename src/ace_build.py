# Copyright (c) 2018 Marco Giusti

import os.path
from cffi import FFI


curdir = os.path.abspath(os.path.dirname(__file__))

c_source = r'''
#include "ace.h"
'''

ffibuilder = FFI()
ffibuilder.set_source(
    '_ace',
    c_source,
    libraries=['ace'],
    include_dirs=[curdir]
)
ffibuilder.cdef(open(os.path.join('src', 'ace.h')).read())


if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
