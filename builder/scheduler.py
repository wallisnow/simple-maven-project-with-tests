#!/usr/bin/python3

import json, argparse, time
from os import path

from pathlib import Path

from utils.tarballbuilder import TarballBuilder
from utils.common import log, headerLog, loadConfig, parseMasterFile


def getLockFilePath(lock_name):
    return "/tmp/sheduler-lock-{}".format(lock_name)

# Lock for causing wait for other sheduler jobs to wait
# the first builder so that we do not build multiple times
def lockBuild(lock_name, timeout):
    filename = getLockFilePath(lock_name)

    if not Path(filename).exists():
        Path(filename).touch()
        return False

    for i in range(0, timeout):
        if not Path(filename).exists():
            return True
        time.sleep(1)

    # Free the lock so that this isn't permanently locked
    freeLock(lock_name)
    raise Exception("Lock was never released. Timeout!")

def freeLock(lock_name):
    filename = getLockFilePath(lock_name)
    try:
        Path(filename).unlink()
    except FileNotFoundError:
        pass

def exitMain(returncode, lock_name):
    # free the lock when exiting
    freeLock(lock_name)
    return returncode

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="config.json",
                        help="config file location")
    parser.add_argument('--commit', type=str,
                        help="What commit is used for build", required=True)
    parser.add_argument('--timeout', type=int, default=3600,
                        help="how long max we wait in lock")
    parser.add_argument('--skipcheck', action='store_true',
                        help="Build all")
    parser.add_argument('--type', type=str, default="container",
                        help="IBD or container package build")
    parser.add_argument('--masterdata', type=str,
                        default="../../build/container-list.json",
                        help="master config file")
    return parser.parse_args()

def main():
    args = getArgs()

    configs=loadConfig(args.config)

    _, _, _, _, version = parseMasterFile(args.masterdata)
    commit = args.commit[:8]

    tarbuilder = TarballBuilder(configs["tar_client_config"])

    # lock the build that other jobs can not build same thing
    # only first one will check if build is needed and others
    # will just exit as build has to be done as they where waiting
    lock_name = "{}-{}-{}.lock".format(version, commit, args.type)
    if lockBuild(lock_name, args.timeout):
        return exitMain(0, lock_name)
    else:
        if args.type == "container":
            if args.skipcheck or not tarbuilder.findBuild(version, commit):
                print("Build is needed")
                return exitMain(2, lock_name)
        elif args.skipcheck or args.type == "ibd":
            if needsToBuildIbd(args.buildall):
                print("Build is needed")
                return exitMain(2, lock_name)
        else:
            msg = "Invalid type: {}, should be ibd or container"
            raise Exception(msg.format(args.type))
    print("No need to build")
    return exitMain(0, lock_name)

main()
