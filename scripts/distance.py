#!/usr/bin/env python3

import argparse
import collections
import functools
import networkx as nx


class memoize:
  # From https://github.com/S2E/s2e-env/blob/master/s2e_env/utils/memoize.py

  def __init__(self, func):
    self._func = func
    self._cache = {}

  def __call__(self, *args):
    if not isinstance(args, collections.abc.Hashable):
      return self._func(args)

    if args in self._cache:
      return self._cache[args]

    value = self._func(*args)
    self._cache[args] = value
    return value

  def __repr__(self):
    # Return the function's docstring
    return self._func.__doc__

  def __get__(self, obj, objtype):
    # Support instance methods
    return functools.partial(self.__call__, obj)


#################################
# Get graph node name
#################################
def node_name (name):
  if is_cg:
    return "\"{%s}\"" % name
  else:
    return "\"{%s:" % name

#################################
# Find the graph node for a name
#################################
@memoize
def find_nodes (name):
  n_name = node_name (name)
  return [n for n, d in G.nodes(data=True) if n_name in d.get('label', '')]

##################################
# Calculate Distance
##################################
def distance (name):
  if not is_cg and name in bb_distance.keys():
    out.write(name)
    out.write(",")
    out.write(str(10 * bb_distance[name]))
    out.write("\n")
    return
  distance = -1
  for n in find_nodes (name):
    d = 0.0
    i = 0

    if is_cg:
      for t in targets:
        try:
          shortest = nx.dijkstra_path_length (G, n, t)
          d += 1.0 / (1.0 + shortest)
          i += 1
        except nx.NetworkXNoPath:
          pass
    else:
      for t_name, bb_d in bb_distance.items():
        di = 0.0
        ii = 0
        for t in find_nodes(t_name):
          try:
            shortest = nx.dijkstra_path_length(G, n, t)
            di += 1.0 / (1.0 + 10 * bb_d + shortest)
            ii += 1
          except nx.NetworkXNoPath:
            pass
        if ii != 0:
          d += di / ii
          i += 1

    if d != 0 and (distance == -1 or distance > i / d) :
      distance = i / d

  if distance != -1:
    out.write (name)
    out.write (",")
    out.write (str (distance))
    out.write ("\n")

##################################
# Main function
##################################
if __name__ == '__main__':
  parser = argparse.ArgumentParser ()
  parser.add_argument ('-d', '--dot', type=str, required=True, help="Path to dot-file representing the graph.")
  parser.add_argument ('-t', '--targets', type=str, required=True, help="Path to file specifying Target nodes.")
  parser.add_argument ('-o', '--out', type=str, required=True, help="Path to output file containing distance for each node.")
  parser.add_argument ('-n', '--names', type=str, required=True, help="Path to file containing name for each node.")
  parser.add_argument ('-c', '--cg_distance', type=str, help="Path to file containing call graph distance.")
  parser.add_argument ('-s', '--cg_callsites', type=str, help="Path to file containing mapping between basic blocks and called functions.")

  args = parser.parse_args ()

  print ("\nParsing %s .." % args.dot)
  G = nx.DiGraph(nx.drawing.nx_pydot.read_dot(args.dot))
  print (nx.info(G))

  is_cg = "Name: Call graph" in nx.info(G)
  print ("\nWorking in %s mode.." % ("CG" if is_cg else "CFG"))

  # Process as ControlFlowGraph
  caller = ""
  cg_distance = {}
  bb_distance = {}
  if not is_cg :

    if args.cg_distance is None:
      print ("Specify file containing CG-level distance (-c).")
      exit(1)

    elif args.cg_callsites is None:
      print ("Specify file containing mapping between basic blocks and called functions (-s).")
      exit(1)

    else:

      caller = args.dot.split(".")
      caller = caller[len(caller)-2]
      print ("Loading cg_distance for function '%s'.." % caller)

      with open(args.cg_distance, 'r') as f:
        for l in f.readlines():
          s = l.strip().split(",")
          cg_distance[s[0]] = float(s[1])

      if not cg_distance:
        print ("Call graph distance file is empty.")
        exit(0)

      with open(args.cg_callsites, 'r') as f:
        for l in f.readlines():
          s = l.strip().split(",")
          if find_nodes(s[0]):
            if s[1] in cg_distance:
              if s[0] in bb_distance:
                if bb_distance[s[0]] > cg_distance[s[1]]:
                  bb_distance[s[0]] = cg_distance[s[1]]
              else:
                bb_distance[s[0]] = cg_distance[s[1]]

      print ("Adding target BBs (if any)..")
      with open(args.targets, "r") as f:
        for l in f.readlines ():
          s = l.strip().split("/");
          line = s[len(s) - 1]
          if find_nodes(line):
            bb_distance[line] = 0
            print ("Added target BB %s!" % line)

  # Process as CallGraph
  else:

    print ("Loading targets..")
    with open(args.targets, "r") as f:
      targets = []
      for line in f.readlines ():
        line = line.strip ()
        for target in find_nodes(line):
          targets.append (target)

    if (not targets and is_cg):
      print ("No targets available")
      exit(0)

  print ("Calculating distance..")
  with open(args.out, "w") as out, open(args.names, "r") as f:
    for line in f.readlines():
      distance (line.strip())
