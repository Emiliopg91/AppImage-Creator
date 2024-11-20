import time
import hashlib
import os
import json
import math
import shutil
import tempfile
import requests
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

class MSync:
    block_size = 1 * 1024 * 1024

    def __init__(self, name, size, hash, blocks, url = None) -> None:
        self.name = name
        self.size = size
        self.hash = hash
        self.blocks = blocks
        self.url = url
    
    def to_file(self, file_path):
        data = {}
        data["name"] = self.name    
        data["size"] = self.size
        data["hash"] = self.hash
        data["blocks"] = self.blocks

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4) 

    def patch(self, file_path):
        t0=time.time()
        tmp_path = None
        session = requests.Session()
        try:
            file_hash = MSync.calculate_file_hash(file_path)
            if file_hash == self.hash:
                print(f"No changes detected for file '{file_path}'")
                return
            
            print(f"Patching changes for '{file_path}'")
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                print(f"Copying to working copy '{tmp_file.name}'")
                shutil.copy2(file_path, tmp_file.name)
                tmp_path = tmp_file.name

            with open(tmp_path, 'rb+') as file:
                print(f"Adjusting file size to {self.size} bytes")
                current_size = MSync.get_file_size(tmp_path)
                if current_size < self.size:
                    file.write(b'\0' * (self.size - current_size))
                    print(f"    File padded with {(self.size - current_size)} zeros")
                elif current_size > self.size:
                    file.truncate(self.size)
                    print(f"    File truncated by {(current_size - self.size)} bytes")

            print("Checking blocks to patch")
            blocks = MSync.get_file_blocks(tmp_path)
            changed_blocks = []
            for i in range(len(blocks)):
                if blocks[i] != self.blocks[i]:
                    changed_blocks.append(i)

            grouped_blocks = MSync._group_blocks(self.size, changed_blocks)
            total_size = 0
            for start, end in grouped_blocks:
                total_size += (end - start)

            print(f"Need to patch {len(changed_blocks)}/{len(self.blocks)} blocks.")
            print(f"Estimated download size: {total_size}/{self.size} bytes ({math.floor(10000 * (total_size) / self.size) / 100}%)")

            parsed_url = urlsplit(self.url)
            base_path = '/'.join(parsed_url.path.split('/')[:-1])
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}/{self.name}"

            with ThreadPoolExecutor() as executor:
                futures = []
                for start, end in grouped_blocks:
                    futures.append(executor.submit(MSync.download_chunk, session, start, end, url))

                with open(tmp_path, 'r+b') as f:
                    for future in as_completed(futures):
                        data, start, end = future.result()
                        f.seek(start)
                        f.write(data)

            print("Checking integrity after update")
            hash = MSync.calculate_file_hash(tmp_path)
            if hash == self.hash:
                print("    Integrity test passed successfully")
                print("Setting permissions")
                permissions = os.stat(file_path).st_mode
                os.remove(file_path)
                shutil.copy2(tmp_path, file_path)
                os.chmod(file_path, permissions)

                print(f"MSync patch finished after {time.time() - t0}")
            else:
                raise Exception("Checksum doesn't match")
        finally:
            if tmp_path is not None:
                os.remove(tmp_path)
            session.close()

    @staticmethod
    def from_url(url:str):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        data = response.json()

        return MSync(data["name"], data["size"], data["hash"], data["blocks"], url)

    @staticmethod
    def from_binary(file_path:str):
        name = os.path.basename(file_path)
        size = MSync.get_file_size(file_path)
        hash = MSync.calculate_file_hash(file_path)
        blocks = MSync.get_file_blocks(file_path)
        
        return MSync(name, size, hash, blocks)


    @staticmethod
    def get_file_blocks(file_path):
        blocks = []
        futures = []

        with open(file_path, 'rb') as f, ThreadPoolExecutor() as executor:
            while True:
                block = f.read(MSync.block_size)
                if not block:
                    break
                
                futures.append(executor.submit(MSync.calculate_block_hash, block))

            for future in futures:
                blocks.append(future.result())

        return blocks
             
    @staticmethod   
    def get_file_size(file_path):
        return os.stat(file_path).st_size
                
    @staticmethod
    def calculate_block_hash(block):
        md5_hash = hashlib.md5()
        md5_hash.update(block)
        return md5_hash.hexdigest()
    
    @staticmethod
    def calculate_file_hash(file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def download_chunk(session, start, end, url):
        headers = {'Range': f'bytes={start}-{end - 1}'}  # Ajuste: rango es inclusivo
        response = session.get(url, headers=headers, stream=True)

        if response.status_code not in [200, 206]:
            raise Exception(f"Error en la descarga: {response.status_code}")

        chunk = b"".join(response.iter_content(chunk_size=end - start))
        return chunk, start, end

    @staticmethod
    def _group_blocks(file_size, changed_blocks):
        grouped = []
        start_index = changed_blocks[0]  
        
        for i in range(1, len(changed_blocks)):
            if changed_blocks[i] != changed_blocks[i - 1] + 1:
                end_index = changed_blocks[i - 1]
                grouped.append((start_index, end_index))
                start_index = changed_blocks[i]
        
        # Agrega el último rango
        grouped.append((start_index, changed_blocks[-1]))
        
        ranges = [
            (
                start * MSync.block_size,
                min((end + 1) * MSync.block_size, file_size) 
            )
            for start, end in grouped
        ]
        return ranges
