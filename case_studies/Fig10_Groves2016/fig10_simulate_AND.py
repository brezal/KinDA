# Perform data collection for Figure 10 (Groves et al., Nature Nanotechnology 2016)
# AND gate

import time
import kinda
 
# Change the MODE flag to 'demo' for quick-and-dirty results or 'publication' for more detailed results.
MODE = 'demo'

PILPATH = 'Groves2016_AND.pil'
OUTPUT_PREFIX = 'Groves2016_AND'
 
def simulate(sim_mode):
  ## Setup KinDA initialization parameters
  peppercorn_params = {
    'k_fast': 5e-7
  }
  kinda_params = {
    'stop_macrostate_mode': sim_mode,
    'start_macrostate_mode': 'ordered-complex'
  }
 
  ## Construct System object
  sstats = kinda.from_pil(PILPATH, peppercorn_params = peppercorn_params, kinda_params = kinda_params)
 
  ## Find relevant resting sets
  rs_InputA = sstats.get_restingset(complex_name = 'InA')
  rs_InputB = sstats.get_restingset(complex_name = 'InB')
  rs_AND = sstats.get_restingset(complex_name = 'AND')
 
  ## Get relevant reactions
  rxns = sstats.get_reactions(spurious = False, unproductive = False)
 
  print "Reaction analysis order:"
  for i, rxn in enumerate(rxns):
    print i, rxn
 
  rxn_times = []
  for rxn in rxns:
    print "Analyzing", rxn
 
    start_time = time.time()

    ## Run simulations
    rxn_stats = sstats.get_stats(rxn)
    rxn_stats.get_k1(**params)
    rxn_stats.get_k2(**params)

    end_time = time.time()
 
    print "k1: {} +/- {}".format(rxn_stats.get_k1(max_sims=0), rxn_stats.get_k1_error(max_sims=0))
    print "k2: {} +/- {}".format(rxn_stats.get_k2(max_sims=0), rxn_stats.get_k2_error(max_sims=0))

    rxn_times.append(end_time - start_time)

    print "Finished analyzing {} in {} seconds\n".format(rxn, end_time - start_time)
 
  ## Store results 
  kinda.export_data(sstats, '{}_{}.kinda'.format(OUTPUT_PREFIX, sim_mode))
 
  return sstats, zip(rxns, rxn_times)

if MODE == 'demo':
  params = {
    'relative_error':  0.5,
    'init_batch_size': 50,
    'max_batch_size':  5000,
    'max_sims':        5000,
  }
elif MODE == 'publication':
  params = {
    'relative_error':  0.025,
    'init_batch_size': 500,
    'max_batch_size':  10000,
    'max_sims':        500000,
    'sims_per_worker': 5
  }
 
## Run simulations at each mode
sstats_disassoc = simulate('ordered-complex')
sstats_cbc = simulate('count-by-complex')
sstats_cbd = simulate('count-by-domain')
