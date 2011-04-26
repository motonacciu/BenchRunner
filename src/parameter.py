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

class OutOfBoundsExcection(Exception): 
    def __init__(self,msg):
        Exception.__init__(self,msg)
        
class NoDefaultValueException(Exception): 
    def __init__(self,msg):
        Exception.__init__(self,msg)

class Parameter:
    def __init__(self, name, values, default):
        assert isinstance(values, list), "The list of values must be a list."
        self.__name = name
        if values is None:
            self.__values = []
        else:
            self.__values = values
        self.__default = default
        self.__observers = set()
        self.reset()
        
    @property
    def name(self):
        """ Property which returns the name of the parameter.
        
        >>> p = Parameter('param_name', range(1,5), 0)
        >>> p.name
        'param_name'
        """
        return self.__name
    
    def __len__(self):
        """ Returns the number of possible values for this parameter.
        
        >>> p = Parameter('param_name', range(1,5), 0)
        >>> len(p)
        4
        """
        return len(self.__values)
    
    def __iter__(self):
        for val in self.__values:
            yield val
    
    def __getitem__(self, idx):
        """ Returns the value with index 'idx' of this parameter.
        
        >>> p = Parameter('param_name', range(1,5), 0)
        >>> p[2]
        3
        """
        assert idx < len(self), \
            "In parameter '{0}', index {1} is out of bounds (size = {2})"\
            .format(self.__name, idx, len(self)) 
        return self.__values[idx]
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __str__(self):
        return "{0} - VALUES:{2} - DEFAULT: {3} --> {1}"\
            .format(self.name, self.currValue(), self.__values, self.__default)
    
    def __hash__(self):
        return hash(self.__name)
    
    def __format__(self, format_spec):
        return str(self.currValue())
    
    def __deepcopy__(self, memo):
        ret = Parameter(self.__name, self.__values[:], self.__default)
        ret.__curr_value_idx = self.__curr_value_idx
        return ret
        
    def __skip(self, n):
        """ Set the previous value in list
        
        >>> p = Parameter('param_name', range(1,5), 2)
        >>> p.next()
        2
        >>> p.next(2)
        4
        >>> p.resetToDefault()
        2
        >>> p.next()
        3
        >>> p.setValueIdx(3)
        4
        >>> p.prev()
        3
        >>> p.prev(2)
        1
        >>> p = Parameter('param_name', range(1,6,2), 2)
        >>> p.next(2)
        5
        """
        index = self.__curr_value_idx
        if index is None:
            # the parameter is currently assuming the default value
            # we have to increase to the next closest value in the 
            # list of values
            ret = list(map(lambda x: 0 if x<self.__default else 1, self.__values))
            # the first item in the list with value 1 is first item greater than the default
            index = ret.index(1) if n>0 else ret.index(1) - 1
            if self[index] == self.__default:
                index = index + 1 if n>0 else index - 1
            n = n-1 if n>0 else n+1
            
        if index + n > len(self)-1 or index + n < 0:
            raise OutOfBoundsExcection( \
                ("Parameter '{0}', trying to increment current value "
                "index = {1} with step {2}, where length is {3}")
                .format(self.name, index, n, len(self)))
        self.__curr_value_idx = index + n
        self.__update()
        return self.currValue()
        
    def next(self, n = 1):
        return self.__skip(n)
        
    def prev(self, n = 1):
        return self.__skip(-n)
        
    def rand(self):
        if self.__values is []:
            return self.__default
        import random
        self.__curr_value_idx = random.randint(0,len(self)-1)
        self.__update()
        return self.currValue()
    
    def setValueIdx(self, idx):
        assert idx < len(self), \
            "In parameter '{0}', index {1} is out of bounds (size = {2})"\
            .format(self.__name, idx, len(self)) 
        if idx != self.__curr_value_idx:
            self.__curr_value_idx = idx
            self.__update() # notify the observers for internal value change
        return self.currValue()
    
    def setValue(self, val):
        if val not in self.__values and val != self.__default:
            raise "Value is not in the list"
        if self.currValue() != val:
            if val in self.__values:
                self.__curr_value_idx = self.__values.index(val)
                self.__update()
            else:
                self.resetToDefault()
        return self.currValue()
    
    def resetToDefault(self):
        self.__curr_value_idx = None
        self.__update()
        return self.currValue()
        
    def reset(self):
        self.__curr_value_idx = 0
        if (self.__values is None) or (self.__values == []):
            self.__curr_value_idx = None
        self.__update()
    
    def currValue(self):
        """ Returns the current value for this parameter.
        
        >>> p = Parameter('param_name', range(1,5), 0)
        >>> p.currValue()
        1
        """
        if self.__curr_value_idx is not None:
            return self.__values[self.__curr_value_idx]
        if self.__default is None:
            raise NoDefaultValueException("No default object set for parameter {0}"\
                                          .format(self.__name))
        return self.__default
    
    def addObserver(self, obs):
        self.__observers.add(obs)
        
    def __update(self):
        for obs in self.__observers:
            obs.notify(self)

    @property
    def values(self):
        return self.__values
    
import doctest
doctest.testmod()
