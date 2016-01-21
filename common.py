#
# common.py
#
# Python utilities for bmk2.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

def load_py_module(f):
    g = {}
    x = execfile(f, g)
    return g
