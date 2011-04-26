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

import optparse, sys, os, re
from parameter import Parameter
from configuration import Constrain
from config_parse import ConfigSection, ConfigFileParser
from iterator import ConfigIterator, CompoundConfigIterator, RandConfigIterator, SingleConfIterator, GeneticSearchIterator
from copy import deepcopy
import runner
from util import *
import random, math, shutil

def main(argv=None):
    parser = optparse.OptionParser()
    parser.add_option("-c", "--cfg", dest="config_file", type="string", 
                      help=("The configuration file which contains"
                      "the details of the benchmark to run"))
    
    parser.add_option("--random", type="int", dest="rand", 
                      help=("Do a random evaluation of the parameters in the 'Optimize'"
                            "section of the configuration file, default: %default"),  
                      default="0")
    
    parser.add_option("--extract", action="store_true", dest="extract", 
                      help=("Only Extract data: %default"),  
                      default="False")
                      
    parser.add_option("--seed", type="int", dest="seed", 
                      help=("Initialize the random number generator: %default"),  
                      default="-1")
    
    parser.add_option("--hill-climbing", action="store_true", dest="hill_climbing",
                      help=("Enable hill-climbing search on the parameters in the 'Optimize'"
                            "section of the configuration file, default= %default"),
                      default="False")
    
    parser.add_option("--genetic", action="store_true", dest="genetic", 
                      help=("Enable genetic search on the parameters on the 'Optimize'"
                            "section of the configuration file, default %default"),
                      default="False")
    
    (options, args) = parser.parse_args()
    
    if not options.config_file:
        parser.error("Error: No configuration input file.")
    
    if not os.path.exists(options.config_file):
        parser.error("Error: Configuration file '{0}' doesn't exist.".format(options.config_file))
    
    config = ConfigFileParser(options.config_file)
    
    main = ConfigSection(config, 'Benchmark')
    initialization = main.parameters['initialize']
    benchmark = main.parameters['benchmark']

    default =  main.parameters['default'] if 'default' in main.parameters.keys() else None
    
    main -= initialization
    main -= benchmark
    
    if 'default' in main.parameters.keys():
        main -= default
    if 'use_sge' not in main.parameters.keys():
	main += Parameter('use_sge', ['False'], 'False')

    print ("Parameters in the main benchmark: ")
    print (main)
    
    optimize = ConfigSection(config, 'Optimize')
    print ("Optimizing parameters:")
    print (optimize)
    
    # reads the invariants
    constrains = []
    if config.sections.has_key('Constrains'):
        constrains = [ Constrain(val) for (key, val) in config.sections['Constrains'] ]
        
    if len(initialization) > 0:
        str = "Initializing the environment"
        print "#{0} {1:^} {0}#".format('~' * int(math.ceil((80 - len(str))/2)-2), str)
        r = runner.LocalRunner(ConfigIterator(main, constrains))
        r.run(initialization, init=True)
        print "@{0}@".format(78 * "-")
    
    extract = ConfigSection(config, 'Extract')
    elaborate = ConfigSection(config, 'Elaborate')
    
    str = "Starting the benchmark"
    print "#{0} {1:^} {0}#".format('~' * int(math.ceil((80 - len(str))/2)-2), str)
    
    for conf in ConfigIterator(main, constrains):
        def_vals = None
        if default:
            print "-> Running  default <-"
            opt_cpy = deepcopy(optimize)
            opt_cpy.setDefault()
            if options.extract == True:
                r = runner.ExtractRunner(SingleConfIterator(conf+opt_cpy), elaborate)
            elif main.use_sge.currValue() == "False" or main.use_sge.currValue() == 0:   
                r = runner.LocalRunner(SingleConfIterator(conf+opt_cpy), extract.experiment_data, elaborate)
            elif main.use_sge.currValue() == "True" or main.use_sge.currValue() == 1:
            	SGE = ConfigSection(config, 'SGE')
            	r = runner.SGERunner(SingleConfIterator(conf+opt_cpy), SGE, False, extract.experiment_data, elaborate)
            def_vals = r.run(default)
     
        opt_param_iter = None
        if options.rand > 0:
            opt_param_iter = RandConfigIterator(optimize, constrains, options.rand, options.seed)
        elif options.genetic is True:
            genetic_conf = ConfigSection(config, 'GeneticSearch')
            opt_param_iter = GeneticSearchIterator(optimize, constrains, 
                sobstitute(genetic_conf.log_file.currValue(), conf), genetic_conf, seed=options.seed)
        else:
            opt_param_iter = ConfigIterator(optimize, constrains)
            
        if options.extract == True:
            r = runner.ExtractRunner(opt_param_iter, elaborate)
        elif main.use_sge.currValue() == "False" or main.use_sge.currValue() == 0:    
            r = runner.LocalRunner(opt_param_iter, extract.experiment_data, elaborate)
        elif main.use_sge.currValue() == "True" or main.use_sge.currValue() == 1:
            SGE = ConfigSection(config, 'SGE')
            r = runner.SGERunner(opt_param_iter, SGE, True, extract.experiment_data, elaborate)
        
        r.run(benchmark, conf, False, def_vals)
    print "@{0}@".format(78 * "-")
    
    #~ print '* Ordering results *'
    #~ for conf in ConfigIterator(main, constrains):
        #~ file_name = sobstitute(elaborate.out_file_name.currValue(), conf)
                
        #~ in_file_name = file_name+'.back'
        #~ shutil.move(file_name, in_file_name)
        
        #~ print ('\t-> Opening file: ' + file_name)
        
        #~ rows = []
        #~ format = elaborate.out_file_format.values
        #~ format.append('speedup')
        #~ # rows.append(format)
        #~ for line in open(in_file_name, 'r'):
            #~ row = []
            #~ for v in line.split(','):
                #~ row.append(convert(v.strip()))
            #~ rows.append(row)
        
        #~ rows.sort()
        #~ rows.insert(0, format)

        #~ # calc the max width for the columns
        #~ col_size = [len(v) for v in format]
        #~ for row in rows:
            #~ for v in range(1,len(row)):
                #~ if len('{0}'.format(row[v])) > col_size[v]:
                    #~ col_size[v] = len('{0}'.format(row[v]))
                    
        #~ # write the values on the file
        #~ of = open(file_name, 'w')
        #~ for row in rows:
            #~ str_row = []
            #~ for v in range(0,len(row)):
                #~ str_row.append('{0:>{1}}'.format(row[v], col_size[v]) )
            #~ of.write(', '.join(str_row) + '\n')
            #~ #writer.write(', '.join(row) + '\n')
        #~ of.close()

    
if __name__ == "__main__":
    sys.exit(main())
