
from math import sqrt

def sobstitute(cmd, conf):
    new_cmd = cmd
    old_cmd = None
    while new_cmd != old_cmd:
        old_cmd = new_cmd
        new_cmd = new_cmd.format(**conf.parameters)
    return new_cmd

def convert(val):
    if val is None:
        return None
    try:
        val = int(val)
    except ValueError:
        # the value is not an float, try with int
        try:
            val = float(val)
        except ValueError:
            # the val is not a float, keep it
            pass
    return val

def toStr(val):
    if type(val) == float:
        return "{0:.5f}".format(val)
    return '{0}'.format(val)
    
def avg(values):
    acc = 0.0
    for val in values:
        acc += val
    return acc/len(values)
    
def std(values, avg):
    acc = 0.0
    for val in values:
        acc += (val - avg)**2
    return sqrt(acc/len(values))

def gen_file_name(name):
    import os
    return os.path.dirname(name) + "/~" + os.path.basename(name)