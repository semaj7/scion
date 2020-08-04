#!/usr/bin/python3

import yaml
import os

def load_config(config_filename="ft-scripts/config-defaults.yaml"):
    # Load Default Config
    with open(config_filename, "r") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return config


# Define name for folder. Check if folder already exists and prompt new name if it does.
# Then make a folder
def generateUniqueResultDir(experiment_name):
    run_name = experiment_name
    while os.path.exists(run_name):
        print("Experiment folder ", run_name, " already exists.  ")
        run_name = input("Please choose a different name to store the graphs: ")

    if run_name[-1] != "/":
        print(run_name, " has: ", run_name[-1])
        run_name += '/'

    result_dir = generateResultDir(run_name)
    return result_dir


def generateResultDir(name):
    curr_path = os.getcwd()
    resultDir = curr_path + '/results/'
    #resultDir += datetime.strftime(datetime.now(), "%Y-%m-%d--%H-%M-%S") + "-"
    resultDir += name+ '/'
    os.system('mkdir -p ' + resultDir)
    for rT in ['hostlogs/', 'hostdata/', 'condensed/']:
        os.system('mkdir -p ' + resultDir+rT)
    return resultDir
