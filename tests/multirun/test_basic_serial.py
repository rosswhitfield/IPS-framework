from ipsframework.ips import Framework
import os
import shutil
import psutil
import pytest
import json
import glob


@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    # if an assert fails then not all the children may close and the
    # test will hang, so kill all the children
    children = psutil.Process(os.getpid()).children()
    for child in children:
        child.kill()


def copy_config_and_replace(infile, srcdir, tmpdir):
    with open(os.path.join(srcdir, infile), "r") as fin:
        with open(os.path.join(tmpdir, infile), "w") as fout:
            for line in fin:
                if line.startswith("SIM_ROOT"):
                    fout.write(f"SIM_ROOT = {tmpdir}\n")
                    IPS_ROOT = os.path.abspath(os.path.join(srcdir, '..', '..'))
                    fout.write(f"IPS_ROOT = {IPS_ROOT}\n")
                else:
                    fout.write(line)


def test_basic_serial1(tmpdir, capfd):
    datadir = os.path.dirname(__file__)
    copy_config_and_replace("basic_serial1.ips", datadir, tmpdir)
    shutil.copy(os.path.join(datadir, "platform.conf"), tmpdir)

    # setup 'input' files
    os.system(f"cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2")

    framework = Framework(do_create_runspace=True,
                          do_run_setup=True,
                          do_run=True,
                          config_file_list=[os.path.join(tmpdir, 'basic_serial1.ips')],
                          log_file_name=os.path.join(tmpdir, 'test.log'),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          compset_list=[],
                          debug=None,
                          ftb=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # Check stdout
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'small_worker.small_worker'>"
    assert captured_out[1] == "Created <class 'medium_worker.medium_worker'>"
    assert captured_out[2] == "Created <class 'large_worker.large_worker'>"
    assert captured_out[4] == "small_worker : init() called"
    assert captured_out[6] == "medium_worker : init() called"
    assert captured_out[8] == "large_worker : init() called"
    assert captured_out[10] == "Current time =  1.00"
    assert captured_out[11] == "Current time =  2.00"
    assert captured_out[12] == "Current time =  3.00"

    # check files copied and created
    driver_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("work/drivers_testing_basic_serial1_*/*")))]
    for infile in ["file1", "ofile1", "ofile2", "sfile1", "sfile2"]:
        assert infile in driver_files

    small_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("work/workers_testing_small_worker_*/*")))]
    medium_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("work/workers_testing_medium_worker_*/*")))]
    large_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("work/workers_testing_large_worker_*/*")))]

    for outfile in ["my_out1.00", "my_out2.00", "my_out3.00"]:
        assert outfile in small_worker_files
        assert outfile in medium_worker_files
        assert outfile in large_worker_files

    # cleanup
    for fname in ["test_basic_serial10.zip", "dask_preload.py"]:
        if os.path.isfile(fname):
            os.remove(fname)