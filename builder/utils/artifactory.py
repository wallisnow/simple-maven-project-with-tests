#!/usr/bin/python3

import requests, json, time, hashlib, tarfile, io, sys

from utils.common import log runCMD

from pathlib import Path

class ArtifactoryClient:

    def __init__(self, config):
        self.url = config["url"]
        self.retry_count = config["retry_count"]
        self.project = config["project"]

    def get(self, path, stream=False):
        r=None
        for i in range(0, self.retry_count):
            try:
                r = requests.get(self.__genUrl(path))
            except:
                log("Error: {} {}".format(sys.exc_info()[0], sys.exc_info()[1]))
                time.sleep(1)
                continue
            if r.status_code in [200, 404] :
                break
            else:
                time.sleep(1)
        return r

    def put(self, path, data, sha256):
        r=None
        for i in range(0, self.retry_count):
            try:
                headers = {'X-Checksum-Sha256': '{}'.format(sha256)}
                r = requests.put(self.__genUrl(path),
                                 data=data, headers=headers)
            except:
                time.sleep(1)
                continue
            if r.status_code in [201] :
                return True

        return False

    def putFile(self, file_path, target_path):
        '''
        Put file to artifactory
        Calculate sha256 checksum for file
        '''
        path = self.__getPath(target_path)

        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        with open(file_path, 'rb') as data:
            output = self.put(path, data=data, sha256=hash_sha256.hexdigest())
        return output

    def putDirectory(self, directory_path, target_path):
        '''
        Create temporarry tar file and upload it to artifactory
        '''
        tar_path = "tmp.tgz"
        if Path(tar_path).exists():
            Path(tar_path).unlink()

        cmd = ["tar", "-zcvf", tar_path, "-C", directory_path, "."]
        runCMD(cmd)
        self.putFile(tar_path, target_path)

        Path(tar_path).unlink()

    def getTar(self, source_path, output_path):
        path = self.__getPath(source_path)
        r = self.get(path)
        if r.status_code != 200:
            raise Exception("Failed to download {} code: {}".format(source_path,
                            r.status_code))
        tar = tarfile.open(fileobj=io.BytesIO(r.content), mode="r|gz")
        tar.extractall(output_path)
        tar.close()

    def getFile(self,target_path, file_path, check=False):
        '''
        Download file and check that checksum matches
        '''
        path = self.__getPath(target_path)
        sha_path = "{}.sha256".format(path)

        r = self.get(path, stream=True)

        hash_sha256 = hashlib.sha256()
        if r.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in r:
                    hash_sha256.update(chunk)
                    f.write(chunk)
        else:
            raise Exception("Failed to load {}, status({})".format(path,
                            r.status_code))

        if check:
            r = self.get(sha_path)
            if r.status_code == 200:
                if hash_sha256.hexdigest() ==  r.text:
                    return True
                else:
                    raise Exception("Checksum Failed: {} != {}".format(
                                    hash_sha256.hexdigest(), r.text))
            else:
                raise Exception("Failed to load {}, status({})".format(
                                sha_path,r.status_code))
        else:
            return True

    def getProjectPath(self):
        return "artifactory/{}".format(self.project)

    def search(self, pattern):
        r = self.get(self.__genSearchPath(pattern))
        if r.status_code == 500:
            raise Exception("Failed to search: {}".format(r.__dict__))
        return self.get(self.__genSearchPath(pattern))

    def searchFiles(self, pattern):
        r = self.search(pattern)
        if r.status_code >= 300:
            raise Exception("Failed to search: {}".format(r.__dict__))
        result = r.json()
        return result["files"]

    def findOneFile(self, path):
        files = self.searchFiles(path)
        return len(files) == 1

    # Private functions
    def __getPath(self,path):
        return "artifactory/{}/{}".format(self.project, path)

    def __genUrl(self, path):
        return "https://{}/{}".format(self.url, path)

    def __genSearchPath(self, pattern):
        return "artifactory/api/search/pattern?pattern={}:{}".format(
                self.project, pattern)
