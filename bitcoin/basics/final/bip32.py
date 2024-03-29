from binascii import hexlify
from binascii import unhexlify
from hashlib import sha256
from hashlib import sha512
import hmac
from ecc import PrivateKey, S256Point, Signature
from helper import encode_base58_checksum, decode_base58, decode_base58_extended, hash160
from io import BytesIO, StringIO

N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

class Xtended_privkey:
    
    def __init__(self, depth, fingerprint, index, chain_code, private_key, testnet = False):
        """
        All data must be bytes
        """
        self.testnet = testnet
        self.version = None
        self.depth = depth
        self.fingerprint = fingerprint
        self.index = index
        self.chain_code = chain_code
        self.private_key = private_key
        self.private_key_obj = PrivateKey(int.from_bytes(private_key,"big"))
        self.private_key_wif = PrivateKey(int.from_bytes(private_key,"big")).wif()
        self.xtended_key = self.get_xtended_key()
        self.xtended_public_key = self.extended_public_key()
        
        
    def __repr__(cls):
        return cls.get_xtended_key()
    
    
    def get_child_xtended_key(self, i):
       
        pub_key = PrivateKey(int.from_bytes(self.private_key,"big")).point.sec()
       
        child_fingerprint = hash160(pub_key)[:4]
     
        if i >= 2**31: 
            hardened=True
            msg=b'\x00' + self.private_key + i.to_bytes(4,"big")
        else: 
            hardened=False
            msg=pub_key + i.to_bytes(4,"big") 

        I= hmac.new(
                    key = self.chain_code,
                    msg=msg,
                    digestmod=sha512).digest()
        
        I_L, I_R = I[:32], I[32:]
        
        #Check if I_L is grater than N
        if int.from_bytes(I_L,"big")>=N : return self.get_child_xtended_key(self,i+1)
        
        
        child_privkey_int = (int.from_bytes(I_L,"big") + int.from_bytes(self.private_key,"big"))%N
        
        #check if public key is on the curve
        if PrivateKey(child_privkey_int).point.sec() is None:
            return self.get_child_xtended_key(self,i+1)
        #check if private key is 0
        if child_privkey_int==0 :
            return self.get_child_xtended_key(self,i+1)
                           
        child_chain_code = I_R
        
        child_depth = (int.from_bytes(self.depth,"big")+1).to_bytes(1,"big")
        
        self.extended_public_key()
        return Xtended_privkey(child_depth, child_fingerprint, i.to_bytes(4,"big"), 
                   child_chain_code, child_privkey_int.to_bytes(32,"big"),testnet = self.testnet)
        
        
        
    def get_child_from_path(self,path_string):
        child = self
        start = False
        begin = 0
        hardened = False
        for index,char in enumerate(path_string):
            
            if char == 'm' and index==0:
                continue
            elif char == '/':
                if start:
                    if hardened:
                        index = int(path_string[begin:index-1])+2**31
                        hardened = False
                    else:
                        index = int(path_string[begin:index])
                    child = child.get_child_xtended_key(index)
                    start = False
                continue
            elif char == "H" or char == "h":
                hardened = True
                continue
                
            elif not start:
                begin = index
                start = True
                
        if hardened:
            index = int(path_string[begin:-1])+2**31
            hardened = False
        else:
            index = int(path_string[begin:])
        child = child.get_child_xtended_key(int(index))
        return child
    
    
    def get_xtended_key(self):
        if self.testnet:
            version= 0x04358394.to_bytes(4,"big")
        else:
            version= 0x0488ade4.to_bytes(4,"big")
        
        pre_ser = version+self.depth+self.fingerprint+self.index+self.chain_code+b'\x00'+self.private_key
        return encode_base58_checksum(pre_ser)
    
    #@classmethod
    def get_xtended_public_key(self):
        return self.extended_public_key()
        
        
    def extended_public_key(self):
        pub_key =  PrivateKey(int.from_bytes(self.private_key,"big")).point.sec()
        x_pub_key = Xtended_pubkey(self.depth, self.fingerprint, self.index, 
                   self.chain_code, pub_key,testnet = self.testnet)
        self.xtended_public_key = x_pub_key
        return x_pub_key
        
    
    
    @classmethod
    def from_bip39_seed(cls, seed_int, testnet = False):
        I= hmac.new(
                    key = b"Bitcoin seed",
                    msg=seed_int.to_bytes(64,"big"),
                    digestmod=sha512).digest()
        return cls(depth=b'\x00', fingerprint=b'\x00'*4, index=b'\x00'*4, 
                   chain_code = I[32:], private_key=I[:32], testnet=testnet)
        
    
    @classmethod
    def parse(cls,xpk_string):
        testnet = None
        s = BytesIO(decode_base58_extended(xpk_string))
        version = s.read(4)
        if version == b"\x04\x35\x83\x94": 
            testnet = True
        elif version == b"\x04\x88\xad\xe4": 
                testnet = False
        depth = s.read(1)
        fingerprint = s.read(4)
        index= s.read(4)
        chain_code = s.read(32)
        s.read(1)
        privkey = s.read(32)
        return cls(depth=depth, fingerprint=fingerprint, index=index, 
                   chain_code = chain_code, private_key=privkey, testnet=testnet)

    
class Xtended_pubkey:
    
    def __init__(self, depth, fingerprint, index, chain_code, public_key, testnet = False):
        """
        All data must be bytes
        """
        self.testnet = testnet
        self.version = None
        self.depth = depth
        self.fingerprint = fingerprint
        self.index = index
        self.chain_code = chain_code
        self.public_key = public_key
        self.xtended_key = None
        
        
    def __repr__(cls):
        return cls.get_xtended_key()
    
    
    def get_child_xtended_key(self, i):
       
        child_fingerprint = hash160(self.public_key)[:4]
     
        if i >= 2**31: 
            hardened=True
            raise Exception ("Extended public keys not possible for hardened keys")
        else: 
            hardened=False
            msg=self.public_key + i.to_bytes(4,"big") 

        I= hmac.new(
                    key = self.chain_code,
                    msg=msg,
                    digestmod=sha512).digest()
        
        I_L, I_R = I[:32], I[32:]
        
        #Check if I_L is grater than N
        if int.from_bytes(I_L,"big")>=N : 
            return self.get_child_xtended_key(self,i+1)
        
        child_public_key = (PrivateKey(int.from_bytes(I_L,"big")).point + S256Point.parse(self.public_key)).sec()
        
        #check if public key is on the curve
        if child_public_key is None:
            return self.get_child_xtended_key(self,i+1)
                           
        child_chain_code = I_R
        
        child_depth = (int.from_bytes(self.depth,"big")+1).to_bytes(1,"big")
        
        return Xtended_pubkey(child_depth, child_fingerprint, i.to_bytes(4,"big"), 
                   child_chain_code, child_public_key,testnet = self.testnet)
        
        
        
    def get_child_from_path(self,path_string):
        child = self
        start = False
        begin = 0
        hardened = False
        for index,char in enumerate(path_string):
            
            if char == 'm' and index==0:
                continue
            elif char == '/':
                if start:
                    if hardened:
                        index = int(path_string[begin:index-1])+2**31
                        hardened = False
                    else:
                        index = int(path_string[begin:index])
                        
                    #######Child creation happens here #######
                    child = child.get_child_xtended_key(index)
                    start = False
                    
                continue
            elif char == "H" or char == "h":
                hardened = True
                continue
                
            elif not start:
                begin = index
                start = True
                
        #Last child created     
        if hardened:
            index = int(path_string[begin:-1])+2**31
            hardened = False
        else:
            index = int(path_string[begin:])
        child = child.get_child_xtended_key(int(index))
        return child
    
    
    def get_xtended_key(self):
        if self.testnet:
            version= 0x043587cf.to_bytes(4,"big")
        else:
            version= 0x0488b21e.to_bytes(4,"big")
        
        pre_ser = version+self.depth+self.fingerprint+self.index+self.chain_code+self.public_key
        return encode_base58_checksum(pre_ser)
        
    
    @classmethod
    def parse(self,xpk_string):
        testnet = None
        s = BytesIO(decode_base58_extended(xpk_string))
        version = s.read(4)
        if version == b'\x04\x35\x87\xcf': 
            testnet = True
        elif version == b'\x04\x88\xb2\x1e': 
                testnet = False
        depth = s.read(1)
        fingerprint = s.read(4)
        index= s.read(4)
        chain_code = s.read(32)
        pubkey = s.read(33)
        return Xtended_pubkey(depth=depth, fingerprint=fingerprint, index=index, 
                   chain_code = chain_code, public_key=pubkey, testnet=testnet)