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
from configuration import Configuration, Constrain
from util import toStr
import math

class ConfigIterator:
    
    def __init__(self, config, invariants):
        self.__config = config
        self.__invariants = invariants
    
    @property
    def configuration(self):
        return self.__config
      
    def __iter__(self):
        return self.next() 
    
    def discardLastConf(self):
        pass
        
    def reset(self):
        pass
        
    def next(self):
        if self.__config.check(self.__invariants):
            yield self.__config
        keys = [k for k in self.__config.parameters.keys()]
        while True:
            k = 0
            overflow = True
            while k < len(keys) and overflow:
                try:
                    self.__config.parameters[keys[k]].next()
                    overflow = False
                except OutOfBoundsExcection:
                    self.__config.parameters[keys[k]].reset()
                    k += 1
            if k == len(keys):
                raise StopIteration
            if self.__config.check(self.__invariants):
                yield self.__config

class SingleConfIterator:
    def __init__(self, config):
        self.__config = config
    
    @property
    def configuration(self):
        return self.__config
      
    def __iter__(self):
        return self.next() 
    
    def discardLastConf(self):
        pass
        
    def reset(self):
        pass
        
    def next(self):
        yield self.__config

import random

class RandConfigIterator:
    
    def __init__(self, config, constraints, iterations=100, seed=-1):
        self.__config = config
        self.__constraints = constraints
        self.__iterations = iterations
        self.__seed = seed
        if self.__seed == -1:
            random.seed(None)
        self.__currIt = 0
    
    @property
    def configuration(self):
        return self.__config
        
    def __iter__(self):
        return self.next() 
    
    def discardLastConf(self):
        self.__currIt -= 1
        
    def reset(self):
        self.__currIt = 0
        if self.__seed != -1:
            random.seed(self.__seed)
    
    def next(self):
        self.reset()
        while self.__currIt  < self.__iterations:
            for param in self.__config.parameters.values():
                param.rand()
            # check configuration
            if self.__config.check(self.__constraints):
                print  '#{0}#'.format('-' * 78)
                print ("#    RandConfigIterator: configuration number {0:^10}".format(self.__currIt+1))
                print  '#{0}#'.format('-' * 78)
                
                yield self.__config
                self.__currIt += 1
        raise StopIteration
       
def iterate(iter, constrains):
    # if we get a list with a single element, unpack it
    if isinstance(iter, list) and len(iter) == 1:
        yield iterate(iter[0])

    # if the element is not a list, we just go through
    # its elements
    if not isinstance(iter, list):
        for it in iter[0]:
            yield it
        raise StopIteration
    # we have a list of iterators!
    # we start chaining the first one
    for it1 in iter[0]:
        # if there are only 2 elements on the list of iters
        # just go through the second iterator and return
        # the combined value
        if len(iter[1:]) == 1:
            for it2 in iter[1]:
                c = it1 + it2
                if c.check(constrains):
                    yield c
                else:
                    for i in iter[1:]:
                        i.discardLastConf()
        else:
            # else, recursively call the function
            for it2 in iterate( iter[1:] ):
                c = it1 + it2
                if c.check(constrains):
                    yield c
                else:
                    for i in iter[1:]:
                        i.discardLastConf()
        for i in iter[1:]:
            i.reset()

    raise StopIteration

class CompoundConfigIterator:

    def __init__(self, iterators, constrains):
        iters = list(iterators)
        diff = set(iters[0].configuration.parameters.keys())
        for it in iters[1:]:
            diff &= set(it.configuration.parameters.keys())
            
        assert len(diff) == 0, \
            ("Cannot create CompoundConfigIterator because the input iterators"
            "have the parameters {0} in common").format(diff)
        self.__iterators = iters
        self.__constrains = constrains
    
    def discardLastConf(self):
        map(lambda x: x.discardLastConf(), self.__iterators)
    
    def reset(self):
        map(lambda x: x.reset(), self.__iterators)
    
    def __iter__(self):
        return iterate(self.__iterators,self.__constrains)

# Genetic Search Algorithm
class GeneticSearchIterator:
    
    def __init__(self, config, constraints, log_file, genetic_conf, seed=-1):
        self.__config = config
        self.__constraints = constraints
        self.__log_file = log_file
        # erase precendent file
        open(log_file, 'w').close()
        
        self.__log_file_format = genetic_conf.log_file_format
        self.__pop_size = genetic_conf.pop_size.currValue()
        self.__tournament_size = genetic_conf.tournament_size.currValue()
        self.__iterations = genetic_conf.iterations.currValue()
        self.__repeatitions = genetic_conf.repeatitions.currValue()
        self.__seed = seed
        if self.__seed == -1:
            random.seed(None)
    
    @property
    def configuration(self):
        return self.__config
        
    def __iter__(self):
        return self.next() 
    
    def discardLastConf(self):
        self.__currIt -= 1
        
    def reset(self):
        print "[Genetic Search]\n-> Initializing population of size: %s" % self.__pop_size 
        self.__pop = []
        # vector of still unused parameters
        # this is done to avoid to have some of the parameters out of the first population
        unused_params = [param for param in self.__config.parameters.values()]
        ratio = int( math.ceil(float(len(self.__config)) / float(self.__pop_size)) )
    
        while len(self.__pop) < self.__pop_size:
            # the gene length for this individual will be chosen randomly between 2 and n
            length = random.randint(1, len(self.__config))
            element = Configuration()
            
            for gene in range(length):
                if gene < ratio and len(unused_params) != 0:
                    idx = random.randint(0, len(unused_params)-1)
                    param = unused_params[idx]
                    param.rand()
                    element += param
                    del unused_params[idx]
                    continue
                # we choose each gene randomly
                param = None
                while param is None:
                    idx = random.randint(0, len(self.__config)-1)
                    param = self.__config.parameters.values()[idx]
                    if not param in element.parameters.values():
                        param.rand()
                        element += param
                    else:
                        param = None
                        
                # remove from the list of mandatory params
                if param in unused_params:
                    unused_params.remove(param)
            
            added_params = []
            for param in self.__config.parameters.values():
                if param.name not in element.parameter_keys():
                    element += param
                    added_params.append(param)
                        
            if element.check(self.__constraints):
                self.__pop.append(element)
            
            for param in added_params:
                element -= param
            
        # print 'Completed population initialization:\n'
        # for p in self.__pop:
        #     print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
        #     print '{0}'.format(p)
    
    def crossover(self, p1, p2): 
        offsprings = [ ]
        # Crossover
        for offspring_idx in range(2):
            # decide the size of the offspring
            offspring = Configuration()
            
            lb = min(len(p1), len(p2))
            ub = max(len(p1), len(p2))
            
            # we choose the size randomly between the 2 parents' size
            size = random.randint(lb,ub)
            
            common = set()
            for p1_gene in p1.parameters.values():
                if p1_gene in p2.parameters.values():
                    # two parents have the same gene
                    if random.randint(0,1):
                        offspring += p1_gene
                    else:
                        offspring += p2.parameters[p1_gene.name]
                    common.add(p1_gene)
            
            # print ','.join(map(lambda x: x.name, common))
            remaining = list((set(p1.parameters.values()) - common) | (set(p2.parameters.values()) - common))
            # print ','.join(map(lambda x: x.name, remaining))
            
            while len(offspring) < size:
                # select from the remaining genes 
                idx = random.randint(0, len(remaining)-1)
                if remaining[idx].name not in offspring.parameter_keys():
                    offspring += remaining[idx]
                    del remaining[idx]
            
            offsprings.append(offspring)
            
        return tuple(offsprings)
    
    def next(self):
        repeatitions = 1;
        while( repeatitions < self.__repeatitions):
            self.reset()
            generation_number = 1
            max_fitness = None
            max_generation = 0
            open(self.__log_file, 'a').write('@ Genetich search start: {0}\n'.format(repeatitions))
            while generation_number < self.__iterations or (generation_number - max_generation) < 10:
                # generate a tournament
                
                toEvaluate = [ self.__pop.index(x) for x in self.__pop if not x.isEvaluated() ]
                # collect configurations which have not been evaluated yet
                print '#{0}#'.format('*' * 78) 
                print "#    Starting new tournament"
                print '#       # of configurations not yet evaluated: %s' % len(toEvaluate)
                    
                tournament = set()
                while len(tournament) < self.__tournament_size:
                    if len(toEvaluate) > 0:
                        n = random.randint(0,len(toEvaluate)-1)
                        tournament.add( self.__pop[toEvaluate[n]] )
                        del toEvaluate[n]
                    else:
                        tournament.add( self.__pop[random.randint(0,self.__pop_size-1)] )
                # we created a tournament, now we evaluate the elements in the tournament
                # print 'Population: [ {0} ]'.format( ', '.join( map(lambda x: '{0}'.format(x.isEvaluated()), self.__pop) ) )
                count = 1
                
                for element in tournament:
                    print  '#{0}#'.format('-' * 78)
                    print ("#    GeneticSearch: evaluating generation {0} (element {1}/{2})".\
                            format(generation_number, count, self.__tournament_size))
                    print  '#{0}#'.format('-' * 78)
                    
                    print "{0}".format(element)
                    
                    count += 1
                    
                    if element.isEvaluated():
                        print "\t* Configuration already evaluated *"
                        continue
                        
                    # set other parameters to default otherwise the runner is not able to run the configuration
                    added_params = []
                    for param in self.__config.parameters.values():
                        if param.name not in element.parameter_keys():
                            element += param
                            added_params.append(param)
                    
                    if element.check(self.__constraints):
                        yield element
                    else:
                        # element failed
                        element.setSpeedup(-1)
                        
                    for param in added_params:
                        element -= param
                
                # evaluation of tournament completed, printing fitness values
                tournament = sorted(tournament, key=lambda element: element.getSpeedup(), reverse=True)
                print  '#{0}#'.format('~' * 78)
                print '#    Fitness values for the tournament:\n#\t[ {0} ]'.\
                    format( ', '.join(map(lambda element: '{0:.5f}'.format(element.getSpeedup()),tournament)) )
                print '#'
                tournament_max = tournament[0].getSpeedup()
                if max_fitness is None or max_fitness < tournament_max:
                    max_fitness = tournament_max
                    max_generation = generation_number
                    
                # Log the outcome of this tournament
                vals = []
                for param in self.__log_file_format:
                    if param in element.parameter_keys():
                        vals.append( toStr(element.parameters[param].currValue()) )
                    else:
                        vals.append( '-' )
                # adding the value of the maximum fitness for this generation
                vals.append( '{0:.5f}'.format(tournament_max) )
                open(self.__log_file,'a').write(",".join( vals ) + "\n")
                    
                # print "##### PARENTS #####"
                # print '{0}'.format(tournament[0])
                # print '{0}'.format(tournament[1])
                (offspring1, offspring2) = self.crossover(tournament[0], tournament[1])
                # print '{0}'.format(offspring1)
                # print '{0}'.format(offspring2)
                if random.random() <= 0.2 or tournament[0] == tournament[1]:
                    # Mutation:
                    # in order to avoid to get stuck in a local maximal, we apply mutation
                    print '#    Applying mutation on newly created offsprings'
                    for offspring in (offspring1, offspring2):
                        for param in offspring.parameters.values():
                            if random.randint(0, 1):
                                param.rand()
                                
                        if random.randint(0, 1) and len(offspring) < len(self.__config):
                            print "#\t-> Adding paraleter to configuration"
                            # we add a new parameter to this configuration
                            found = False
                            while not found:
                                idx = random.randint(0,len(self.__config)-1)
                                param = self.__config.parameters[self.__config.parameter_keys()[idx]]
                                if param.name not in offspring.parameter_keys():
                                    offspring += param
                                    found = True
                        elif len(offspring) > 1:
                            print "#\t-> Removing parameter to configuration"
                            #remove 1 parameter
                            idx = random.randint(0,len(offspring)-1)
                            offspring -= offspring.parameters[offspring.parameter_keys()[idx]]
                
                # Kicking out the elements with the lowest fitness from the population
                # by replacing with the new offspings
                self.__pop[self.__pop.index(tournament[-1])] = offspring1
                self.__pop[self.__pop.index(tournament[-2])] = offspring2
                
                print "#    End tournament:\n#\tLocal maximal fitness = {0:.4f}, Global maximal = {1:.4f}".\
                    format(tournament_max, max_fitness)
                generation_number += 1
                
                print  '#{0}#'.format('~' * 78)
            
            repeatitions+=1
            
        raise StopIteration
