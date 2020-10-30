from ipsframework.ips import Framework
import glob
import json
import pytest


def write_basic_config_and_platform_files(tmpdir):
    test_component = tmpdir.join("test_component.py")

    driver = """#!/usr/bin/env python3
from ipsframework.component import Component
class test_driver(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
"""

    with open(test_component, 'w') as f:
        f.write(driver)

    platform_file = tmpdir.join('platform.conf')

    platform = """MPIRUN = eval
NODE_DETECTION = manual
CORES_PER_NODE = 1
SOCKETS_PER_NODE = 1
NODE_ALLOCATION_MODE = shared
HOST =
SCRATCH =
"""

    with open(platform_file, 'w') as f:
        f.write(platform)

    config_file = tmpdir.join('ips.config')

    config = f"""RUN_COMMENT = testing
SIM_NAME = test
LOG_FILE = {str(tmpdir)}/log.warning
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER
    [[DRIVER]]
        IMPLEMENTATION = test_driver
[test_driver]
    CLASS = driver
    SUB_CLASS =
    NAME = test_driver
    NPROC = 1
    BIN_PATH =
    INPUT_DIR =
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT = {test_component}
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_framework_simple(tmpdir, capfd):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    assert framework.log_file_name.endswith('test.log')

    assert len(framework.config_manager.get_framework_components()) == 2

    component_map = framework.config_manager.get_component_map()

    assert len(component_map) == 1
    assert 'test' in component_map
    test = component_map['test']
    assert len(test) == 1
    assert test[0].get_class_name() == 'test_driver'
    assert test[0].get_instance_name().startswith('test@test_driver')
    # assert test[0].get_seq_num() == 1 # need to find a way to reset static variable
    assert test[0].get_serialization().startswith('test@test_driver')
    assert test[0].get_sim_name() == 'test'

    framework.run()

    # check simulation_log
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        json_lines = json_file.readlines()

    assert len(json_lines) == 3

    event0 = json.loads(json_lines[0])
    event1 = json.loads(json_lines[1])
    event2 = json.loads(json_lines[2])

    assert event0['eventtype'] == 'IPS_START'
    assert event1['eventtype'] == 'IPS_RESOURCE_ALLOC'
    assert event2['eventtype'] == 'IPS_END'

    for event in [event0, event1, event2]:
        assert str(event['ok']) == 'True'
        assert event['sim_name'] == 'test'

    captured = capfd.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_framework_empty_config_list(tmpdir):

    with pytest.raises(ValueError) as excinfo:
        Framework(config_file_list=[],
                  log_file_name=str(tmpdir.join('test.log')),
                  platform_file_name='platform.conf',
                  debug=None,
                  verbose_debug=None,
                  cmd_nodes=0,
                  cmd_ppn=0)

    assert str(excinfo).endswith("Missing config file? Something is very wrong")

    # check output log file
    with open(str(tmpdir.join('test.log')), 'r') as f:
        lines = f.readlines()

    assert len(lines) == 3
    assert lines[0].endswith("FRAMEWORK       ERROR    Missing config file? Something is very wrong\n")
    assert lines[1].endswith("FRAMEWORK       ERROR    Problem initializing managers\n")
    assert lines[2].endswith("FRAMEWORK       ERROR    exception encountered while cleaning up config_manager\n")


def test_framework_log_output(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.log("log message")
    framework.debug("debug message")
    framework.info("info message")
    framework.warning("warning message")
    framework.error("error message")
    framework.exception("exception message")
    framework.critical("critical message")

    # check output log file
    with open(str(tmpdir.join('test.log')), 'r') as f:
        lines = f.readlines()

    assert len(lines) == 9
    assert lines[5].endswith("FRAMEWORK       WARNING  warning message\n")
    assert lines[6].endswith("FRAMEWORK       ERROR    error message\n")
    assert lines[7].endswith("FRAMEWORK       ERROR    exception message\n")
    assert lines[8].endswith("FRAMEWORK       CRITICAL critical message\n")


def test_framework_log_output_debug(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=str(platform_file),
                          debug=True,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.log("log message")
    framework.debug("debug message")
    framework.info("info message")
    framework.warning("warning message")
    framework.error("error message")
    framework.exception("exception message")
    framework.critical("critical message")

    # check output log file
    with open(str(tmpdir.join('test.log')), 'r') as f:
        lines = f.readlines()

    assert len(lines) == 13
    assert lines[6].endswith("FRAMEWORK       INFO     log message\n")
    assert lines[7].endswith("FRAMEWORK       DEBUG    debug message\n")
    assert lines[8].endswith("FRAMEWORK       INFO     info message\n")
    assert lines[9].endswith("FRAMEWORK       WARNING  warning message\n")
    assert lines[10].endswith("FRAMEWORK       ERROR    error message\n")
    assert lines[11].endswith("FRAMEWORK       ERROR    exception message\n")
    assert lines[12].endswith("FRAMEWORK       CRITICAL critical message\n")
