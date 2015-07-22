
def load_py_module(f):
    g = {}
    x = execfile(f, g)
    return g
