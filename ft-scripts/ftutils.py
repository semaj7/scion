#!/usr/bin/python3

import yaml

def load_config(config_filename="ft-scripts/config-defaults.yaml"):
    # Load Default Config
    with open(config_filename, "r") as ymlfile:
        config = yaml.load(ymlfile)
    return config
