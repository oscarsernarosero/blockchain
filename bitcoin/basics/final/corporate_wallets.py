from wallet import Wallet
from accounts import SHMAccount, FHMAccount, Account, MultSigAccount
from ecc import PrivateKey, S256Point
from transactions import MultiSigTransaction
from bip32 import Xtended_pubkey, Xtended_privkey
from constants import *
import datetime
from blockcypher import get_address_details, get_transaction_details
from blockcypher import pushtx
import threading
from wallet_database_sqlite3 import Sqlite3Wallet, Sqlite3Environment

"""
This code is developed entirely by Oscar Serna. This code is subject to copy rights.
This file contains the different kind of corporate wallets that exists in this porject.
"""


class CorporateSuperWallet(Wallet):
    
    def create_store_account(self, store_code):
        """
        Returns the master private key of the store with index 'store_code'.
        store_code: Integer. The code designated to the store. It is recomended that 
        this code matches that one already stablished by the company.
        """
        path = "m/44H/0H/0H/"+str(store_code)
        print(path)
        store_account = self.get_child_from_path(path)
        return store_account
    
    def request_pubkeys_daily_safe(self,store_code, m=2,n=6):
        """
        Returns the message to start requesting the public keys necessary to setup a
        daily safe.
        m: minumum signatures to validate transaction. Don't modify this if not necessary.
        n: number of signatures than can sign the transaction.
        store_code: Integer. The code designated to the store. It is recomended that 
        this code matches that already stablished by the company.
        """
        #save in the database the unique_id, public keys, m, n, and the store_code.
        return 
    
    def create_daily_safe_wallet(self, public_key_list, m=2, n=6,addr_type="p2wsh",
                                 testnet=False, segwit=True):
        """
        This is a watch-only wallet by definition. CHANGE THIS TO BE ABLE TO SIGN TX!
        Returns a Single-Herarchical multisignature master wallet based on the public keys 
        and the master_pubkey.
        public_key_list: the list of public keys of the keys that can sign the transaction.
        the length of the list must be 6 according to the protocol. However, a different 
        length can be stablished.
        m: minumum signatures to validate transaction. Don't modify this if not necessary.
        n: number of signatures than can sign the transaction. Must match with 
        public_key_list's length-1.
        """
        
        path = "m/44H/0H/1H"
        daily_safes_acc = self.get_child_from_path(path)
        print(daily_safes_acc)
        shm_account = SHMAccount(m,n, str(daily_safes_acc.xtended_public_key), public_key_list, _privkey=None,
                                 addr_type=addr_type,testnet=testnet, segwit=segwit)
        return shm_account
    
    def create_weekly_safe_wallet(self,master_pubkey, public_key_list, m=2, n=5,addr_type="p2wsh",
                                 testnet=False, segwit=True):
        """
        This is a watch-only wallet by definition. CHANGE THIS TO BE ABLE TO SIGN TX!
        Returns a Single-Herarchical multisignature master wallet based on the public keys 
        and the master_pubkey.
        public_key_list: the list of public keys of the keys that can sign the transaction.
        the length of the list must be 6 according to the protocol. However, a different 
        length can be stablished.
        m: minumum signatures to validate transaction. Don't modify this if not necessary.
        n: number of signatures than can sign the transaction. Must match with 
        public_key_list's length-1.
        """
        path = "m/44H/0H/2H"
        weekly_safes_acc = self.get_child_from_path(path)
        shm_account = SHMAccount(m,n, str(weekly_safes_acc.xtended_public_key), public_key_list, _privkey=None,
                                 addr_type=addr_type,testnet=testnet, segwit=segwit)
        return shm_account
    
    def create_corporate_safe(self, index):
        return 
    
    def get_store_deposit_account(self, store_index):
        return
    
    def get_year_xpub(self):
        path = "m/44H/0H/3H"
        year_account = self.get_child_from_path(path)
        return year_account.xtended_public_key
    
    def accept_corporate_safe_invite(self,invite, name):
        """
        accepts the invitation from a SuperCorporateWallet to participate in a daily-safe wallet.
        The acceptance must be through a private key that matches one of the public keys that are
        part of the SHM wallet passed in the invite.
        invite: SHMAccount object. The wallet that we are going to be part of.
        """
        path = "m/44H/0H/3H"
        year_safe_acc = self.get_child_from_path(path)
        print(f"accept_safe_wallet_invite: priv: {year_safe_acc.xtended_key}; pubkey: {{year_safe_acc.xtended_public_key}}")

        master_pubkey_list = invite["master_pubkey_list"]
        m = invite["m"]
        n = invite["n"]
        addr_type = invite["addr_type"]
        segwit = invite["segwit"]
        testnet = invite["testnet"]
   
            
        safe_wallet = HDMWallet( name, master_pubkey_list, year_safe_acc,m, n, addr_type, testnet,segwit)
        
        return safe_wallet
    
    
    
class StoreWallet(Wallet):
    
    def __init__(self, xpriv):
        if not isinstance(xpriv, Xtended_privkey): xpriv = Xtended_privkey.parse( xpriv )
            
        super().__init__(depth=xpriv.depth, fingerprint=xpriv.fingerprint, index=xpriv.index, 
                         chain_code=xpriv.chain_code,private_key=xpriv.private_key, testnet=xpriv.testnet)
        
    def create_receiving_address(self,index, addr_type = "p2pkh"):
        if addr_type.lower()   ==   "p2pkh":     _type  = P2PKH
        elif addr_type.lower() ==  "p2wpkh":     _type  = P2WPKH
        elif addr_type.lower() ==    "p2sh":     _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wpkh": _type  = P2SH_P2WPKH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
        receiving_path = "m/"
        #i = self.get_i(receiving_path, index)
        i = index
        path = receiving_path + str(i)
        print(f"Deposit address's Path: {path}")
        receiving_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(receiving_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.start_conn()
        self.db.new_address(account.address,receiving_path,i,FALSE, _type, self.get_xtended_key())
        self.close_conn()
        return account
        
        
        
class ManagerWallet(Wallet):
    
    def get_daily_safe_pubkey(self):
        path = "m/44H/0H/1H"
        daily_safes_acc = self.get_child_from_path(path)
        return daily_safes_acc.private_key_obj.point.sec()
    
    def accept_invite(self,invite, name):
        """
        accepts the invitation from a SuperCorporateWallet to participate in a daily-safe wallet.
        The acceptance must be through a private key that matches one of the public keys that are
        part of the SHM wallet passed in the invite.
        invite: SHMAccount object. The wallet that we are going to be part of.
        """
        path = "m/44H/0H/1H"
        daily_safes_acc = self.get_child_from_path(path)
        print(daily_safes_acc.private_key)
        
        public_key_list = invite["public_key_list"]
        master_pubkey = invite["master_pubkey"]
        m = invite["m"]
        n = invite["n"]
        addr_type = invite["addr_type"]
        segwit = invite["segwit"]
        testnet = invite["testnet"]
        
        safe_wallet = SHDSafeWallet.from_privkey_masterpubkey( name, public_key_list, master_pubkey, 
                                                              daily_safes_acc.private_key,m, n, addr_type, testnet,
                                                              segwit)
     
        return safe_wallet
        



class SHDSafeWallet(Wallet):
    """
    SafeWallet is a Multisignature SHD wallet.
    SHDM Single Herarchical Deterministic Multi-Signature Wallet
    """
    def __init__(self, name, public_key_list, m=2, n=6,addr_type="p2wsh",_privkey=None, master_pubkey=None, 
                 master_privkey=None, testnet=False, segwit=True, parent_name=None, safe_index=-1):
        """
        public_key_list: List of public keys. Must be in bytes.
        m: integer
        n: integer
        _privkey: PrivateKey object. If you provide a Private key, don't provide a master_privkey.
        master_pubkey: Xtended_pubkey object. If you provide a master_privkey, it is not necessary to
        provide a master_pubkey.
        master_privkey: Xtended_privkey object. If you provide a master_privkey, don't provide a _privkey.
        testnet: Boolean.
        segwit: Boolean.
        child_wallet: Boolean.
        """
        
        if m < 1 or m > 16 or n < 1 or n > 16: raise Exception("m and n must be between 1 and 16")
        if m > n: raise Exception("m must be always less or equal than n")   
        if len(public_key_list) != (n-1):
            msg = "n and the amount of public keys don't match. The amount of public keys must always be n-1."
            raise Exception(msg)
        
        self.index = None
        #getting the index of the private key in the list of public keys
        if _privkey is not None and master_privkey is None and master_pubkey is not None:
            self.wallet_type = "simple"
            self.master_privkey = None
            self.privkey = _privkey
            self.pubkey = PrivateKey(int.from_bytes(self.privkey,"big")).point.sec()
            for i,public_key in enumerate(public_key_list):
                if public_key == self.pubkey:
                    self.index = i
            if self.index is None: raise Exception ("Private key must be able to generate one of the public keys.")
            self.master_pubkey = master_pubkey
        
        elif _privkey is None and master_privkey is not None:
            self.privkey = _privkey
            self.wallet_type = "main"
            self.master_privkey = master_privkey
            self.master_pubkey = self.master_privkey.xtended_public_key
            
        elif _privkey is not None and master_privkey is not None:
            msg1 = "Provide either a Private key or a master_privkey, not both. Provide a _privkey if you are not "
            msg2 = "the main creator of the wallet or if you received this wallet as an invitation. Provide a "
            msg3 = "master_privkey if you have the public keys of the cosigners and you are in charge of sharing "
            msg4 = "this wallet with the cosigners."
            raise Exception (msg1+msg2+msg3+msg4)
            
        elif _privkey is None and master_privkey is None and master_pubkey is not None: 
            self.wallet_type = "watch-only"
            self.privkey = _privkey
            self.master_privkey = None
            self.master_pubkey = master_pubkey
        else:
            raise Exception ("You can only skip providing a master public key when you provide a master private key.")
        
        self.public_key_list = public_key_list
        self.m = m
        self.n = n
        self.addr_type = addr_type
        self.testnet = testnet
        self.segwit =segwit
        self.name = name
        self.parent_name = parent_name
        self.safe_index = safe_index
        
        #save the new wallet in the database
        #but first, lets convert the public keys to bytes to avoid problems in the database
        int_pubkeys = [int.from_bytes(x,"big") for x in self.public_key_list]
        if self.privkey is not None: int_privkey = int.from_bytes(self.privkey,"big")
        else: int_privkey = None
        if self.master_privkey is None: xpriv = None
        else: xpriv = str(self.master_privkey.xtended_key)
        
        self.start_conn()
        self.db.new_SHDSafeWallet(self.name, str(int_pubkeys), self.m, self.n, str(int_privkey),
                                  xpriv, str(self.master_pubkey.get_xtended_key()),
                                  self.addr_type, int(self.testnet), int(self.segwit), self.parent_name, 
                                  self.safe_index)
        print(f"self: {self}")
        self.close_conn()
        
    def __repr__(cls):
        return f"SHDSafeWallet xpub:{cls.master_pubkey}, pubkeys: {cls.public_key_list}"
        
    @classmethod    
    def from_privkey_masterpubkey(cls, name, public_key_list, master_pubkey, _privkey, m=2, n=6,addr_type="p2wsh", 
                                   testnet=False, segwit=True,parent_name=None,index=-1):
        """
        simple
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n,addr_type=addr_type,_privkey=_privkey, 
                   master_pubkey=master_pubkey,testnet=testnet, segwit=segwit,parent_name=parent_name, 
                   safe_index=index)
    
    @classmethod    
    def from_master_privkey(cls, name, public_key_list, master_privkey, m=2, n=6,addr_type="p2wsh",
                            testnet=False, segwit=True,  parent_name=None,index=-1):
        """
        main
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n, addr_type=addr_type, master_privkey=master_privkey, 
                   testnet=testnet, segwit=segwit,parent_name=parent_name, safe_index=index)
    
    @classmethod    
    def watch_only(cls, name, public_key_list,master_pubkey,m=2,n=6,addr_type="p2wsh",testnet=False, segwit=True, 
                    parent_name=None, index=-1):
        """
        watch-only
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n, addr_type=addr_type, master_pubkey=master_pubkey,
                   testnet=testnet, segwit=segwit, parent_name=parent_name, safe_index=index)
    
    @classmethod   
    def from_database(self, name):
        self.start_conn(self)
        w = self.db.recover_SHDSafeWallet(name)
        try: w = w[0]
        except: 
            print(f"wallet with name {name} not found ")
            return False
        self.close_conn(self)
        print(w)
        
        
        pubkeys = w[1][1:-1].split(", ")
        public_key_list = [int(x).to_bytes(33,"big") for x in pubkeys]
        print(public_key_list)
        if w[4] == "None": privkey = None
        else: privkey = int(w[4]).to_bytes(32,"big")
        if w[6] == "None": master_pubkey=None 
        else: master_pubkey = Xtended_pubkey.parse(w[6])
        if w[5] == "None": master_privkey = None
        else: master_privkey = Xtended_privkey.parse(w[5])
        if w[10] == "None": parent_name = None
        else: parent_name = w[10]
        
        return self(name, public_key_list, w[2],w[3],w[7],privkey,master_pubkey,master_privkey,
                    w[8],w[9],parent_name,w[11])
    
    def get_i(self,wallet_name, account_path, index):
        
        self.start_conn()

        last_index = self.db.get_max_index( account_path, wallet_name)

        if last_index is None: i = 0
        else: i = last_index + 1
        
        self.close_conn()
        return i
        
    def get_child_wallet(self, index, path):
        """
        This is the wallet for specific daily or weekly safes. Therefore, the index must comply with the format YYMMDD
        for daily safes, and YYWW for weekly safes.
        index: Integer.
        """
        #data validation
        if self.safe_index > -1: raise Exception ("Only master wallets can create child wallets.")  
        if index < 2000 or index > 999999 or (index > 9999 and index < 200101):
            raise Exception ("Bad index for daily or weekly safe. Follow YYMMDD for daily or YYWW for weekly.")
        
        full_path = path + str(index)
        #wallet creation depending on the type of wallet
        if self.wallet_type == "main":
            child_xtended_privkey = self.master_privkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.from_master_privkey( str(index)+"_"+self.name,self.public_key_list, 
                                                             child_xtended_privkey, 
                                                             self.m,self.n,self.addr_type,self.testnet, self.segwit,
                                                            self.name, index)
        elif self.wallet_type == "simple":
            child_xtended_pubkey = self.master_pubkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.from_privkey_masterpubkey(str(index)+"_"+self.name,self.public_key_list, 
                                                                   child_xtended_pubkey,
                                                                   self.privkey, self.m, self.n,self.addr_type, 
                                                                   self.testnet, self.segwit,self.name, index)
        elif self.wallet_type == "watch-only":
            child_xtended_pubkey = self.master_pubkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.watch_only(str(index)+"_"+self.name,self.public_key_list,child_xtended_pubkey,
                                                    self.m,self.n,
                                                    self.addr_type,self.testnet, self.segwit,self.name, index)
        
        return child_wallet
    
    def get_daily_safe_wallet(self, index=None):
        """
        Returns a daily_safe wallet based on the index.
        If today's wallet is desired, don't pass any argument or set index to None.
        """
        if self.safe_index >= 0: raise Exception ("Only master wallets can create safe wallets.")
        path = "m/"
        if index is None:
            today = datetime.datetime.now()
            index_string = str(today.year)[2:]+'{:02d}'.format(today.month)+'{:02d}'.format(today.day)
            index = int(index_string)
            
        safe_wallet = self.get_child_wallet(index, path)
        
        return safe_wallet
    
    
    def get_unused_addresses_list(self, change_addresses=False):
        
        self.start_conn()
        unused_addresses = self.db.get_unused_safe_addresses(name = self.name)
        self.close_conn()
        print(f"unused_addresses: {unused_addresses}")
        
        if    change_addresses: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==1]
        else: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==0]
        
        return unused_addresses_filtered
                               
                               
    def create_receiving_address(self, addr_type = "p2wsh",index=0):
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        if addr_type.lower() ==    "p2sh":       _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
        receiving_path = "m/0/"
        #i = self.get_i(self.name,receiving_path, index)
        i = index
        path = receiving_path + str(i)
        print(f"Deposit address's Path: {path}")
        
        if self.privkey is not None and self.master_privkey is None: 
            
            privkey = PrivateKey(int.from_bytes(self.privkey,"big"))
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  _privkey=privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        elif self.privkey is None and self.master_privkey is not None:
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  master_privkey=self.master_privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        else: privkey = None
        
        
        
        address = account.get_deposit_address(i)
        self.start_conn()
        self.db.new_address(address,receiving_path,i,FALSE, _type, self.name, self.safe_index)
        self.close_conn()
        return address

    
    def create_change_address(self, addr_type = "p2wsh", index=None):
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        receiving_path = "m/1/"
        
        i = self.get_i(self.name,receiving_path, index)
        path = receiving_path + str(i)
        print(f"Change address's Path: {path}")
        
        if self.privkey is not None and self.master_privkey is None: 
            
            privkey = PrivateKey(int.from_bytes(self.privkey,"big"))
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  _privkey=privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        elif self.privkey is None and self.master_privkey is not None:
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  master_privkey=self.master_privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        else: privkey = None
        
        #address = account.get_change_address(index=i)
        change_account = account.get_change_account(index=i)
        self.start_conn()
        self.db.new_address(change_account.address,receiving_path,i,TRUE, P2WSH, self.name, self.safe_index)
        self.close_conn()
        return change_account
    
    def get_a_change_address(self):
        """
        Returns an Account object containing a change address. It returns an existing unused change
        address account, or creates a new one if necessary.
        """
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        self.start_conn()
        unused_addresses = self.get_unused_addresses_list(change_addresses=True)
        self.close_conn()
        
        if len(unused_addresses)>0: return self.create_change_address(index=unused_addresses[0][3])
        else: return self.create_change_address()
        
    def share(self):
        if self.safe_index >= 0: raise Exception ("Only master wallets can be shared.")
        return {"public_key_list":self.public_key_list,"m":self.m, "n":self.n, "addr_type":self.addr_type,
                "master_pubkey":self.master_pubkey,"testnet":self.testnet, "segwit":self.segwit }
    

    def get_utxos(self):
        """
        This method is an overwritten version of the original Wallet-class version.
        """
        self.start_conn()
        ################################ FOR DEVOLPMENT PORPUSES ONLY ###############################
        ############### CHANGE BACK TO ORIGINAL STATE ONCE DONE WITH TESTS ##########################
        #coins = self.db.look_for_coins(self.name) #ORIGINAL LINE!
        coins = self.db.look_for_coins("200827_test1_master_wallet") #TEST LINE
        ############################################################################################
        self.close_conn()
        return coins
    
    def update_balance(self):
        """
        This method is an overwritten version of the original Wallet-class version.
        """
        self.start_conn()
        addresses = self.db.get_all_addresses(self.name)
        self.close_conn()
        
        if self.testnet: coin_symbol = "btc-testnet"
        else: coin_symbol = "btc"
            
        for address in addresses:
            "address will be a touple with data (address,)"
            print(f"consulting blockchain for address {address}")
            addr_info = get_address_details(address[0], coin_symbol = coin_symbol, unspent_only=True)
            print(f"res for {address}:\n{addr_info}")
            
            self.start_conn()
            if addr_info["unconfirmed_n_tx"] > 0:
                print("got unconfirmed transactions.")
                for utxo in addr_info["unconfirmed_txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 0):
                        print("new unconfirmed UTXO")
                        self.db.new_utxo(utxo["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],confirmed = 0)
            
            if addr_info["n_tx"] - addr_info["unconfirmed_n_tx"] > 0 :
                print("got transactions.")
                for utxo in addr_info["txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 1):
                        print("new confirmed UTXO")
                        self.db.new_utxo(addr_info["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],
                                         confirmed = 1)
      
        self.close_conn()
        return self.get_balance()
        
    def get_coins(self, to_address_amount_list, segwit=True):
        send_all = False
        
        print(f"From wallet.send(): {to_address_amount_list}")
        #calculate total amount to send from the wallet
        total_amount = 0
        for output in to_address_amount_list:
            total_amount += output[1]
            
            
        #we validate that we have funds to carry out the transaction, or if we are trying to send all the funds  
        balance = self.get_balance()
        if total_amount>balance:
            raise Exception(f"Not enough funds in wallet for this transaction.\nOnly {balance} satoshis available")
        
        elif total_amount == balance: send_all = True
            
            
        #We choose the utxos to spend for the transaction
        all_utxos = self.get_utxos()
        
        #If we are trying to send all the funds, then we choose all the utxos
        if send_all: utxos = all_utxos
        #If not, then we have to choose in an efficient manner.
        else:    
            utxos = []
            utxo_total = 0
            
            #First we check if only one utxo can carry out the whole transaction
            for utxo in all_utxos:
                if utxo[2] > total_amount*1.1:
                    utxos = [utxo]
                    break
            #if we found that none of the utxos is big enough to carry out the whole tx, we have to choose several.
            if len(utxos)==0:    
                for utxo in all_utxos:
                    utxos.append(utxo)
                    utxo_total += utxo[2]
                    if utxo_total > (total_amount*1.1) : break
        
        return utxos, send_all
    
    def build_tx(self, utxos, to_address_amount_list, segwit=True, send_all = False):
        
        account = self.get_signing_account()
        
        #if we want to send all the funds we don't need a change address.
        if send_all: change_address = None    
        else:        change_address = self.get_a_change_address()
        """    
        privkey = PrivateKey(int.from_bytes(self.privkey,"big"))
            
        account = SHMAccount(self.m, self.n, str(self.master_pubkey), self.public_key_list, privkey,
                             self.addr_type, self.testnet, self.segwit)
        """
        #We create the Multi-Signature Transaction object
        tx_response = MultiSigTransaction.create_from_wallet(utxo_list=utxos,
                                                             receivingAddress_w_amount_list =to_address_amount_list,
                                                             multi_sig_account = account,change_address = change_address,
                                                             fee=None,segwit=True,send_all=send_all)
        
        return tx_response
    
    
    def get_signing_account(self):
        
        #we take care of validating and formatting the private key
        if self.privkey is not None and self.master_privkey is None: 
            
            privkey = PrivateKey(int.from_bytes(self.privkey,"big"))
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  _privkey=privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        elif self.privkey is None and self.master_privkey is not None:
            
            account = SHMAccount(m=self.m, n=self.n, xtended_pubkey = str(self.master_pubkey), 
                                 public_key_list = self.public_key_list,  master_privkey=self.master_privkey,
                                 addr_type=self.addr_type, testnet=self.testnet, segwit=self.segwit)
            
        else: privkey = None
        #else: raise Exception("Multi signature Transaction with a master key is not developed yet.")
        
        #We create the multisignature account to sign the transaction. This only works for spending from deposit
        #account. To spend from the change account, we need to do something else.
        
        
        
        #account = shm_account.get_deposit_account()
        return account
        
        
    def broadcast_tx(self, tx,utxos):
        
        if self.testnet: symbol = "btc-testnet"
        else: symbol= "btc"

        env = Sqlite3Environment()
        BLOCKCYPHER_API_KEY = env.get_key("BLOCKCYPHER_API_KEY")[0][0]
        env.close_database()
        push = pushtx(tx_hex= tx.serialize().hex(), coin_symbol=symbol,api_key=BLOCKCYPHER_API_KEY)
        tx_id = tx.id()
        print(f"TRANSACTION ID: {tx_id}")

        #saving in db
        self.start_conn()
        self.db.new_tx(tx_id, [ (x[0],x[1]) for x in utxos] ,
                       [str(x).split(":")+[i] for i,x in enumerate(tx.tx_outs)])
        self.close_conn()
        #start new thread to check if the transaction goes through in the blockchain or not.
        #Maybe move this to the front end class to pop a warning when it doesn't go through
        mythread = threading.Thread(target=self.confirm_tx_sent,args=(tx_id,))
        mythread.start()

        return tx,push
        
        
    def send(self, to_address_amount_list, segwit=True):
        """
        to_address can be a single address or a list.
        amount can be an integer or a list of integers.
        If they are lists, they must be ordered in the same way. address 1 will e sent amount 1, 
        adrress 2 will be sent amount2.. adress n will be sent amount n.
        """
        #First let's get ready the inputs for the transaction
        utxos, send_all = self.get_coins(to_address_amount_list, segwit)
        
        #Now, let's build the transaction
        tx_response = self.build_tx(utxos,to_address_amount_list, segwit, send_all)
        
        # tx_response will be a touple of the transaction object and a boolean (tx,READY) that tells us if the  
        #transaction is ready to be broadcasted or if it needs more signatures:
        if tx_response[1]: 
            #if it is ready, we broadcast the transaction
            self.broadcast_tx(tx_response[0],utxos)
            
        return tx_response 
        
    def sign_received_tx(self, tx):
        """
        tx: Tx object. The transaction object that needs to be signed.
        """
        
        #to do: we need to get the utxo list from the database using the transaction to be able to sign
        utxos = []
        self.start_conn()
        for _in in tx.tx_ins:
            res = self.db.get_utxo_info(_in.prev_tx.hex(), _in.prev_index)
            print(res)
            utxos.append(res[0])
            
        self.close_conn()
        #We create the multisignature account to sign the transaction.
        account = self.get_signing_account()
        
        tx_response = MultiSigTransaction.sign_received_tx_with_wallet(utxos,tx,account)
        
        if tx_response[1]: self.broadcast_tx(tx_response[0],utxos)
            
        return tx_response
            
        
        
class HDMWallet(Wallet):
    """
    HDMWallet is a Herarchical Deterministic Multi-signature Wallet (HDM-Wallet).
    It is a Fully HD MS wallet which means that all its participants share the extended public key, \
    and all its child addresses are the result of the multi-signature address created by the \
    publick keys derived from the same path of all the master public keys.
    """
    def __init__(self, name, master_pubkey_list,master_privkey, m=2, n=6,addr_type="p2wsh",  
                  testnet=False, segwit=True, parent_name=None, safe_index=-1):
        """
        public_key_list: List of public keys. Must be in bytes.
        m: integer
        n: integer
        _privkey: PrivateKey object. If you provide a Private key, don't provide a master_privkey.
        master_pubkey: Xtended_pubkey object. If you provide a master_privkey, it is not necessary to
        provide a master_pubkey.
        master_privkey: Xtended_privkey object. If you provide a master_privkey, don't provide a _privkey.
        testnet: Boolean.
        segwit: Boolean.
        child_wallet: Boolean.
        """
        
        if m < 1 or m > 16 or n < 1 or n > 16:
            raise Exception("m and n must be between 1 and 16")
        if m > n:
            raise Exception("m must be always less or equal than n")
        if len(master_pubkey_list) != (n):
            raise Exception("n and the amount of public keys don't match. The amount of public keys must always be n-1.")
        
        
        index = -1
        #getting the index of the private key in the list of public keys
        self.master_privkey = master_privkey
        pubkey = str(self.master_privkey.xtended_public_key)
        for i,public_key in enumerate(master_pubkey_list):
            if str(public_key) == pubkey:
                index = i
        if index < 0: raise Exception ("Private key must correspond to one of the public keys.")

        self.xtended_pubkey_list = master_pubkey_list
        self.name = name
        self.m = m
        self.n = n
        self.testnet = testnet
        self.addr_type = addr_type.lower()
        self.privkey_index = index
        self.parent_name = parent_name
        self.safe_index = safe_index
        self.segwit = segwit
        
        #save the new wallet in the database
        #but first, lets convert the public keys into strings to avoid problems in the database
        str_pubkeys = [str(x.get_xtended_key()) for x in self.xtended_pubkey_list]
        xpriv = str(self.master_privkey.xtended_key)
        
        self.start_conn()
        self.db.new_HDMWallet(self.name, str_pubkeys, self.m, self.n,xpriv, self.addr_type, int(self.testnet), 
                                  int(self.segwit), self.parent_name, self.safe_index)
        self.close_conn()
        
    def __repr__(cls):
        return f"FHDSafeWallet :{cls.m}-of-{cls.n} pubkeys: {cls.xtended_pubkey_list}"
    
    @classmethod   
    def from_database(self, name):
        self.start_conn(self)
        w = self.db.recover_HDMWallet(name)
        try: w = w[0]
        except: 
            print(f"wallet with name {name} not found ")
            return False
        self.close_conn(self)
        print(w)
        pubkeys = w[1][1:-1].split(", ")
        master_pubkey_list = [Xtended_pubkey.parse(x) for x in pubkeys]
        print(f"parsed master public keys: {public_key_list}")
        master_privkey = Xtended_privkey.parse(w[4])
        if w[8] == "None": parent_name = None
        else: parent_name = w[8]
        
        return self(name, master_pubkey_list,master_privkey, w[2],w[3],
                    w[5],w[6],w[7],parent_name,w[9])
    
    def get_i(self,wallet_name, account_path, index):
        
        self.start_conn()

        last_index = self.db.get_max_index( account_path, wallet_name)

        if last_index is None: i = 0
        else: i = last_index + 1
        
        self.close_conn()
        return i
    
    def get_child_wallet(self, index, path):
        """
        This is the wallet for specific years. Therefore, the index must comply with the format YY.
        index: Integer.
        """
        #data validation
        if self.safe_index > -1: raise Exception ("Only master wallets can create child wallets.")  
        if index < 20 or index > 99:
            raise Exception ("Bad index for year wallet. Follow YY format.")
        
        full_path = path + str(index)
        child_xtended_privkey = self.master_privkey.get_child_from_path(full_path)
        
        child_pubkey_list = [x.get_child_from_path(full_path) for x in self.xtended_pubkey_list]
            
        child_wallet = HDMWallet( "20"+str(index)+"_"+self.name,  child_pubkey_list,
                                 child_xtended_privkey,  self.m,  self.n,  self.addr_type,
                                 self.testnet, self.segwit,  self.name, index)
        
        return child_wallet
    
    def get_year_wallet(self, index=None):
        """
        Returns a year_safe wallet based on the index.
        If this-years's wallet is desired, don't pass any argument or set index to None.
        """
        if self.safe_index >= 0: raise Exception ("Only master wallets can create safe wallets.")
        path = "m/"
        if index is None:
            today = datetime.datetime.now()
            index_string = str(today.year)[2:]
            index = int(index_string)
            
        safe_wallet = self.get_child_wallet(index, path)
        
        return safe_wallet
    
    def get_unused_addresses_list(self, change_addresses=False):
        
        self.start_conn()
        unused_addresses = self.db.get_unused_safe_addresses(name = self.name)
        self.close_conn()
        print(f"unused_addresses: {unused_addresses}")
        
        if    change_addresses: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==1]
        else: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==0]
        
        return unused_addresses_filtered
                               
                               
    def create_receiving_address(self, addr_type = "p2wsh",index=None):
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        if addr_type.lower() ==    "p2sh":       _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
        receiving_path = "m/0/"
        i = self.get_i(self.name,receiving_path, index)
        path = receiving_path + str(i)
        print(f"Deposit address's Path: {path}")
        
        account = FHMAccount(self.m, self.xtended_pubkey_list, self.master_privkey, self.addr_type,
                             self.testnet, self.segwit)
        
        
        
        address = account.get_deposit_address(i)
        self.start_conn()
        self.db.new_address(address,receiving_path,i,FALSE, _type, self.name, self.safe_index)
        self.close_conn()
        return address

    
    def create_change_address(self, addr_type = "p2wsh", index=None):
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        receiving_path = "m/1/"
        
        i = self.get_i(self.name,receiving_path, index)
        path = receiving_path + str(i)
        print(f"Change address's Path: {path}")
        
        account = FHMAccount(self.m, self.xtended_pubkey_list, self.master_privkey, self.addr_type,
                             self.testnet, self.segwit)
        
        change_account = account.get_change_account(index=i)
        self.start_conn()
        self.db.new_address(change_account.address,receiving_path,i,TRUE, P2WSH, self.name, self.safe_index)
        self.close_conn()
        return change_account
    
    def get_a_change_address(self):
        """
        Returns an Account object containing a change address. It returns an existing unused change
        address account, or creates a new one if necessary.
        """
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        self.start_conn()
        unused_addresses = self.get_unused_addresses_list(change_addresses=True)
        self.close_conn()
        
        if len(unused_addresses)>0: return self.create_change_address(index=unused_addresses[0][3])
        else: return self.create_change_address()
        
    def share(self):
        if self.safe_index >= 0: raise Exception ("Only master wallets can be shared.")
        return {"master_pubkey_list":self.xtended_pubkey_list,"m":self.m, "n":self.n, "addr_type":self.addr_type,
                "testnet":self.testnet, "segwit":self.segwit }
    

    def get_utxos(self):
        """
        This method is an overwritten version of the original Wallet-class version.
        """
        self.start_conn()
        ################################ FOR DEVOLPMENT PORPUSES ONLY ###############################
        ############### CHANGE BACK TO ORIGINAL STATE ONCE DONE WITH TESTS ##########################
        #coins = self.db.look_for_coins(self.name) #ORIGINAL LINE!
        coins = self.db.look_for_coins("2020_Corporate_wallet_master") #TEST LINE
        ############################################################################################
        self.close_conn()
        return coins
    
    def update_balance(self):
        """
        This method is an overwritten version of the original Wallet-class version.
        """
        self.start_conn()
        addresses = self.db.get_all_addresses(self.name)
        self.close_conn()
        
        if self.testnet: coin_symbol = "btc-testnet"
        else: coin_symbol = "btc"
            
        for address in addresses:
            "address will be a touple with data (address,)"
            print(f"consulting blockchain for address {address}")
            addr_info = get_address_details(address[0], coin_symbol = coin_symbol, unspent_only=True)
            print(f"res for {address}:\n{addr_info}")
            
            self.start_conn()
            if addr_info["unconfirmed_n_tx"] > 0:
                print("got unconfirmed transactions.")
                for utxo in addr_info["unconfirmed_txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 0):
                        print("new unconfirmed UTXO")
                        self.db.new_utxo(utxo["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],confirmed = 0)
            
            if addr_info["n_tx"] - addr_info["unconfirmed_n_tx"] > 0 :
                print("got transactions.")
                for utxo in addr_info["txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 1):
                        print("new confirmed UTXO")
                        self.db.new_utxo(addr_info["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],
                                         confirmed = 1)
      
        self.close_conn()
        return self.get_balance()
        
    def get_coins(self, to_address_amount_list, segwit=True):
        send_all = False
        
        print(f"From wallet.send(): {to_address_amount_list}")
        #calculate total amount to send from the wallet
        total_amount = 0
        for output in to_address_amount_list:
            total_amount += output[1]
            
            
        #we validate that we have funds to carry out the transaction, or if we are trying to send all the funds  
        balance = self.get_balance()
        if total_amount>balance:
            raise Exception(f"Not enough funds in wallet for this transaction.\nOnly {balance} satoshis available")
        
        elif total_amount == balance: send_all = True
            
            
        #We choose the utxos to spend for the transaction
        all_utxos = self.get_utxos()
        
        #If we are trying to send all the funds, then we choose all the utxos
        if send_all: utxos = all_utxos
        #If not, then we have to choose in an efficient manner.
        else:    
            utxos = []
            utxo_total = 0
            
            #First we check if only one utxo can carry out the whole transaction
            for utxo in all_utxos:
                if utxo[2] > total_amount*1.1:
                    utxos = [utxo]
                    break
            #if we found that none of the utxos is big enough to carry out the whole tx, we have to choose several.
            if len(utxos)==0:    
                for utxo in all_utxos:
                    utxos.append(utxo)
                    utxo_total += utxo[2]
                    if utxo_total > (total_amount*1.1) : break
        
        return utxos, send_all
    
    def build_tx(self, utxos, to_address_amount_list, segwit=True, send_all = False):
        
        account = self.get_signing_account()
        
        #if we want to send all the funds we don't need a change address.
        if send_all: change_address = None    
        else:        change_address = self.get_a_change_address()
        
        #We create the Multi-Signature Transaction object
        tx_response = MultiSigTransaction.create_from_wallet(utxo_list=utxos,
                                                             receivingAddress_w_amount_list =to_address_amount_list,
                                                             multi_sig_account = account,change_address = change_address,
                                                             fee=None,segwit=True,send_all=send_all)
        
        return tx_response
    
    
    def get_signing_account(self):
        
        #We create the multisignature account to sign the transaction. 
        account = FHMAccount(self.m, self.xtended_pubkey_list, self.master_privkey, self.addr_type,
                             self.testnet, self.segwit)
        
        return account
        
        
    def broadcast_tx(self, tx,utxos):
        
        if self.testnet: symbol = "btc-testnet"
        else: symbol= "btc"

        env = Sqlite3Environment()
        BLOCKCYPHER_API_KEY = env.get_key("BLOCKCYPHER_API_KEY")[0][0]
        env.close_database()
        push = pushtx(tx_hex= tx.serialize().hex(), coin_symbol=symbol,api_key=BLOCKCYPHER_API_KEY)
        tx_id = tx.id()
        print(f"TRANSACTION ID: {tx_id}")

        #saving in db
        self.start_conn()
        self.db.new_tx(tx_id, [ (x[0],x[1]) for x in utxos] ,
                       [str(x).split(":")+[i] for i,x in enumerate(tx.tx_outs)])
        self.close_conn()
        #start new thread to check if the transaction goes through in the blockchain or not.
        #Maybe move this to the front end class to pop a warning when it doesn't go through
        mythread = threading.Thread(target=self.confirm_tx_sent,args=(tx_id,))
        mythread.start()

        return tx,push
        
        
    def send(self, to_address_amount_list, segwit=True):
        """
        to_address can be a single address or a list.
        amount can be an integer or a list of integers.
        If they are lists, they must be ordered in the same way. address 1 will e sent amount 1, 
        adrress 2 will be sent amount2.. adress n will be sent amount n.
        """
        #First let's get ready the inputs for the transaction
        utxos, send_all = self.get_coins(to_address_amount_list, segwit)
        
        #Now, let's build the transaction
        tx_response = self.build_tx(utxos,to_address_amount_list, segwit, send_all)
        
        # tx_response will be a touple of the transaction object and a boolean (tx,READY) that tells us if the  
        #transaction is ready to be broadcasted or if it needs more signatures:
        if tx_response[1]: 
            #if it is ready, we broadcast the transaction
            self.broadcast_tx(tx_response[0],utxos)
            
        return tx_response 
        
    def sign_received_tx(self, tx):
        """
        tx: Tx object. The transaction object that needs to be signed.
        """
        
        #to do: we need to get the utxo list from the database using the transaction to be able to sign
        utxos = []
        self.start_conn()
        for _in in tx.tx_ins:
            res = self.db.get_utxo_info(_in.prev_tx.hex(), _in.prev_index)
            print(res)
            utxos.append(res[0])
            
        self.close_conn()
        #We create the multisignature account to sign the transaction.
        account = self.get_signing_account()
        
        tx_response = MultiSigTransaction.sign_received_tx_with_wallet(utxos,tx,account)
        
        if tx_response[1]: self.broadcast_tx(tx_response[0],utxos)
            
        return tx_response
            