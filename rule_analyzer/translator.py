"""
Translate the given datalog rules into sql query mapping info -
which can later be used to generate the corresponding sql queries
"""
import collections
from copy import deepcopy


def extract_variable_arg_to_atom_map(body_atoms):
    """ Extract and return the mapping between 
        each body variable argument to the indexes of body atoms containing the argument

        Args:
            body_atoms: 
                the list of atoms of the datalog rule body

        Return:
            variable_arg_to_atom_map: {<key, value>}
                key - argument name 
                value - {<key, value>}
                        key - atom index
                        value - list of argument index
    """
    body_atom_num = len(body_atoms)
    variable_arg_to_atom_map = collections.OrderedDict()
    for atom_index in range(body_atom_num):
        atom = body_atoms[atom_index]
        atom_arg_list = atom['arg_list']
        atom_arg_num = len(atom_arg_list)
        for arg_index in range(atom_arg_num):
            arg = atom_arg_list[arg_index]
            if arg.type != 'variable':
                continue
            if arg.name not in variable_arg_to_atom_map:
                variable_arg_to_atom_map[arg.name] = collections.OrderedDict()
            if atom_index not in variable_arg_to_atom_map[arg.name]:
                variable_arg_to_atom_map[arg.name][atom_index] = list()
            variable_arg_to_atom_map[arg.name][atom_index].append(arg_index)

    return variable_arg_to_atom_map


def search_argument_mapping_in_body_atoms(variable_arg_to_atom_map, var_name):
    """ Return the first atom-arg index pair found matching the given argument name 

        Args:
            variable_arg_to_atom_map:
                mapping between 
                each body variable argument to the indexes of body atoms containing the argument
            var_name:
                the variable name 
    """
    atom_index_to_arg_index_map = variable_arg_to_atom_map[var_name]
    # return the the indices of the first mapped atom and argument found
    for atom_index in atom_index_to_arg_index_map:
        for arg_index in atom_index_to_arg_index_map[atom_index]:
            return {'atom_index': atom_index, 'arg_index': arg_index}

    return None

def extract_selection_map(head, variable_arg_to_atom_map):
    """ Extract and store the information for attributes selected (computed) from the datalog rule/query

        Args:
            body_atoms: 
                the list of atoms of the datalog rule body
            variable_arg_to_atom_map:
                mapping between 
                each body variable argument to the indexes of body atoms containing the argument

    """
    head_arg_list = head['arg_list']
    head_arg_num = len(head_arg_list)

    # map arguments of the head to the position of the corresponding arguments in the body
    head_arg_to_body_atom_arg_map = collections.OrderedDict()
    # map arguments of the head to the specific type (e.g., variable, aggregation, constants)
    head_arg_type_map = list()
    # map the aggregation attributes of the head to the specific aggregation operator
    head_aggregation_map = dict()
    for arg_index in range(head_arg_num):
        head_arg = head_arg_list[arg_index]
        if head_arg.type == 'variable':
            head_arg_name = head_arg.name
            head_arg_type_map.append('var')
            head_arg_to_body_atom_arg_map[arg_index] = search_argument_mapping_in_body_atoms(
                variable_arg_to_atom_map, head_arg_name)

        elif head_arg.type == 'aggregation':
            head_arg_name = head_arg.name['agg_arg']
            head_arg_type_map.append('agg')
            head_aggregation_map[arg_index] = head_arg.name['agg_op']
            if head_arg_name['type'] == 'attribute':
                head_arg_to_body_arg_map = search_argument_mapping_in_body_atoms(
                    variable_arg_to_atom_map, head_arg_name['content'])
                head_arg_to_body_atom_arg_map[arg_index] = \
                    {'type': 'attribute', 'map': head_arg_to_body_arg_map}
            elif head_arg_name['type'] == 'math_expr':
                math_expr = head_arg_name['content']
                lhs_variable_arg_name = math_expr['lhs']
                rhs_variable_arg_name = math_expr['rhs']
                math_op = math_expr['op']
                lhs_variable_arg_mapping = search_argument_mapping_in_body_atoms(
                    variable_arg_to_atom_map, lhs_variable_arg_name)
                rhs_variable_arg_mapping = search_argument_mapping_in_body_atoms(
                    variable_arg_to_atom_map, rhs_variable_arg_name)
                head_arg_to_body_atom_arg_map[arg_index] = \
                    {'type': 'math_expr', 'lhs_map': lhs_variable_arg_mapping,
                     'rhs_map': rhs_variable_arg_mapping, 'math_op': math_op}

        elif head_arg.type == 'math_expr':
            head_arg_type_map.append('math_expr')
            math_expr = head_arg.name
            lhs_variable_arg_name = math_expr['lhs']
            rhs_variable_arg_name = math_expr['rhs']
            math_op = math_expr['op']
            lhs_variable_arg_mapping = search_argument_mapping_in_body_atoms(
                variable_arg_to_atom_map, lhs_variable_arg_name)
            rhs_variable_arg_mapping = search_argument_mapping_in_body_atoms(
                variable_arg_to_atom_map, rhs_variable_arg_name)
            head_arg_to_body_atom_arg_map[arg_index] = \
                {'type': 'math_expr', 'lhs_map': lhs_variable_arg_mapping,
                 'rhs_map': rhs_variable_arg_mapping, 'math_op': math_op}

        elif head_arg.type == 'constant':
            head_arg_type_map.append('constant')
            head_arg_to_body_atom_arg_map[arg_index] = head_arg.name

    return {
        'head_arg_to_body_atom_arg_map': head_arg_to_body_atom_arg_map,
        'head_arg_type_map': head_arg_type_map,
        'head_aggregation_map': head_aggregation_map
    }


def extract_join_map(variable_arg_to_atom_map):
    """
        Args:
            variable_arg_to_atom_map:
                mapping between 
                each body variable argument to the indexes of body atoms containing the argument
        Returns:
            join_map:
                mapping beween join variable name to the indices of join atoms and variable positions
    """
    join_map = collections.OrderedDict()
    for var in variable_arg_to_atom_map:
        join_on_var = False
        # same variable shown in different atoms
        if len(variable_arg_to_atom_map[var]) > 1:
            join_on_var = True
        # same variable shown more than once in the same atom
        for atom in variable_arg_to_atom_map[var]:
            if len(variable_arg_to_atom_map[var][atom]) > 1:
                join_on_var = True
                break
        if join_on_var:
            join_map[var] = variable_arg_to_atom_map[var]

    return join_map


def extract_comparison_map(body_comparisons, variable_arg_to_atom_map):
    """ Extract and store the information of comparison in the body

        Args:
            body_comparisons: 
                the comparison items of the rule body
            body_atoms: 
                the list of atoms of the datalog rule body

        Return:
            comparison_map
    """
    comparison_map = dict()
    for comparison in body_comparisons:
        lhs = comparison['lhs']
        rhs = comparison['rhs']
        lhs_arg = lhs[0]
        rhs_arg = rhs[0]
        lhs_arg_type = lhs[1]
        rhs_arg_type = rhs[1]
        if lhs_arg_type != 'var' and rhs_arg_type != 'var':
            raise Exception(
                'At least one side of the comparison has to be variable in the body relations')

        base_side = 'l'
        if lhs_arg_type == 'var':
            base_var = lhs_arg
            compare_arg = rhs_arg
            compare_arg_type = rhs_arg_type
        else:
            base_var = rhs_arg
            compare_arg = lhs_arg
            compare_arg_type = lhs_arg_type
            base_side = 'r'

        arg_to_body_atom_arg_map = search_argument_mapping_in_body_atoms(
            variable_arg_to_atom_map, base_var)
        mapped_atom_index = arg_to_body_atom_arg_map['atom_index']
        mapped_arg_index = arg_to_body_atom_arg_map['arg_index']
        if mapped_atom_index not in comparison_map:
            comparison_map[mapped_atom_index] = dict()
        if mapped_arg_index not in comparison_map[mapped_atom_index]:
            comparison_map[mapped_atom_index][mapped_arg_index] = list()
        comparison_struct = dict()
        comparison_struct['base_variable_side'] = base_side
        comparison_struct['compare_op'] = comparison['op']
        if compare_arg_type == 'num':
            comparison_struct['other_side_type'] = 'num'
            comparison_struct['numerical_value'] = float(compare_arg)
        else:
            other_side_atom_arg_indices = search_argument_mapping_in_body_atoms(
                variable_arg_to_atom_map, compare_arg)
            comparison_struct['other_side_type'] = 'var'
            comparison_struct['other_side_atom_index'] = other_side_atom_arg_indices['atom_index']
            comparison_struct['other_side_arg_index'] = other_side_atom_arg_indices['arg_index']

        comparison_map[mapped_atom_index][mapped_arg_index].append(
            comparison_struct)

    return comparison_map


def extract_constant_constraint_map(body_atoms):
    """ Extract constant specification in the rule body (e.g., T(x,y) :- X(x, 1), Y(x, 2))

        Args:
            body_atoms: 
                the list of atoms of the datalog rule body

        Return:
            constant_constraint_map: <key, value>
                key - body_atom_index
                value - <key, value>
                    key - body_atom_arg_index
                    value - body_atom_arg_constant_specification
    """
    body_atom_num = len(body_atoms)
    constant_constraint_map = dict()
    for atom_index in range(body_atom_num):
        atom = body_atoms[atom_index]
        atom_arg_list = atom['arg_list']
        atom_arg_num = len(atom_arg_list)
        for arg_index in range(atom_arg_num):
            arg_type = atom_arg_list[arg_index].type
            arg_name = atom_arg_list[arg_index].name
            if arg_type == 'constant':
                if atom_index not in constant_constraint_map:
                    constant_constraint_map[atom_index] = dict()
                constant_constraint_map[atom_index][arg_index] = arg_name

    return constant_constraint_map


def extract_negation_map(body_negation_atoms, variable_arg_to_atom_map):
    """Extract the negation in the rule body (e.g., T(x,y) :- A(x,w), B(w,y), !C(x,y).
       negation map can be considered as the "anti-join" map

        Args:
            body_negation_atoms:
                the list of negation atoms of the datalog rule body
            variable_arg_to_atom_map:
                mapping between 
                each body variable argument to the indexes of body atoms containing the argument

        Return:
            negation_map
    """
    body_negation_num = len(body_negation_atoms)
    negation_map = dict()
    anti_join_map = dict()
    for negation_index in range(body_negation_num):
        negation = body_negation_atoms[negation_index]
        negation_arg_list = negation['arg_list']
        negation_arg_num = len(negation_arg_list)
        negation_map[negation_index] = dict()
        negation_atom_map = negation_map[negation_index]
        for arg_index in range(negation_arg_num):
            negation_arg = negation_arg_list[arg_index]
            negation_arg_name = negation_arg.name
            negation_arg_type = negation_arg.type
            negation_atom_map[arg_index] = dict()
            negation_atom_map[arg_index]['arg_name'] = negation_arg_name
            negation_atom_map[arg_index]['arg_type'] = negation_arg_type

    for negation_atom_index in negation_map:
        negation_atom_map = negation_map[negation_atom_index]
        for arg_index in negation_atom_map:
            if negation_atom_map[arg_index]['arg_type'] == 'variable':
                arg_name = negation_atom_map[arg_index]['arg_name']
                arg_to_body_atom_arg_map = search_argument_mapping_in_body_atoms(
                    variable_arg_to_atom_map, arg_name)
                if arg_to_body_atom_arg_map is None:
                    continue 
                if negation_atom_index not in anti_join_map:
                    anti_join_map[negation_atom_index] = dict()
                anti_join_map[negation_atom_index][arg_index] = arg_to_body_atom_arg_map

    return {
        'negation_map': negation_map,
        'anti_join_map': anti_join_map
    }


def build_atom_aliases(body_atoms):
    """ Name each atom in the body with aliases and return the alias list

        Args:
            body_atoms:
                the list of atoms of the rule body
        Return:
            body_atom_alias_list:
                the list of aliases of the body atoms
    """
    body_atom_alias_list = list()
    body_atom_naming_index = 0
    for atom in body_atoms:
        alias = "{}_{}".format(atom['name'][0].lower(), body_atom_naming_index)
        body_atom_alias_list.append(alias)
        body_atom_naming_index += 1

    return body_atom_alias_list


def build_negation_atom_aliases(negation_atoms):
    """ Name each negation atom in the body with aliases and return the alias list

        Args:
            negation_atoms:
                the list of negation atoms of the rule body
        Return:
            negation_atom_alias_list:
                the list of aliases of negation atoms
    """
    negation_atom_aliases = list()
    negation_atom_naming_index = 0
    for negation_atom in negation_atoms:
        alias = "neg_{}_{}".format(
            negation_atom['name'][0].lower(), negation_atom_naming_index)
        negation_atom_aliases.append(alias)
        negation_atom_naming_index += 1

    return negation_atom_aliases


def build_recursive_atom_aliases(body_atoms, eval_idb_to_rule_maps, iter_num):
    """ Each idb atom in the body may have different aliases in terms of 'delta', 'prev' tables: 
            the function builds the list storing idb aliases (i.e. atom_aliases)
    """
    body_atom_num = len(body_atoms)
    body_atom_eval_names = list()
    idb_num = 0
    for atom in body_atoms:
        if atom['name'] in eval_idb_to_rule_maps:
            idb_num += 1
        atom_alias_list = list()
        body_atom_eval_names.append(atom_alias_list)

    for i in range(body_atom_num):
        atom_name = body_atoms[i]['name']
        atom_alias_list = body_atom_eval_names[i]
        # idb or edb not evaluated in the current rule group keeps the original name 
        if atom_name not in eval_idb_to_rule_maps:
            atom_alias_list.append({'alias': atom_name, 'type': 'default'})
        else:
            prev_idb_name = "{}_prev".format(atom_name)
            delta_idb_name = "{}_delta_{}".format(atom_name, iter_num - 1)
            atom_alias_list.append({'alias': prev_idb_name, 'type': 'prev'})
            atom_alias_list.append({'alias': delta_idb_name, 'type': 'delta'})

    return { 
        'body_atom_eval_names': body_atom_eval_names,
        'idb_num': idb_num
    }


def build_recursive_atom_alias_groups(body_atoms, atom_aliases_map):
    """ Datalog rules having multiple recursive idbs are evaluated by "multiple" subqueries, each of which
        has different combination of recursive atom aliases (e.g., 'delta', 'prev'):
            The function builds a list of combinations of idb aliases considering a single recursive datalog rule

        Args:
            body_atom_list: the list containing the atoms in the rule body
            body_atom_eval_names: the list containing the names of atoms to be evaluated
            eval_idbs:
                the list containing names of *all* idbs in the whole datalog program
            idb_num:
                the number of idbs in the current datalog rule being considered

        Return:
            atom_eval_name_groups:
                list containing groups of idb aliases each of which corresponds to a single recursive datalog rule
    """
    body_atom_num = len(body_atoms)
    body_atom_eval_names = atom_aliases_map['body_atom_eval_names']
    idb_num = atom_aliases_map['idb_num']
    atom_eval_name_groups = list()
    for atom_index in range(body_atom_num):
        atom_eval_names = body_atom_eval_names[atom_index]
        # just start to build the groups (i.e., just start DFS)
        if len(atom_eval_name_groups) == 0:
            for atom_eval_name in atom_eval_names:
                atom_eval_name_groups.append([atom_eval_name])
        else:
            # check to see if the node needs to split (check if the children number is more than 1)
            if len(atom_eval_names) > 1:
                group_increasing_factor = len(atom_eval_names) - 1
                groups_to_be_added = list()
                for i in range(group_increasing_factor):
                    groups_to_be_added.append(deepcopy(atom_eval_name_groups))
                # extend the existing groups with the first eval name of the current IDB to be evaluated
                for group in atom_eval_name_groups:
                    group.append(atom_eval_names[0])
                for k in range(group_increasing_factor):
                    for group in groups_to_be_added[k]:
                        group.append(atom_eval_names[k+1])
                        atom_eval_name_groups.append(group)
            else:
                for group in atom_eval_name_groups:
                    group.append(atom_eval_names[0])        
    
    # remove the group in which aliases of all recursive atoms are 'prev' (e.g., R_prev) - for semi-naive
    for group in atom_eval_name_groups:
        prev_count = 0
        for alias in group:
            if alias['type'] == 'prev':
                prev_count += 1
        if prev_count == idb_num:
            atom_eval_name_groups.remove(group)
    
    return atom_eval_name_groups