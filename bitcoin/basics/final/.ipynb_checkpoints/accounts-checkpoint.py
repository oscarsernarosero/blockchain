"""
This code makes use of the code written by Jimmy Song in the book Programming Bitcoin.
This code only tries to build on Jimmi Song's code and take it to the next step as 
suggested by him in chapter 14 of his book.
This module is coded entirely by Oscar Serna.

This is just an educational-purpose code. The author does not take any responsibility
on any losses caused by the use of this code.
"""

from ecc import PrivateKey, S256Point, Signature
from script import p2pkh_script, p2sh_script, Script, p2wpkh_script,p2wsh_script
from helper import (
    decode_base58, SIGHASH_ALL, h160_to_p2pkh_address, hash160, 
    h160_to_p2sh_address, encode_varint)
from tx import TxIn, TxOut, Tx, TxFetcher
import hashlib
from bip32 import Xtended_privkey, Xtended_pubkey
from bip39 import Mnemonic
import segwit_addr

class MasterAccount(Xtended_privkey):
    
    @classmethod
    def generate_random(self,entropy = 128,  passphrase="", testnet = False):
        mnemonic = Mnemonic.generate_random(entropy, passphrase)
        print(f"Copy these words for future recovery:\n{mnemonic.words}")
        print(int.from_bytes(mnemonic.seed,"big"))
        return self.from_bip39_seed(int.from_bytes(mnemonic.seed,"big"), testnet = testnet)
        
    @classmethod
    def recover_from_words(self,mnemonic_list = None, entropy = 128,  passphrase="", testnet = False):
        if isinstance(mnemonic_list,str):
            mnemonic_list = mnemonic_list.split()
        mnemonic = Mnemonic.recover_from_words(mnemonic_list, entropy ,  passphrase)
        print(int.from_bytes(mnemonic.seed,"big"))
        return self.from_bip39_seed(int.from_bytes(mnemonic.seed,"big"), testnet = testnet)
    
        

class Account():

    
    def __init__(self, _privkey,addr_type = "P2PKH",testnet=False):
        """
        Initialize the account with a private key in Integer form.
        addr_type = String. Possible values: "P2PKH","P2WPKH","P2SH_P2WPKH"
        testnet: Boolean. If Testnet network is desired, simply specify this value True.
        Otherwise, simply ommit it.
        
        """
        self.privkey = PrivateKey(_privkey)
        self.addr_type = addr_type.lower()
        self.testnet = testnet
        self.redeem_script_segwit = p2wpkh_script(self.privkey.point.hash160())
        serialized_redeem = self.redeem_script_segwit.raw_serialize()
        
        if self.addr_type == "p2pkh":
            self.address = self.privkey.point.address(testnet = testnet)
        elif self.addr_type == "p2wpkh":
            if self.testnet:
                self.address = segwit_addr.encode("tb",0,self.privkey.point.hash160())
            else:
                self.address = segwit_addr.encode("bc",0,self.privkey.point.hash160())
        elif self.addr_type == "p2sh_p2wpkh":
            self.address = h160_to_p2sh_address(hash160(serialized_redeem), testnet=testnet)
        else:
            raise Exception("Addres type not supported. Must be p2pkh, p2wpkh, or p2sh_p2wpkh")
        
        
        
    def __repr__(self):
        return f"Private Key Hex: {self.privkey.hex()}"
        
    
    @classmethod
    def from_phrase(cls,phrase, endian="big",addr_type = "P2PKH",testnet=False):
        """
        phrase must be in bytes.
        endian can be either "big" or "little". Change later to boolean "bignendian"
        Returns an account using the phrase chosen which is converted to an Integer
        """
        if endian not in ["big","little"]:
            raise Exception( f'endian can be either "big" or "little" not "{endian}"')
            
        if isinstance(phrase, str):
            phrase = phrase.encode('utf-8')
            
        if isinstance(phrase, bytes):
            return cls(int.from_bytes(phrase,endian),addr_type,testnet)
        
        else:
            raise Exception( f"The phrase must be a string or bytes, not {type(phrase)}" )


class MultSigAccount():
    
    def __init__(self,m, n, _privkey, public_key_list, addr_type="p2sh", testnet = False, segwit=True):
        """
        Initialize the account with a private key in Integer form.
        m: the minumin amount of signatures required to spend the money.
        n: total amount of signatures that can be used to sign transactions.
        Note: Therefore:
        a- m has to be less or equal to n.
        b- n has to be equal to the length of the array _privkeys
        Also:
        c- n could be 20 or less, but to keep simplicity in the code, n can only be 16 or less.
        private_key must be an int.
        addr_type = String. Possible values: "P2SH","P2WSH","P2SH_P2WSH". NOT case sensitive.
        Public keys must be in bytes
        """
        if n != len(public_key_list):
            raise Exception("n must be equal to the amount of public keys")
        if m < 1 or m > 16 or n < 1 or n > 16:
            raise Exception("m and n must be between 1 and 16")
        if m > n:
            raise Exception("m must be always less or equal than n")
            
        index = -1
        pubkey = PrivateKey(_privkey).point.sec()
        for i,public_key in enumerate(public_key_list):
            if public_key == pubkey:
                index = i
        if index < 0: raise Exception ("Private key must correspond to one of the public keys.")
    
        
        self.privkey = PrivateKey(_privkey)
        self.public_keys = public_key_list
        self.m = m
        self.n = n
        self.testnet = testnet
        self.address = h160_to_p2sh_address(hash160(serialized_redeem), testnet=self.testnet)
        self.addr_type = addr_type.lower()
        self.privkey_index = index
        self.redeem_script = Script([m+80, *self.public_keys, n + 80, 174])
        serialized_redeem = self.redeem_script.raw_serialize()
      
        if self.addr_type == "p2sh":
            self.address = h160_to_p2sh_address(hash160(serialized_redeem), testnet=self.testnet)
        elif self.addr_type == "p2wsh":
            if self.testnet:
                self.address = segwit_addr.encode("tb",0,hashlib.sha256(serialized_redeem).digest())
            else:
                self.address = segwit_addr.encode("bc",0,hashlib.sha256(serialized_redeem).digest())
        elif self.addr_type == "p2sh_p2wsh":
            address_script = p2wsh_script(hashlib.sha256(serialized_redeem).digest())
            serialized_addr_script = address_script.raw_serialize()
            self.address = h160_to_p2sh_address(hash160(serialized_addr_script), testnet=testnet)
        else:
            raise Exception("Addres type not supported. Must be p2sh, p2wsh, or p2sh_p2wsh")
        
        
    def __repr__(self):
        return f"Private Key Hex: {self.privkey.hex()}"
        
    
    @classmethod
    def from_phrases(cls, m , n , phrases, testnet = False):
        """
        phrase: must be a list of tuples of (bytes, endian) or (string, endian). i.e:
            [(b"my secret","little"),("my other secret","big")]
            
        endian: can be either "big" or "little"
        Returns a multisignature account using the phrases chosen which are converted to Integers
        """
        keys = [int.from_bytes(key[0],key[1]) for key in phrases]
        return cls(m,n,keys,testnet)