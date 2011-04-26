'''
    BenchRunner 
    Copyright (C) 2010  Simone Pellegrini

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

from parameter import Parameter, OutOfBoundsExcection
from copy import deepcopy
import functools, math
from util import sobstitute, convert, avg, std, toStr
import os, threading

class Constrain:
    def __init__(self, inv):
        self.__constrain = inv
        
    @property
    def constrain(self):
        return self.__constrain
    
    def check(self, conf):
        try:
            con = sobstitute(self.__constrain, conf)
            ret = eval(con)
            if not ret:
                print "Failed to satisfy constrain: {0}".format(con)
        except KeyError, err:
            # print ("Warning: invariant '{0}' couldn't be checked"
            #        "for the current configuration.").format(self.__constrain)
            return True
        except SyntaxError, err:
            raise "SyntaxError in constrain '{0}' -> {1}".format(self.__constrain, con)
        return ret
    
    def __str__(self):
        return str(self.__constrain)
    
    def __eq__(self, other):
        return self.constrain == other.constrain
    
    def __hash__(self):
        return hash(self.__constrain)

def intersect(param_list):
    params = list(param_list)
    if params is None or len(params) == 0:
        return []
    
    diff = set(params[0])
    for it in params[1:]:
        diff &= set(it)
    return diff


class Configuration:
    
    def __init__(self):
        self.__parameters = {}
        self.__order = []
        self.__sync = threading.Condition()
        self.__speedup = None
    
    def __add__(self, conf):
        # adding 2 configuration
        # we check if there are parameters in common
        if len(intersect([self.parameters.values(), conf.parameters.values()])) > 0:
            # some parameters are in common, we cannot create the union config
            raise "cannot sum"
        # everything ok, we start copying the parameters
        ret = Configuration()
        # params = set(self.__parameters.values()[:]) | set(conf.parameters.values()[:])
        for k in self.__order + conf.__order:
            p = self.__parameters[k] if k in self.__order else conf.__parameters[k]
            ret += deepcopy(p)
        return ret
    
    def __iadd__(self, param):
        if isinstance(param, Parameter):
            assert param.name not in self.__parameters.keys(), "Parameter {0} already in this configuration".format(param.name)
            self.__parameters[param.name] = deepcopy(param)
            self.__order.append(param.name)
        # add to the dict obj
        self.__dict__[param.name] = self.__parameters[param.name]
        return self
    
    def __isub__(self, param):
        if isinstance(param, Parameter):
            assert param.name in self.__parameters.keys(), "Parameter {0} not in this configuration".format(param.name)
            del self.__parameters[param.name]
            del self.__order[self.__order.index(param.name)]
        # remove from dict obj
        del self.__dict__[param.name]
        return self
    
    def __str__(self):
	if len(self.__parameters) == 0:
		return "";

        keys = self.__order
        max_name_lenght = max( list(map(lambda x: len(x), keys) )) + 1
        func = lambda x : x if x < 80 else 80
        max_val_lenght = func( max( list( map(lambda x: len(str(x[1].currValue())), self.__parameters.items()) )) + 1 )
        ret = '{0:=^{1}}\n'.format('conf.', max_name_lenght + max_val_lenght + 1)
        for key in keys:
            ret += "{0:<{1}}: {2:>{3}}\n".format(key, max_name_lenght, self.__parameters[key], max_val_lenght)
        ret += '{0:-^{1}}'.format('-',max_name_lenght + max_val_lenght + 1)
        return ret
        
    def __len__(self):
        return len(self.__parameters)
    
    def __nonzero__(self):
        for i in self.__constrain:
            if not i.check(self):
                return False
        return True
       
    def parameter_keys(self):
        return self.__order;
    
    @property
    def parameters(self):
        return self.__parameters
    
    def getSpeedup(self):
        self.__sync.acquire()
        if self.__speedup is None:
            self.__sync.wait()
        self.__sync.release()
        return self.__speedup
    
    def setSpeedup(self, val):
        self.__sync.acquire()
        self.__speedup = val
        self.__sync.notify()
        self.__sync.release()
    
    def isEvaluated(self):
        return self.__speedup is not None
    
    def __deepcopy__(self, memo):
        ret = Configuration()
        for p in self.__parameters.values():
            ret += deepcopy(p)
        return ret
        
    def setDefault(self):
        for p in self.__parameters.values():
            p.resetToDefault()

    def check(self, constrain):
        for inv in constrain:
            if not inv.check(self):
                return False
        return True
    
    def WriteBack(self, def_vals, data, final_out_file, elaborate):
              
        if elaborate is None:
            return
        
        self.__sync.acquire()
        data = [x for x in data if x is not None]
        data = [x for x in data if len(x)]
        # we remove the empty elements
        
        file_name = sobstitute( elaborate.out_file_name.currValue(), self )
        in_file_format = elaborate.in_file_format
        
        res = {}
        res['MIN'] = [0] * len(in_file_format)
        res['MAX'] = [0] * len(in_file_format)
        res['AVG'] = [0] * len(in_file_format)
        res['STD'] = [0] * len(in_file_format)
        
        if len(data):
            data_ex = zip(*data);
            for i in range(len(in_file_format)):
                res['AVG'][i] = avg(data_ex[i])
                res['MIN'][i] = min(data_ex[i])
                res['MAX'][i] = max(data_ex[i])
                
            for i in range(len(in_file_format)):
                res['STD'][i] = std(data_ex[i], res['AVG'][i])
            
            # print "MINS: " + str(res['MIN'])
            # print "MAXS: " + str(res['MAX'])
            # print "AVG : " + str(res['AVG'])
            # print "STD : " + str(res['STD'])
        
        vals = []
        for param in elaborate.out_file_format:
            if param in self.__parameters.keys():
                vals.append( toStr(self.__parameters[param].currValue()) )
            elif ( param.startswith('AVG(') or param.startswith('STD(') or 
                   param.startswith('MIN(') or param.startswith('MAX(') ) and param.endswith(')'):
                param_name = param[4:-1]
                assert param_name in in_file_format.values
                vals.append( toStr(res[param[:3]][in_file_format.values.index(param_name)]) )
        
        self.__speedup = -1
        idx = elaborate.speedup_idx.currValue()
        if def_vals:
            if def_vals['AVG'][idx] != 0 and res['AVG'][idx] != 0:
                assert(idx > 0 or idx < 0)
                if idx<0:
                    idx = (-idx)-1
                    self.__speedup = res['AVG'][idx]/def_vals['AVG'][idx]
                else:
                    idx -= 1
                    self.__speedup = def_vals['AVG'][idx]/res['AVG'][idx]
                
            vals.append( toStr(self.__speedup) )
            
        open(file_name,'a').write(",".join( vals ) + "\n")
        
        print "\n{0}".format(80 * "*")
        if res['AVG'][idx] == 0:
            print "* Configuration failed to execute! "
        else:
            print "* Average values: \n*\t%s" %  ", ".join(map(lambda x: "{0:.3f}".format(x), res['AVG']))
            if self.__speedup != -1:
                print "* Speedup: \n*\t{0:.5f}".format(self.__speedup) 
        print "{0}".format(80 * "*")
                
        self.__sync.notify()
        self.__sync.release()
        return res
    
