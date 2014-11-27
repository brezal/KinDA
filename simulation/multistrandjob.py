from imports import multistrandhome, dnaobjectshome

import math

# Import Multistrand
import multistrand.objects as MSObjects
from multistrand.options import Options as MSOptions
from multistrand.system import SimSystem as MSSimSystem

from dnaobjects import utils, io_Multistrand, Macrostate, RestingSet, Complex

import options
from datablock import Datablock

# GLOBALS
TRAJECTORY_MODE = 128
TRANSITION_MODE = 256
FIRST_PASSAGE_MODE = 16
FIRST_STEP_MODE = 48

EXACT_MACROSTATE = 0
BOUND_MACROSTATE = 1
DISASSOC_MACROSTATE = 2
LOOSE_MACROSTATE = 3
COUNT_MACROSTATE = 4

# Custom statistical functions:
def rate_mean_func(datablock):
  """Computes the expected rate given that the sampled reaction times
  follow an exponential distribution with a mean of 1/r. In this case,
  the correct estimate for the rate is the harmonic mean of the r's.
  If no data has been collected, returns NaN."""
  data = datablock.get_data()
  if len(data) > 0:
    times = [1.0 / r for r in data if r != 0]
    return len(times) / sum(times)
  else:
    return float('nan')
def rate_error_func(datablock):
  """Estimates the standard error for the rate estimate from the
  standard error for the measured reaction times. Based on local linearity
  of r=1/t, the error in the rates has the same proportion of the estimated
  rate as the error in the times.
  If 1 or fewer data points are collected, returns float('inf')."""
  data = datablock.get_data()
  n = len(data)
  if n > 1:
    times = [1.0 / r for r in data if r != 0]
    time_mean = sum(times) / n
    time_std = math.sqrt(sum([(t - time_mean)**2 for t in times]) / (n - 1))
    time_error = time_std / math.sqrt(n)
    # Based on estimated local linearity of relationship between t and r=1/t
    return time_error / time_mean**2
  else:
    return float('inf')
def bernoulli_std_func(datablock):
  return math.sqrt(datablock.get_mean() * (1 - datablock.get_mean()))
def bernoulli_error_func(datablock):
  data = datablock.get_data()
  n = len(data)
  if n > 0:
    return datablock.get_std() / math.sqrt(n)
  else:
    return float('inf')
    
# MultistrandJob class definition
class MultistrandJob(object):
  """Represents a simulation job to be sent to Multistrand. Allows the
  calculation of reaction rates/times and error bars on calculated data.
  Depending on the output mode, different statistics are calculated on
  the trajectory results.
  This is the parent class to the more useful job classes that compile
  specific information for each job mode type."""
  datablocks = {}
  
  ms_options = None
  
  def __init__(self, start_state, stop_states, stop_tags, sim_mode):
    self.ms_options = self.setup_options(start_state = start_state,
                                         stop_states = stop_states,
                                         stop_tags = stop_tags,
                                         mode = sim_mode)
    
    self.datablocks["overall_time"] = Datablock()
    self.datablocks["overall_rate"] = Datablock(mean_func = rate_mean_func,
                                                error_func = rate_error_func)
                                                
  def setup_options(self, *args, **kargs):
    """ Inelegant. Consider revising. """
    def make_stop_macrostates(stop_states, stop_tags):
      """stop_complexes is a list of lists of Complexes or RestingSets
      that define the stop conditions for this job. We convert each list of
      complexes to a macrostate conjunction of loose or exact macrostates
      corresponding to each complex in the list."""
      loose_complexes = options.flags['loose_complexes']
      loose_cutoff = options.general_params['loose_complex_similarity']
      
      obj_to_mstate = {}
      for obj in set(sum(stop_states, [])):
        if obj._object_type == 'resting-set':
          obj_to_mstate[obj] = Macrostate(type = 'disassoc', complex = next(iter(obj.complexes)))
        elif loose_complexes:
          obj_to_mstate[obj] = utils.similar_complex_macrostate(obj, loose_cutoff)
        else:
          obj_to_mstate[obj] = utils.exact_complex_macrostate(obj)
          
      macrostates = [
        Macrostate(name = tag, type = 'conjunction', macrostates = [
          obj_to_mstate[o]
            for o
            in objs
        ])
          for objs, tag
          in zip(stop_states, stop_tags)
      ]
      return macrostates
      
    ## Create state_state with Multistrand Complexes
    if all(map(lambda x: isinstance(x, RestingSet), kargs['start_state'])):
      resting_sets = kargs['start_state']
      start_complexes = []
      boltzmann = True
    elif all(map(lambda x: isinstance(x, Complex), kargs['start_state'])):
      resting_sets = []
      start_complexes = kargs['start_state']
      boltzmann = False
    else:
      assert False, "Starting state must be all complexes or all resting sets"
      
    stop_conditions = make_stop_macrostates(kargs['stop_states'], kargs['stop_tags'])
    complexes = start_complexes
    #print [c.strands for c in complexes]
    #print strands
    #print domains
    
    ms_data = io_Multistrand.to_Multistrand(
        complexes = complexes,
        resting_sets = resting_sets,
        macrostates = stop_conditions
    )
    domains_dict = dict(ms_data['domains'])
    strands_dict = dict(ms_data['strands'])
    complexes_dict = dict(ms_data['complexes'])
    resting_sets_dict = dict(ms_data['restingstates'])
    macrostates_dict = dict(ms_data['macrostates'])
    
    ## Create Options object using options.multistrand_params
    if boltzmann:
      start_state = [resting_sets_dict[rs] for rs in resting_sets]
    else:
      start_state = [complexes_dict[c] for c in start_complexes]
    o = MSOptions(start_state = start_state,
                  dangles = options.multistrand_params['dangles'],
                  simulation_time = options.multistrand_params['sim_time'],
                  parameter_type = options.multistrand_params['param_type'],
                  substrate_type = options.multistrand_params['substrate_type'],
                  rate_method = options.multistrand_params['rate_method'])
    o.simulation_mode = kargs['mode']
    o.temperature = options.multistrand_params['temp']
    o.boltzmann_sample = boltzmann
#    o.output_interval = options.multistrand_params['output_interval']
    o.stop_conditions = [macrostates_dict[m] for m in stop_conditions]
    
    return o
    
  def get_statistic(self, reaction, stat = 'rate'):
    return self.datablocks[reaction + "_" + stat].get_mean()
  def get_statistic_error(self, reaction, stat = 'rate'):
    return self.datablocks[reaction + "_" + stat].get_error()
  
  def run_simulations(self, num_sims):
    self.ms_options.num_simulations = num_sims
    print "Running %d simulations..." % num_sims
    MSSimSystem(self.ms_options).start()
    print "Processing %d simulations..." % num_sims
    results = self.ms_options.interface.results
    self.process_results()
    
  def process_results(self):
    results = self.ms_options.interface.results
    times = [r.time for r in results]
    rates = [1.0/t for t in times if t != 0]
    
    self.datablocks["overall_time"].add_data(times)
    self.datablocks["overall_rate"].add_data(rates)
    
    del self.ms_options.interface.results[:]
      
  
  def reduce_error_to(self, rel_goal, abs_goal = 0.0, reaction = 'overall', stat = 'rate'):
    """Runs simulations to reduce the error to either rel_goal*mean or abs_goal."""
    tag = reaction + "_" + stat
    block = self.datablocks[tag]
    
    error = block.get_error()
    goal = max(abs_goal, rel_goal * block.get_mean())  
    while not error <= goal:
      # Estimate additional trials based on inverse square root relationship
      # between error and number of trials
      if error == float('inf'):
        num_trials = 5
      else:
        reduction = error / goal
        num_trials = int(block.get_num_points() * (reduction**2 - 1) + 1)
        num_trials = min(num_trials, 50)
        
      self.run_simulations(num_trials)
      error = block.get_error()
      goal = max(abs_goal, rel_goal * block.get_mean())
    
    

class FirstPassageTimeModeJob(MultistrandJob):
  
  datablocks = {}
  tags = None
  
  ms_options = None
  
  def __init__(self, start_complexes, stop_conditions):
      
    super(FirstPassageTimeModeJob, self).__init__(start_complexes,
                                                  stop_conditions,
                                                  FIRST_PASSAGE_MODE)
      
    self.tags = [sc.tag for sc in self.ms_options.stop_conditions]
    for sc in self.ms_options.stop_conditions:
      self.datablocks[sc.tag + "_time"] = Datablock()
      self.datablocks[sc.tag + "_rate"] = Datablock(mean_func = rate_mean_func,
                                                    error_func = rate_error_func)
  
  def process_results(self):
    results = self.ms_options.interface.results
    
    times = [r.time for r in results]
    rates = [1.0/t for t in times if t != 0]
    self.datablocks["overall_time"].add_data(times)
    self.datablocks["overall_rate"].add_data(rates)
    
    for tag in self.tags:
      relevant_sims = filter(lambda x: x.tag == tag, results)
      times = [r.time for r in relevant_sims]
      rates = [1.0 / t for t in times if t != 0]
      self.datablocks[tag + "_time"].add_data(times)
      self.datablocks[tag + "_rate"].add_data(rates)
      
    del self.ms_options.interface.results[:]
      
      
class TransitionModeJob(MultistrandJob):
  
  datablocks = {}
  states = None
  
  ms_options = None
  
  def __init__(self, start_complexes, macrostates, stop_states):
    stop_conditions = macrostates[:]
    
    # This actually modifies the stop macrostates in place, so this could be bad
    for sc in stop_states:
      sc.name = "stop:" + sc.name
      stop_conditions.append(sc)
      
    super(TransitionModeJob, self).__init__(start_complex, stop_conditions, TRANSITION_MODE)
      
    self.states = [sc.tag for sc in self.ms_options.stop_conditions]
  
  def get_statistic(self, start_states, end_states, stat = 'rate'):
    tag = self.get_tag(start_states, end_states)
    return self.datablocks[tag + "_" + stat].get_mean()
  def get_statistic_error(self, start_states, end_states, stat = 'rate'):
    tag = self.get_tag(start_states, end_states)
    return self.datablocks[tag + "_" + stat].get_error()
  
  def process_results(self):
    results = self.ms_options.interface.results
    transition_paths = self.ms_options.interface.transition_lists
    
    times = [r.time for r in results]
    rates = [1.0/t for t in times if t != 0]
    self.datablocks["overall_time"].add_data(times)
    self.datablocks["overall_rate"].add_data(rates)
    
    new_data = {}
    for path in transition_paths:
      collapsed_path = collapse_transition_path(path)
      for start, end in zip(collapsed_path[0:-1], collapsed_path[1:]):
        time_diff = end[0] - start[0]
        key_start = ",".join(filter(lambda x: x[1], enumerate(start[1])))
        key_end = ",".join(filter(lambda x: x[1], enumerate(end[1])))
        key = key_start + "->" + key_end
        if key in new_data:
          new_data[key].append(time_diff)
        else:
          new_data[key] = [time_diff]
    
    for key, times in new_data.items():
      if (key + "_time") not in self.datablocks:
        self.datablocks[key + "_time"] = Datablock()
        self.datablocks[key + "_rate"] = Datablock(mean_func = rate_mean_func,
                                                   error_func = rate_error_func)
      self.datablocks[key + "_time"].add_data(times)
      self.datablocks[key + "_rate"].add_data([1.0/t for t in times if t != 0])
    
    del self.ms_options.interface.results[:]
    del self.ms_options.interface.transition_lists[:]
    
  def collapse_transition_path(transition_path):
    """transition path is a list of the form
       [[time1, [in_state1, in_state2, ...]]
        [time2, [in_state1, in_state2, ...]]
        ...]"""
    return filter(lambda x: sum(x[1])>0, transition_path)
    
  
  def reduce_error_to(self, rel_goal, abs_goal, start_states, end_states, stat = 'rate'):
    super(TransitionModeJob, self).reduce_error_to(rel_goal, abs_goal,
        self.get_tag(start_states, end_states), stat)
    
  def get_tag(self, start_states, end_states):
    assert all([s in self.states for s in start_states]), "Unknown start state given in %s" % start_states
    assert all([s in self.states for s in end_states]), "Unknown end state given in %s" % end_states
    key_start = ",".join([i for i,s
                            in enumerate(self.states)
                            if s in start_states])
    key_end = ",".join([i for i,s
                            in enumerate(self.states)
                            if s in end_states])
    return key_start + "->" + key_end


class FirstStepModeJob(MultistrandJob):
  
  datablocks = {}
  tags = None
  
  ms_options = None
  
  def __init__(self, start_state, stop_states, stop_tags = None):
  
    super(FirstStepModeJob, self).__init__(start_state, stop_states, stop_tags, FIRST_STEP_MODE)
      
    self.tags = [sc.tag for sc in self.ms_options.stop_conditions]
    self.tags.append("None")
    for tag in self.tags:
      self.datablocks[tag + "_prob"] = Datablock(std_func = bernoulli_std_func,
                                                  error_func = bernoulli_error_func)
      self.datablocks[tag + "_kcoll"] = Datablock(mean_func = rate_mean_func,
                                                  error_func = rate_error_func)
      self.datablocks[tag + "_k1"] = Datablock()
      self.datablocks[tag + "_k2"] = Datablock(mean_func = rate_mean_func,
                                                  error_func = rate_error_func)

  def process_results(self):
    results = self.ms_options.interface.results
    
    times = [r.time for r in results]
    rates = [1.0/t for t in times if t != 0]
    self.datablocks["overall_time"].add_data(times)
    self.datablocks["overall_rate"].add_data(rates)
    
    for r in [r for r in results if r.tag == None]:
      r.tag = "None"
    
    for tag in self.tags:
      relevant_sims = filter(lambda x: x.tag == tag, results)
      successes = map(lambda x: int(x.tag == tag), results)
      kcolls = [r.collision_rate for r in relevant_sims]
      k1s = map(lambda x: int(x.tag == tag) * x.collision_rate, results)
      k2s = [1.0 / r.time for r in relevant_sims if r.time != 0]
      self.datablocks[tag + "_prob"].add_data(successes)
      self.datablocks[tag + "_kcoll"].add_data(kcolls)
      self.datablocks[tag + "_k1"].add_data(k1s)
      self.datablocks[tag + "_k2"].add_data(k2s)
      
    del self.ms_options.interface.results[:]
    