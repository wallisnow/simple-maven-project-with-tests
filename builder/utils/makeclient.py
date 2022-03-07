#!/usr/bin/python3

from pathlib import Path
from utils.common import runCMD

class MakeClient:

    def __init__(self, config):
        self.root = config["root"]

    def make(self, source, cmd="", nofail=False):
        '''
        Run make <cmd> in source directory starting from root.
        '''
        exec_cmd = ["make", cmd]
        return runCMD(exec_cmd, cwd="{}/{}".format(self.root,source),
                        nofail=nofail)
