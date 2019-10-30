"""

Output Simplifier

Takes ncsmc output (.out) files, grabs info about bound states,
and outputs a ".out_simplified" file in the same spot as the original.

Can be run by editing the filename parameter in this file,
or just running the file with the command:

python output_simplifier.py -f [filename]

"""
import argparse
import re

from . import utils

# enter a filename here,
# or run this with "python output_simplifier.py -f [file]"
filename = "ncsmc_output/ncsm_rgm_Am2_1_1.out"

# edit these two if you want to change the format of the output
file_format = """Simplified View of {filename}:

(only includes bound states)

Threshold Energy = {thresh_E} MeV
Groud State Energy = {ground_E} MeV

{states}
=========================================================================
"""

state_format = """
=========================================================================
State Energy = {E} MeV
J = {J}
T = {T}
Parity = {parity}

Details:
{details}"""

# a bunch of tiny functions for parsing data
def j_parity_line(line):
    """
    checks if line is of the form 
    
    2*J=  6    parity=-1
    """
    regex = r"[ ]*2\*J=[ ]*[-]?[0-9]*[ ]*parity=[ ]*[-]?[0-9]*\n"
    return bool(re.match(regex, line))
def get_j_parity(line):
    """assuming j_parity_line(line) == True, return J, parity"""
    # remove everything except necessary info
    just_nums = line.replace("2*J=", "").replace("parity=", "")
    # get the two "words", i.e. numbers, separated by spaces
    Jx2, parity = just_nums.split()
    J = int(Jx2)/2
    return J, parity
def t_line(line):
    """
    checks if line is of the form 
    
    2*T= 0
    """ 
    regex = r"[ ]*2\*T=[ ]*[-]?[0-9]*\n"
    return bool(re.match(regex, line))
def get_t(line):
    """assuming t_line(line) == True, return T"""
    Tx2 = line.replace("2*T=", "")
    T = int(Tx2)/2
    return T
def bound_state_line(line):
    """
    checks if line is of the form 
    
    Bound state found at E_b=[energy] [unit]
    """ 
    return "Bound state found at E_b=" in line
def get_e(line):
    """assuming bound_state_line(line) == True, return E"""
    # remove the initial bit, as well as extra whitespace
    with_units = line.replace("Bound state found at E_b=", "").strip()
    E = with_units.split()[0]  # first "word" = E, second = units
    return float(E)
def groud_e_line(line):
    return "Ground-state E=" in line
def get_ground_e(line):
    """line looks like:
    Ground-state E= -68.4838  T_rel=   9.3033  [...]"""
    # remove initial bit
    line = line.replace("Ground-state E=", "")
    # then after that, it'll be the first "word", strip whitespace too
    E = line.split()[0].strip()
    return float(E)
def thresh_e_line(line):
    return "Threshold E=" in line
def get_thresh_e(line):
    """line looks like:
     Threshold E= -69.0645 MeV"""
    # remove the first bit, as well as any extra whitespace
    with_units = line.replace("Threshold E=", "").strip()
    E = with_units.split()[0]  # first "word" = E, second = units
    return float(E)


def simplify(filename):
    """
    Makes a simpler version of ncsmc .out files,
    no more scrolling through 100000 line files!
    """
    filename = utils.abs_path(filename)
    print("Simplifying "+filename)
    # get all lines from the file, as a list of strings
    with open(filename, "r+") as file_to_simplify:
        lines = file_to_simplify.readlines()

    # if something went wrong, we'll see this where the right value should be
    default = "ERROR"

    # constant parameters
    ground_E, thresh_E = default, default

    # parameters for each bound state
    E, J, T, parity, details = default, default, default, default, default

    # this will hold strings describing states
    states = []

    """
    Steps:

    1. Look for J, parity, T.
        - we may have many of these values before seeing a bound state
        - keep the most recent values before the bound state is mentioned
    2. Get bound state energy
    3. Get details
    """
    # start by searching for a bound state
    step = "looking for bound state"
    for line in lines:
        # if we can get one of the constants for this file, do it
        if groud_e_line(line):
            ground_E = get_ground_e(line)
        elif thresh_e_line(line):
            thresh_E = get_thresh_e(line)

        # get J, T, parity, E
        elif step in ["looking for bound state", "done"]:
            # safe to assume that if we find a bound state, we'll find
            # J, parity, T first, so no need to make that its own step
            if j_parity_line(line):
                J, parity = get_j_parity(line)
            elif t_line(line):
                T = get_t(line)
            # then keep looking for a bound state.
            # if we find new J, parity, T values we'll update as needed

            elif bound_state_line(line):
                E = get_e(line)
                step = "looking for details" 

        # get the first detail line
        elif step == "looking for details":
            if "i_p,p_chan,p_st" in line:
                details = line
                step = "getting details"
        # get all other detail lines
        elif step == "getting details":
            if "i_p,p_chan,p_st" in line:
                details += line
            else:
                # once we've found the first line after the details,
                # save state and move on to the next one
                states.append(state_format.format(
                    E=E, J=J, T=T, parity=parity, details=details))
                # set some parameters back to default, but not all
                # since some might be the same as for the next state
                E, details = default, default
                # back to the first step / look for next bound state
                step = "looking for bound state"

    # ensure we didn't end part way through processing a state
    if step != "looking for bound state":
        raise IOError("unable to parse file correctly, exited at wrong step!")

    # write everything to a file
    if len(states) == 0:
        states = "No bound states found..."
    else:
        states = "".join(states)
    file_str = file_format.format(
        filename=filename,
        ground_E=ground_E,
        thresh_E=thresh_E,
        states=states)
    with open(filename+"_simplified", "w+") as out_file:
        out_file.write(file_str)
    print("Done simplifying!")
    print("Output: "+filename+"_simplified")

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Output Simplifier")
    parser.add_argument("-f", nargs='?', const=None, help="filepath", type=str)
    args = parser.parse_args()
    if args.f is not None:
        simplify(args.f)
    else:
        simplify(filename)
