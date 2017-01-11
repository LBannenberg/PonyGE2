from random import randint, random, choice

from algorithm.parameters import params
from representation import individual
from representation.derivation import generate_tree

def mutation(pop):
    """
    Perform mutation on a population of individuals. Calls mutation operator as
    specified in params dictionary.
    
    :param pop: A population of individuals to be mutated.
    :return: A fully mutated population.
    """

    return list(map(params['MUTATION'], pop))


def int_flip(ind, within_used=True):
    """
    Mutate the genome of an individual by randomly choosing a new int with
    probability p_mut. Works per-codon. Mutation is performed over the
    effective length (i.e. within used codons, not tails) by default;
    within_used=False switches this off.
    
    :param ind: An individual to be mutated.
    :param within_used: Boolean flag for selecting whether or not mutation
    is confined to within the used portion of the genome. Default set to True.
    :return: A mutated individual.
    """

    # Set effective genome length over which mutation will be performed.
    if within_used:
        eff_length = min(len(ind.genome), ind.used_codons)
    else:
        eff_length = len(ind.genome)

    # Set mutation probability. Default is 1 over the length of the genome.
    if params['MUTATION_PROBABILITY']:
        p_mut = params['MUTATION_PROBABILITY']
    else:
        # Default mutation events per individual is 1. Raising this number
        # will influence the mutation probability for each codon.
        p_mut = params['MUTATION_EVENTS']/eff_length

    # Mutation probability works per-codon over the portion of the
    # genome as defined by the within_used flag.
    for i in range(eff_length):
        if random() < p_mut:
            ind.genome[i] = randint(0, params['CODON_SIZE'])

    # Re-build a new individual with the newly mutated genetic information.
    new_ind = individual.Individual(ind.genome, None)

    return new_ind


def int_flip_per_ind(ind, within_used=True):
    """
    Mutate the genome of an individual by randomly choosing a new int with
    probability p_mut. Works per-individual. Mutation is performed over the
    entire length of the genome by default, but the flag within_used is
    provided to limit mutation to only the effective length of the genome.
    
    :param ind: An individual to be mutated.
    :param within_used: Boolean flag for selecting whether or not mutation
    is confined to within the used portion of the genome. Default set to True.
    :return: A mutated individual.
    """
    
    # Set effective genome length over which mutation will be performed.
    if within_used:
        eff_length = min(len(ind.genome), ind.used_codons)
    else:
        eff_length = len(ind.genome)
    for _ in params['MUTATION_EVENTS']:
        idx = randint(0, eff_length-1)
        ind.genome[idx] = randint(0, params['CODON_SIZE'])
    
    # Re-build a new individual with the newly mutated genetic information.
    new_ind = individual.Individual(ind.genome, None)

    return new_ind
    

def subtree(ind):
    """
    Mutate the individual by replacing a randomly selected subtree with a
    new randomly generated subtree. Guaranteed one event per individual, unless
    params['MUTATION_EVENTS'] is specified as a higher number.
    
    :param ind: An individual to be mutated.
    :return: A mutated individual.
    """
    def subtree_mutate(ind_tree):
        """
        Creates a list of all nodes and picks one node at random to mutate.
        Because we have a list of all nodes, we can (but currently don't)
        choose what kind of nodes to mutate on. Handy.

        :param ind_tree: The full tree of an individual.
        :return: The full mutated tree and the associated genome.
        """

        # Find the list of nodes we can mutate from.
        targets = ind_tree.get_target_nodes([], target=params[
                                          'BNF_GRAMMAR'].non_terminals)

        # Pick a node.
        new_tree = choice(targets)

        # Set the depth limits for the new subtree.
        new_tree.max_depth = params['MAX_TREE_DEPTH'] - new_tree.depth

        # Mutate a new subtree.
        generate_tree(new_tree, [], [], "random", 0, 0, 0, new_tree.max_depth)

        return ind_tree

    def subtree_mutate_delete(ind_tree):
        """
        Picks a node at random to delete from the tree

        :param ind_tree: The full tree of an individual.
        :return: The full mutated tree and the associated genome.
        """
        # Find the list of nodes we can mutate from.
        targets = ind_tree.get_target_nodes([], target=params[
                                          'BNF_GRAMMAR'].non_terminals)

        # Pick a node.
        tree_for_deletion = choice(targets)

        if tree_for_deletion.parent:
            # do we need to rebuild the tree/genome?
            tree_for_deletion.parent.children.remove(tree_for_deletion)
            return ind_tree
        else:
            return subtree_mutate(ind_tree)

    # Save the tail of the genome.
    tail = ind.genome[ind.used_codons:]
    
    # Allows for multiple mutation events should that be desired.
    for i in range(params['MUTATION_EVENTS']):
        if params['SEMANTIC_LOCK']:
            ind.tree = semantic_mutate(ind.tree)
        # else:
        #     ind.tree = subtree_mutate(ind.tree)
        elif choice([True, False]): # too much?
            ind.tree = subtree_mutate(ind.tree)
        else:
            ind.tree = subtree_mutate_delete(ind.tree)
            
    # Re-build a new individual with the newly mutated genetic information.
    try:
        ind = individual.Individual(None, ind.tree)
    except RuntimeError as re:
        print("Tree generate error on recursion")
    
    # Add in the previous tail.
    ind.genome = ind.genome + tail

    return ind


def leaf_mutate(ind_tree):
    """
    Creates a list of all nodes and picks one node at random to mutate.
    Because we have a list of all nodes, we can (but currently don't)
    choose what kind of nodes to mutate on. Handy.

    :param ind_tree: The full tree of an individual.
    :return: The full mutated tree and the associated genome.
    """
    
    target = params['BNF_GRAMMAR'].non_terminals
    l_target = [i for i in target if target[i]['min_steps'] == 1]
    
    # Find the list of nodes we can mutate from.
    targets = ind_tree.get_target_nodes([], target=l_target)
    
    # Pick a node.
    new_tree = choice(targets)
    
    # Set the depth limits for the new subtree.
    new_tree.max_depth = params['MAX_TREE_DEPTH'] - new_tree.depth
    
    # Mutate a new subtree.
    generate_tree(new_tree, [], [], "random", 0, 0, 0, new_tree.max_depth)
    
    return ind_tree


def hillclimb(ind):
    """
    Mutate the individual by selecting a random subtree to mutate, then by
    mutating the CODON of that subtree up or down a number of steps (based
    on a probability distribution), and then mapping a new subtree from that
    new codon. Allows for hillclimbing local mutations
    
    :param ind: An individual to be mutated.
    :return: A mutated individual.
    """

    # Save the tail of the genome.
    tail = ind.genome[ind.used_codons:]

    # Allows for multiple mutation events should that be desired.
    for i in range(params['MUTATION_EVENTS']):
        if params['SEMANTIC_LOCK']:
            ind.tree = semantic_hillclimb_mutate(ind.tree)
        else:
            ind.tree = hillclimb_mutate(ind.tree)

    # Re-build a new individual with the newly mutated genetic information.
    ind = individual.Individual(None, ind.tree)

    # Add in the previous tail.
    ind.genome = ind.genome + tail

    return ind
