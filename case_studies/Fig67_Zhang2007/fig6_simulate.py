# Perform data collection for Figure 6A-D (Entropy-driven catalyst, Zhang et al., Science 2007)

import kinda

# Change the MODE flag to 'demo' for quick-and-dirty results or 'publication' for more detailed results.
MODE = 'demo'

PIL_PATH = 'Zhang2007.pil'
DATA_PATH = 'fig6_raw.kinda'

#### Read domains, strands, and complexes from old-style PIL file
sstats = kinda.from_pil(PIL_PATH)


#### Analyze reaction rates.

## Collect all reactions to simulate.
## Here we simulate all enumerated and unproductive reactions but
## do not explicitly collect data for spurious reactions.
rxns = sstats.get_reactions(spurious = False)

print "Reaction analysis order:"
for i,r in enumerate(rxns):
  print i,r

## Set up parameters dict.
if MODE == 'demo':
  params = {
    'relative_error':  0.5,
    'init_batch_size': 50,
    'max_batch_size':  5000,
    'max_sims':        5000,
    'sims_per_update': 1
  }
elif MODE == 'publication':
  params = {
    'relative_error':  0.01,
    'init_batch_size': 500,
    'max_batch_size':  15000,
    'max_sims':        100000,
    'sims_per_update': 50
  }

## Simulate each reaction
for i, r in enumerate(rxns):
  print "\nAnalyzing reaction {}: {}".format(i,r)

  # Get stats object
  rxn_stats = sstats.get_stats(r)

  # Query k1 and k2 reaction rates to requested precision
  rxn_stats.get_k1(**params)
  rxn_stats.get_k2(**params)
  print "k1: {} +/- {}".format(rxn_stats.get_k1(max_sims=0), rxn_stats.get_k1_error(max_sims=0))
  print "k2: {} +/- {}".format(rxn_stats.get_k2(max_sims=0), rxn_stats.get_k2_error(max_sims=0))

## Export all collected data
kinda.export_data(sstats, DATA_PATH)


#### Analyze resting sets.

## Collect all resting sets to analyze.
restingsets = sstats.get_restingsets()

print "Resting set analysis order:"
for i,rs in enumerate(restingsets):
  print i,rs
print

## Set up parameters dict.
if MODE == 'demo':
  params = {
    'relative_error':  0.1,
    'init_batch_size': 50,
    'max_batch_size':  1000,
    'max_sims':        5000
  }
elif MODE == 'publication':
  params = {
    'relative_error':  0.005,
    'init_batch_size': 500,
    'max_batch_size':  10000,
    'max_sims':        500000
  }

## Analyze each resting set
for i,rs in enumerate(restingsets):
  print "\nAnalyzing resting set {}: {}".format(i,rs)

  # Get stats object
  rs_stats = sstats.get_stats(rs)

  # Query probabilities for all conformations (including the spurious conformation, denoted as None)
  rs_stats.get_conformation_probs(**params)
  for c in rs.complexes:
    print c.name, rs_stats.get_conformation_prob(c.name,max_sims=0), '+/-', rs_stats.get_conformation_prob_error(c.name,max_sims=0)

## Export all collected data
kinda.export_data(sstats, DATA_PATH)
