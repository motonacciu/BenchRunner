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

from configuration import Configuration
from parameter import Parameter
from iterator import CompoundConfigIterator, ConfigIterator, RandConfigIterator
import config_parse, math
import subprocess, time, shlex, re, sys, os
from util import *
from copy import deepcopy

def write(file, msg):
    if file:
        of = open(file, 'a')
        of.write(msg)
        of.close()
    else:
        print (msg)

def extract(output, extracted_params):
    rows = [ 0 ] * len(extracted_params)
    for i in range(len(extracted_params)):
        p = re.compile(extracted_params[i] + '\d+(\.\d+)?')
        rows[i] = []
        for it in p.finditer(output):
            substring = it.group()
            # print substring
            p = re.compile('\d+(\.\d+)?')
            rows[i].append( config_parse.convert(p.search(substring).group()) )
    # return non empty rows
    return zip(*rows)

# Interface for Runners. 
class Runner:
    def __init__(self, iter):
        self.iter = iter
        
    def run(self):
        pass

class DummyRunner(Runner):
    
    def __init__(self, iter):
        Runner.__init__(self, iter)

    def run(self, cmd_list):
        for conf in self.iter:
            for cmd in cmd_list:
                print (sobstitute(cmd, conf))

def run_local(cmd, kill_after=None):
    pid = subprocess.Popen( shlex.split(cmd), stdout=subprocess.PIPE )
    if kill_after is None:
        pid.wait()
    else:
        remaining = kill_after
        while remaining > 0 and pid.poll() is None:
            time.sleep(1)
            remaining -= 1
    if pid.poll() is None:
        print ("* Killing process {0}".format(pid.pid))
        pid.kill()
    return pid.communicate()

class LocalRunner(Runner):
    def __init__(self, iter, extracted_params=None, elaborate=None):
        Runner.__init__(self, iter)
        self.__extract = extracted_params
        self.__elaborate = elaborate
        
    def run(self, cmd_list, paren_conf=None, init=False, def_vals=None):
        ret = None
        for conf in self.iter:
        #    for conf in confs:
            # print conf
            if not init: 
                print "----> new configuration <----"
            
            final_out_file = None
            ret = None
            
            cconf = conf
            if paren_conf is not None:
                cconf = paren_conf + conf
                
            data = []
            kill_after = None
            if 'kill_after' in cconf.parameters.keys():
                kill_after = cconf.kill_after.currValue() if not init else None
            
            for n in range(cconf.num_of_runs.currValue()):
                if not init:
                    print "~~ RUN #{0} ~~".format(n+1)
                for cmd in cmd_list:
                    out_file = None
                    curr_cmd = sobstitute(cmd, cconf)
                    
                    curr_cmd = curr_cmd.replace('\\\n','')
                    if curr_cmd.find('>>') != -1:
                        out_file = curr_cmd[curr_cmd.rfind('>>')+2:].strip()
                        curr_cmd = curr_cmd[:curr_cmd.rfind('>>')].strip()
                        final_out_file = out_file
                    
                    curr_data = self.__run_local( curr_cmd, out_file, kill_after)
                    if(curr_data and len(curr_data) > 0):
                        data.append( curr_data )
                    
                if init:
                    break
                
                if len(data) == 0:
                    # it means the first run failed, so it means this configuration is not working
                    break
                    
            if not init:
                ret = cconf.WriteBack(def_vals, data, final_out_file, self.__elaborate)
                conf.setSpeedup( cconf.getSpeedup() )
                
        return ret
    
    def __run_local(self, cmd, out_file=None, kill_after=None):
        data = run_local(cmd, kill_after)[0] 
        
        if self.__extract and out_file:
            ext_data = extract( data, self.__extract )
            if len(ext_data) > 0:
                ext_data = ext_data[0]
                sys.stdout.write("Extracting data... ")
                print ", ".join(  map(lambda x: "{0:.3f}".format(x), ext_data) )
                print "Writing results onto file: {0}".format(out_file)
                write( out_file, data )
                write( gen_file_name(out_file) , 
                       ",".join( map(lambda x: "{0}".format(x), ext_data)) + '\n' )
            else:
                write( out_file, data )
            return ext_data
        if out_file is None:
            print data

class ExtractRunner(Runner):
    
    def __init__(self, iter, elaborate=None):
        Runner.__init__(self, iter)
        self.__elaborate = elaborate
        
    def run(self, cmd_list, paren_conf=None, init=False, def_vals=None):
        ret = None
        for conf in self.iter:
            # print conf
            
            cconf = conf
            if paren_conf is not None:
                cconf = paren_conf + conf
                
            for cmd in cmd_list:
                out_file = None
                curr_cmd = sobstitute(cmd, cconf)
                
                curr_cmd = curr_cmd.replace('\\\n','')
                if curr_cmd.find('>>') != -1:
                    out_file = curr_cmd[curr_cmd.rfind('>>')+2:].strip()
                    curr_cmd = curr_cmd[:curr_cmd.rfind('>>')].strip()
                    final_out_file = out_file
                    
                if out_file:
                    data = []
                    if os.path.exists(gen_file_name(out_file)):
                        for line in open(gen_file_name(out_file)):
                            data.append([convert(x.strip()) for x in line.split(',')])

                    ret = cconf.WriteBack(def_vals, data, out_file, self.__elaborate)
                
        return ret

class SGERunner(Runner):
    
    def __init__(self, iter, sge, use_thread_pool=True, extracted_params=None, elaborate=None):
        Runner.__init__(self, iter)  
        self.__extract = extracted_params
        self.__use_thread_pool = use_thread_pool
        self.__elaborate = elaborate
        self.__sge = sge
    
    def run(self, cmd_list, paren_conf=None, init=False, def_vals=None):
        
        import threadpool
        
        ret = None
                
        # Create a pool with three worker threads
        i = 0
        pool = threadpool.ThreadPool( self.__sge.pool_size.currValue() )
        for conf in self.iter:
            # print conf
            
            cconf = conf
            if paren_conf is not None:
                cconf = paren_conf + conf
            
            pack = ""
            out_file = None
            for _ in range(cconf.num_of_runs.currValue()):
                for cmd in cmd_list:
                    curr_cmd = sobstitute(cmd, cconf)
                    
                    curr_cmd = curr_cmd.replace('\\\n','')
                    if curr_cmd.find('>>') != -1:
                        out_file = curr_cmd[curr_cmd.rfind('>>')+2:].strip()
                    pack += curr_cmd + "\n"
            
            sge_skel = self.__sge.skel_script.currValue().replace('\\\n','\n')

            if self.__use_thread_pool:
                # Insert tasks into the queue and let them run
                pool.queueTask(self.__run_sge, 
                        (conf, deepcopy(cconf), sobstitute(sge_skel, cconf + self.__sge) + "\n\n" + pack, i, out_file, def_vals), None)
                i += 1
            else:
                ret = self.__run_sge(conf, cconf, sobstitute(sge_skel, cconf + self.__sge) + "\n\n" + pack, i, out_file, def_vals)
        # When all tasks are finished, allow the threads to terminate
        pool.joinAll()
        return ret
                
    def __monitor(self, jobid):
        print '--> Monitoring execution of job %s' % jobid
        time.sleep(self.__sge.timeout.currValue())
        found = 0
        while 1:
            lines = os.popen('qstat -u {0}'.format(self.__sge.user_name.currValue())).readlines()[2:]
            for l in lines:
                if len(l) == 0:
                    continue
                values = [v for v in l.strip().split(' ') if len(v) > 0]
                if values[0] != jobid:
                    continue
                
                found = 1
                curr = time.strftime("%d|%b|%Y@%H:%M:%S", time.gmtime())
                start_time = time.strptime(curr.split('@')[0]+'@'+values[6] , "%d|%b|%Y@%H:%M:%S")
                stop_time =  time.localtime(time.mktime(start_time) + 
                            self.__sge.sqe_kill_after.currValue())
                curr_time = time.localtime()
                if values[4] == 'r' and curr_time > stop_time:
                   print '\t[monitor()]: Job {0} stuck -> KILLED'.format(jobid)
                   os.system( 'qdel {0} &'.format(jobid) )
                   return
                break
                    
            if not found:
                return
            
            found=0
            time.sleep(self.__sge.timeout.currValue())
        
    def __run_sge(self, conf, cconf, cmd, id, out_file=None, def_vals=None):
        # print conf
        file_name = '~script.sh.' + str(id)
        open(file_name, 'w').write(cmd)
        time.sleep(1)
        pid = subprocess.Popen( ['qsub', file_name], stdout=subprocess.PIPE )
        pid.wait()
        data = pid.communicate()[0]
        if os.path.exists(file_name):
            os.remove(file_name)           
        if data.strip().startswith("Your job") and data.strip().find("has been submitted") != -1:
            p = re.compile('\d+')
            jobid = p.finditer(data).next().group()
            # wait for the job to finish
            self.__monitor(jobid)
            if self.__extract and out_file:
                ext_data = []
                if os.path.exists(out_file):
                    ext_data = extract( open(out_file).read(), self.__extract )
                    
                # print ext_data
                    
                sys.stdout.write("Extracting data... ")
                for i in range(len(ext_data)):
                    print ", ".join(  map(lambda x: "{0:.3f}".format(x), ext_data[i]) )
                    
                print "Writing results onto file: {0}".format(out_file)
                for i in range(len(ext_data)):
                    write( os.path.dirname(out_file) + "/~" + os.path.basename(out_file), 
                            ",".join( map(lambda x: "{0}".format(x), ext_data[i])) + "\n" )
                            
                ret = cconf.WriteBack(def_vals, ext_data, out_file, self.__elaborate)
                conf.setSpeedup( cconf.getSpeedup() )
                return ret
                
            if out_file is None:
                print data
            
        else:
            print "ERROR submitting job to SGE: %s" % data 
        
        
        
