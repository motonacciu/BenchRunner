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

import re
from parameter import Parameter
from configuration import Configuration
from util import convert

DEFAULT = 'DEFAULT'

class ConfigFileParser:
    
    def __init__(self, file_name):
        self.__sections = { DEFAULT:[] }
        curr_section = DEFAULT
        file = open(file_name)
        for line in file:
            if line.strip().startswith('#') or len(line.strip()) == 0:
                # ship comment
                continue
            if line.strip().startswith('['):
                value = line.strip()
                curr_section = value[value.index('[')+1:value.index(']')]
                self.__sections[ curr_section ] = []
                continue
            # we have a name: value tuple
            (name, value) = line[:line.find(':')].strip(), line[line.find(':')+1:].strip()
            if value.endswith('\\'):
                value += '\n'
                # multiline value
                for line in file:
                    if line.startswith('#'):
                        # if there is a comment, remove it
                        continue
                    # line = line[:line.index('#')]
                    value += line.strip()
                    if not line.strip().endswith('\\'):
                        break # this is the last line in the value
                    value += '\n'
                    
            value = value.strip()
            if value.startswith('[') and value.endswith(']'):
                value = value.replace('\\\n','')
                
            self.__sections[curr_section].append( (name, value) )
    
    @property        
    def sections(self):
        return self.__sections
    
class ConfigSection(Configuration):
    
    def __init__(self, config, section):
        Configuration.__init__(self)
        for (name, value) in config.sections[section]:
            # print "reading %s" % name
            (values, default) = parse(value)
            self += Parameter(name, values, default) 

def parse(str):
    ret_values = []
    default = None
    
    step_type = '+'
    step = 1
    
    if str.startswith('['):
        # split the list of values from the default value (if present)
        at_idx = str.find('@')
        (val, def_val) = (str, None) if at_idx == -1 else (str[:at_idx], str[at_idx+1:]) 
        ret_values = [x.strip() for x in val[val.index('[')+1:val.index(']')].split(',')]
        if def_val:
            default = def_val.strip()
    elif str.startswith('('):
        # this is a stride operator
        at_idx = str.find('@')
        (val, def_val) = (str, None) if at_idx == -1 else (str[:at_idx], str[at_idx+1:])
        p = re.compile('\w+')
        v = p.findall(val)
        start = int(v[0])
        end = int(v[1])
        if(len(v) == 3):
            p = re.compile('\*\w+')
            if p.findall(val):
                step_type = '*'
            step = int(v[2])
        
        # Create values
        curr = start
        while curr <= end:
            ret_values.append(curr)
            curr = eval( 'curr {0} {1}'.format(step_type, step))
        if def_val:
            default = def_val.strip()
    else:
        # this is a single value variable
        if str.startswith("s\""):
            str = str.replace('\\\n','')[2:-1] # remove initial 's"' and final '"'
        ret_values.append(str)
            
    # try to convert the values into float/int
    return ( list(map(lambda x: convert(x), ret_values)), convert(default) )
