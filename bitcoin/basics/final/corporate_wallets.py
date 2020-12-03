from wallet import Wallet
from accounts import SHMAccount, FHMAccount, Account, MultSigAccount
from ecc import PrivateKey, S256Point
from tx import Tx, TxIn, TxOut
from transactions import MultiSigTransaction
from bip32 import Xtended_pubkey, Xtended_privkey
from constants import *
import datetime
from blockcypher import get_address_details, get_transaction_details
from blockcypher import pushtx
import threading
from wallet_database_sqlite3 import Sqlite3Wallet, Sqlite3Environment
import calendar
from io import BytesIO
from coin_selector import coin_selector

"""
This code is developed entirely by Oscar Serna. This code is subject to copy rights.
This file contains the different kind of corporate wallets that exists in this porject.
"""

class MultiSignatureWallet(Wallet):
    
    def get_all_addresses(self):
        return self.db.get_all_addresses(self.name)
    
    def get_utxos(self):
        """
        This method is an overwritten version of the original Wallet-class version.
        """
        self.start_conn()
        coins = self.db.look_for_coins(self.name) 
        self.close_conn()
        return coins
    
    
    def get_a_change_address(self):
        """
        Returns an Account object containing a change address. It returns an existing unused change
        address account, or creates a new one if necessary.
        """
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        self.start_conn()
        unused_addresses = self.get_unused_addresses_list(change_addresses=True)
        self.close_conn()
        
        if len(unused_addresses)>0: return self.create_change_address(index=unused_addresses[-1][-1])
        else: return self.create_change_address()
        
    
    def get_i(self,wallet_name, account_path, index=None):
        
        if index is not None:
            if index>=0: 
                print(f"reusing address with index {index}")
                return index
        
        self.start_conn()
        last_index = self.db.get_max_index( account_path, wallet_name)

        if last_index is None: i = 0
        else: i = last_index + 1
        
        self.close_conn()
        return i
    
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
        
    def build_tx(self, coins, to_address_amount_list, segwit=True):
        
        account = self.get_signing_account()
        
        #if we want to send all the funds we don't need a change address.
        if not coins["change"]: change_address = None    
        else:        change_address = self.get_a_change_address()
        #We create the Multi-Signature Transaction object
        tx_response = MultiSigTransaction.create_from_wallet(coins=coins,
                                                             receivingAddress_w_amount_list =to_address_amount_list,
                                                             multi_sig_account = account,change_account = change_address,
                                                             fee=None,segwit=True)
        
        return tx_response
    
    def send(self, to_address_amount_list, segwit=True, send_all = None, min_fee_per_byte=70):
        """
        to_address_amount_list: List of tuples [(address1,amount1),...]
        """
        #First let's get ready the inputs for the transaction
        coins = self.get_coins(to_address_amount_list, send_all=send_all,
                                         segwit=segwit,min_fee_per_byte=min_fee_per_byte)
        print(f"coins from coin-selector: {coins}")
        
        #Now, let's build the transaction
        tx_response = self.build_tx(coins,to_address_amount_list, segwit)
        self.start_conn()
        consigners_reply = {}
        [consigners_reply.update({f"{int.from_bytes(pubkey,'big')}":None}) for pubkey in self.public_key_list]
        consigners_reply.update({f'{self.master_pubkey}':None})
        if   self.wallet_type=="main"  : consigners_reply.update({f"{self.master_pubkey}":True})
        elif self.wallet_type=="simple": consigners_reply.update({f"{int.from_bytes(self.pubkey,'big')}":True})
        
        tx_id = tx_response[0].transaction.id()
        tx_hex = tx_response[0].transaction.serialize().hex()
        self.db.new_partial_tx(tx_id, [ (x[0],x[1]) for x in coins["utxos"]], 
                               [str(x).split(":")+[i] for i,x in enumerate(tx_response[0].transaction.tx_outs)], 
                               consigners_reply, tx_hex)
        
        
        # tx_response will be a touple of the transaction object and a boolean (tx,READY) that tells us if the  
        #transaction is ready to be broadcasted or if it needs more signatures:
        #utxos = coins["utxos"]
        if tx_response[1]: 
            #if it is ready, we broadcast the transaction
            self.broadcast_tx(tx_response[0],coins["utxos"])
            
        self.close_conn()  
        #share it with the other participants of the multi-signature wallet. For now:
        print(f"##### This is the partially signed tx #####:\n{tx_response[0].transaction.serialize().hex()}")
        return tx_response 
        
    def sign_received_tx(self, tx):
        """
        tx: MultiSignatureTx object. The transaction object that needs to be signed.
        """
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
        
        tx_id = tx_response[0].transaction.id()
        
        if tx_response[1]: 
            self.broadcast_tx(tx_response[0].transaction,utxos)
            #self.start_conn()
            #self.db.delete_partial_tx(tx_id)
            
        else:
            #update the cosigners_reply
            if   self.wallet_type=="main"  : pubkey = self.master_pubkey
            elif self.wallet_type=="simple": pubkey = int.from_bytes(self.pubkey,"big")
            self.start_conn()
            self.db.update_cosigners_reply(tx_id, pubkey, reply=True)
            #update the tx_ins in the partial-tx database
            new_tx_hex = tx_response[0].transaction.serialize().hex()
            self.db.update_partial_tx(tx_id, new_tx_hex)
            #share it with the other participants of the multi-signature wallet. For now:
            print(f"##### This is the partially signed tx #####:\n{tx_response[0].transaction.serialize().hex()}\ntx_in: \
            {tx_response[0].tx_ins}")
        
        self.close_conn()
        return tx_response


class CorporateSuperWallet(Wallet):
    
    def get_daily_safe_pubkey(self):
        path = "m/44H/0H/1H"
        daily_safes_acc = self.get_child_from_path(path)
        return daily_safes_acc.private_key_obj.point.sec()
    
    
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
        #print(daily_safes_acc)
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
        path = "m/44H/0H/1H"
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
        #print(daily_safes_acc.private_key)
        
        public_key_list = invite["public_key_list"]
        master_pubkey = invite["master_pubkey"]
        m = invite["m"]
        n = invite["n"]
        addr_type = invite["addr_type"]
        segwit = invite["segwit"]
        testnet = invite["testnet"]
        level1 = invite["level1pubkeys"]
        
        safe_wallet = SHDSafeWallet.from_privkey_masterpubkey( name, public_key_list, master_pubkey, 
                                                              daily_safes_acc.private_key,m, n, addr_type, testnet,
                                                              segwit,level1pubkeys = level1)
     
        return safe_wallet
        
        
        
class SHDSafeWallet(MultiSignatureWallet):
    """
    SafeWallet is a Multisignature SHD wallet.
    SHDM Single Herarchical Deterministic Multi-Signature Wallet
    """
    def __init__(self, name, public_key_list, m=2, n=6,addr_type="p2wsh",_privkey=None, master_pubkey=None, 
                 master_privkey=None, testnet=False, segwit=True, parent_name=None, safe_index=-1, level1pubkeys=None):
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
        level1pubkeys: List. List of the public keys that are going to be part of the daily safes but NOT part\
        of the weekly safes. Therefor, these public keys must be among the public_key_list as well.
        """
        if isinstance(master_pubkey, str): master_pubkey = Xtended_pubkey.parse(master_pubkey)
            
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
        
        #we check that all the level1pubkeys exist in the public_key_list
        if level1pubkeys is not None:
            all_level1_exist = True
            for level1 in level1pubkeys: 
                all_level1_exist = all_level1_exist & (level1 in public_key_list)
                if not all_level1_exist: raise Exception("level1pubkeys must be part of the public_key_list.")
            
        self.level1pubkeys = level1pubkeys
        
        #save the new wallet in the database
        #but first, lets convert the public keys to int to avoid problems in the database
        int_pubkeys = [int.from_bytes(x,"big") for x in self.public_key_list]
        if self.privkey is not None: int_privkey = int.from_bytes(self.privkey,"big")
        else: int_privkey = None
        if self.master_privkey is None: xpriv = None
        else: xpriv = str(self.master_privkey.xtended_key)
        if self.level1pubkeys is not None: int_level1 = [int.from_bytes(x,"big") for x in self.level1pubkeys]
        else: int_level1 = None
            
        
        self.start_conn()
        self.db.new_SHDSafeWallet(self.name, str(int_pubkeys), self.m, self.n, str(int_privkey),
                                  xpriv, str(self.master_pubkey.get_xtended_key()),
                                  self.addr_type, int(self.testnet), int(self.segwit), self.parent_name, 
                                  self.safe_index, str(int_level1))
        print(f"self: {self}")
        self.close_conn()
        
    def __repr__(cls):
        return f"SHDSafeWallet xpub:{cls.master_pubkey}, pubkeys: {cls.public_key_list}"
        
    @classmethod    
    def from_privkey_masterpubkey(cls, name, public_key_list, master_pubkey, _privkey, m=2, n=6,addr_type="p2wsh", 
                                   testnet=False, segwit=True,parent_name=None,index=-1,level1pubkeys=None):
        """
        simple
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n,addr_type=addr_type,_privkey=_privkey, 
                   master_pubkey=master_pubkey,testnet=testnet, segwit=segwit,parent_name=parent_name, 
                   safe_index=index,level1pubkeys=level1pubkeys)
    
    @classmethod    
    def from_master_privkey(cls, name, public_key_list, master_privkey, m=2, n=6,addr_type="p2wsh",
                            testnet=False, segwit=True,  parent_name=None,index=-1, level1pubkeys=None):
        """
        main
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n, addr_type=addr_type, master_privkey=master_privkey, 
                   testnet=testnet, segwit=segwit,parent_name=parent_name, safe_index=index, level1pubkeys=level1pubkeys)
    
    @classmethod    
    def watch_only(cls, name, public_key_list,master_pubkey,m=2,n=6,addr_type="p2wsh",testnet=False, segwit=True, 
                    parent_name=None, index=-1, level1pubkeys=None):
        """
        watch-only
        """
        return cls(name,public_key_list=public_key_list, m=m, n=n, addr_type=addr_type, master_pubkey=master_pubkey,
                   testnet=testnet, segwit=segwit, parent_name=parent_name, safe_index=index, level1pubkeys=level1pubkeys)
    
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
        if w[12] == "None": level1pubkeys = None
        else: 
            pubkeys = w[12][1:-1].split(", ")
            level1pubkeys = [int(x).to_bytes(33,"big") for x in pubkeys]
        
        
        print(f"from SHDSafeWallet: parent_name = {parent_name}")
        return self(name=name, public_key_list=public_key_list, m=w[2], n=w[3], addr_type=w[7], _privkey=privkey,
                    master_pubkey=master_pubkey, master_privkey=master_privkey,
                    testnet=w[8], segwit=w[9], parent_name=parent_name, safe_index=w[11], level1pubkeys = level1pubkeys)
    
    
        
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
        
        #let's build a human-redable prefix for the name of the child wallet, and modify the public key list 
        #in the case of the week-safe wallets
        public_key_list=[]
        if index < 9999:
            prefix = "week-"+str(index)[2:]+"-of-"+str(index)[:2]
            public_key_list = list( set(self.public_key_list) - set(self.level1pubkeys) )
            n = self.n - len(self.level1pubkeys)
        else:           
            prefix = calendar.month_abbr[int(str(index)[2:4])]+str(index)[4:]+"-of-"+str(index)[:2]
            public_key_list = self.public_key_list
            n = self.n
        print(f"prefix {prefix}")
        
        full_path = path + str(index)
        #wallet creation depending on the type of wallet
        if self.wallet_type == "main":
            child_xtended_privkey = self.master_privkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.from_master_privkey( prefix+"_"+self.name, public_key_list, 
                                                             child_xtended_privkey, 
                                                             self.m,n,self.addr_type,self.testnet, self.segwit,
                                                            self.name, index)
        elif self.wallet_type == "simple":
            child_xtended_pubkey = self.master_pubkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.from_privkey_masterpubkey(prefix+"_"+self.name,public_key_list, 
                                                                   child_xtended_pubkey,
                                                                   self.privkey, self.m, n,self.addr_type, 
                                                                   self.testnet, self.segwit,self.name, index)
        elif self.wallet_type == "watch-only":
            child_xtended_pubkey = self.master_pubkey.get_child_from_path(full_path)
            
            child_wallet = SHDSafeWallet.watch_only(prefix+"_"+self.name,public_key_list,child_xtended_pubkey,
                                                    self.m,n,
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
    
    
    def get_weekly_safe_wallet(self, index=None):
        """
        Returns a daily_safe wallet based on the index.
        If today's wallet is desired, don't pass any argument or set index to None.
        """
        if self.safe_index >= 0: raise Exception ("Only master wallets can create safe wallets.")
        path = "m/"
        if index is None:
            this_year, this_week, _weekday  =  datetime.datetime.now().isocalendar()
            index = int(  str(this_year)[2:] + f"{this_week:02d}"  )
            
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
    
    
    def share(self):
        if self.safe_index >= 0: raise Exception ("Only master wallets can be shared.")
        return {"public_key_list":self.public_key_list,"m":self.m, "n":self.n, "addr_type":self.addr_type,
                "master_pubkey":f"{self.master_pubkey}","testnet":self.testnet, "segwit":self.segwit,
                "level1pubkeys":self.level1pubkeys }
    
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
            
        return account
        
    def open_partial_tx(self, tx_id):
        """
        Opens the new partial transaction in the database, and reconstructs the MultiSigTransaction object \
        to pass it to the sign_received_tx() method.
        tx_id: str. The tx id of the new partial tx in the database.
        """
        self.start_conn()
        tx = Tx.parse(BytesIO(bytes.fromhex(self.db.get_partial_tx_hex(tx_id)[0][0])), self.testnet)
        print(f"tx {tx}")
        tx_ins = tx.tx_ins
        print(f"tx_ins {tx.tx_ins}")
        ms_tx = MultiSigTransaction(tx,None,tx_ins,None,tx.tx_outs,None,None,self.testnet,None)
        self.close_conn()
        return self.sign_received_tx(ms_tx)
        
        
class HDMWallet(MultiSignatureWallet):
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
    
    
    
    def get_child_wallet(self, index, path):
        """
        This is the wallet for specific years. Therefore, the index must comply with the format YY.
        index: Integer.
        """
        #data validation
        if self.safe_index > -1: raise Exception ("Only master wallets can create child wallets.")  
        
        #If self.index is < 0 it means it is a master wallet. Therefore, the very next child wallets must be
        #Year accounts which must follow the YY format.
        if index < 2020 or index > 2199: raise Exception ("Bad index for year wallet. Follow YYYY format.")
        
        #Accounts with index 0 and 1 are reserved for deposit and change adddresses. Therefore, the index must be
        #always greater than 1.
        #if index < 2: raise Exception ("Bad index for sub-wallet. Index must be greater than 1.")
            
        
        full_path = path + str(index)
        child_xtended_privkey = self.master_privkey.get_child_from_path(full_path)
        
        child_pubkey_list = [x.get_child_from_path(full_path) for x in self.xtended_pubkey_list]
            
        child_wallet = HDMWallet( str(index)+"_"+self.name,  child_pubkey_list,
                                 child_xtended_privkey,  self.m,  self.n,  self.addr_type,
                                 self.testnet, self.segwit,  self.name, index)
        
        return child_wallet
    
    def get_year_wallet(self, index=None):
        """
        Returns a year_safe wallet based on the index.
        If this-years's wallet is desired, don't pass any argument or set index to None.
        """
        if self.safe_index >= 0: raise Exception ("Only master wallets can create safe wallets.")
        path = "m/44H/0H/3H/"
        if index is None:
            today = datetime.datetime.now()
            index_string = str(today.year)
            index = int(index_string)
            
        safe_wallet = self.get_child_wallet(index, path)
        
        return safe_wallet
    
    def get_sub_wallet(self, index=None):
        """
        WARINING: CURRENTLY NOT BEING USED! this method is not being used due to design changes. The \
        new design uses only accounts from the year-corporate wallet instead of creating child wallets.
        
        Returns a year_safe wallet based on the index. If a new wallet is being created, don't pass \
        any argument since the method should decide what index to assign the new wallet. Index must be\
         used only when recoverying an existing wallet.
        """
        #if self.safe_index >= 0: raise Exception ("Only master wallets can create safe wallets.")
        path = "m/"
        if index is None:
            self.start_conn()

            last_index = self.db.get_max_child_wallet_index( self.name)

            if last_index is None: i = 0
            else: i = last_index + 1

            self.close_conn()
            
        child_wallet = self.get_child_wallet(index, path)
        
        return child_wallet
    
    def get_unused_addresses_list(self, change_addresses=False, account_index=None):
        """
        change_addresses: Boolean. If change addresses are desired, set this to True.
        account_index: int. The index of the corporate account in the BIP32 tree
        """
        self.start_conn()
        unused_addresses = self.db.get_unused_safe_addresses(name = self.name)
        self.close_conn()
        print(f"unused_addresses: {unused_addresses}")
        
        if account_index is None: 
            if change_addresses: receiving_path = "m/1/"
            else: receiving_path = "m/0/"
        else: 
            if account_index < 2: raise Exception("Acount indeces 0 and 1 are reserved.")
            if change_addresses: receiving_path = f"m/{account_index}/1/"
            else: receiving_path = f"m/{account_index}/0/"
            
            
        unused_addresses_filtered = [x for x in unused_addresses if x[2]==receiving_path]
        
        #if    change_addresses: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==1]
        #else: unused_addresses_filtered =  [x for x in unused_addresses if x[1]==0]
        
        return unused_addresses_filtered
                               
                               
    def create_receiving_address(self, addr_type = "p2wsh",index=None, account_index=None):
        """
        index: int. If an address with a specific index is desired then 'index' must be an int.
        account_index: int. The index of the corporate account in the BIP32 tree
        """
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        if addr_type.lower() ==    "p2sh":       _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
            
        if account_index is None: 
            receiving_path = "m/0/"
        else: 
            if account_index < 2: raise Exception("Acount indeces 0 and 1 are reserved.")
            receiving_path = f"m/{account_index}/0/"
            
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

    
    def create_change_address(self, addr_type = "p2wsh", index=None, account_index=None):
        """
        index: int. If an address with a specific index is desired then 'index' must be an int.
        account_index: int. The index of the corporate account in the BIP32 tree
        """
        if self.safe_index < 0: raise Exception ("Only child wallets can create addresses.")
        
        
        i = self.get_i(self.name,receiving_path, index)
        
        if account_index is None: 
            receiving_path = "m/1/"
        else: 
            if account_index < 2: raise Exception("Acount indeces 0 and 1 are reserved.")
            receiving_path = f"m/{account_index}/1/"
        
        path = receiving_path + str(i)
        print(f"Change address's Path: {path}")
        
        account = FHMAccount(self.m, self.xtended_pubkey_list, self.master_privkey, self.addr_type,
                             self.testnet, self.segwit)
        
        change_account = account.get_change_account(index=i)
        self.start_conn()
        self.db.new_address(change_account.address,receiving_path,i,TRUE, P2WSH, self.name, self.safe_index)
        self.close_conn()
        return change_account
    
    
    def share(self):
        if self.safe_index >= 0: raise Exception ("Only master wallets can be shared.")
        return {"master_pubkey_list":self.xtended_pubkey_list,"m":self.m, "n":self.n, "addr_type":self.addr_type,
                "testnet":self.testnet, "segwit":self.segwit }
    

    def new_account(self, index, name):
        """
        index: int. must be greater than 1.
        name: name of the account being created.
        """
        self.db.new_corportate_account(name,index,self.name)
    
    def get_utxos_from_corporate_account(self,account_index=None):
        """
        This method is an overwritten version of the original Wallet-class version.
        account_index: int. The index of the corporate account in the BIP32 tree. If set \
        to None, it will return only the utxos from accounts 0 and 1.
        """
        self.start_conn()
        coins = self.db.look_for_coins(self.name) #ORIGINAL LINE!
        
        if account_index is None: 
            change_path = "m/1/"
            deposit_path = "m/0/"
        else: 
            if account_index < 2: raise Exception("Acount indeces 0 and 1 are reserved.")
            change_path = f"m/{account_index}/1/"
            deposit_path = f"m/{account_index}/0/"
            
        coins_from_account = [ x for x in unused_addresses  if  x[3] == change_path  or  x[3] == deposit_path ]
        
        self.close_conn()
        return coins_from_account
    
        
    def get_coins(self, to_address_amount_list, send_all=None, segwit=True, account_index=None, total=False):
        """
        Returns a dictionary with the utxos, fee, and change.
        to_address_amount_list: List of tuples [(address1,amount1),(address2,amount2),...]
        send_all: bool/None: if you are trying to send all of your funds somewhere else, set this to True.
        account_index: if we are trying to spend from a specific account, then spicify the index here.
        total: if we are trying to spend from the wallet and not from a specific account, then set this to True. \
        If True, account_index will be ignored.
        
        """
        print(f"From wallet.send(): {to_address_amount_list}")
        #calculate total amount to send from the wallet
        total_amount = sum([x[1] for x in to_address_amount_list])
        
        #We get all of our utxos depending if we are spending the 'total' of our wallet, or from
        #a specific account.
        if    total:               all_utxos = self.get_utxos()
        elif account_index is None:all_utxos = self.get_utxos_from_corporate_account()
        else:                      all_utxos = self.get_utxos_from_corporate_account(account_index)
        
        # ..and calculate our balance.
        
        if len(all_utxos) == 0: raise Exception("There is no coins at all here.")
        balance = sum([x[2] for x in all_utxos])
        
        #We calculate the min and max fee for using all of our coins:
        min_fee = (len(all_utxos)*146 + len(to_address_amount_list)*34 + 20)*min_fee_per_byte
        max_fee = min_fee*2 + 546
        
        #If we are trying to send more than what we have minus the minumim fee, but we are not explicitly
        #trying to send all of our money somewhere, then we raise an exception. We don't have enough funds.
        if total_amount>balance-min_fee and not send_all:
            raise Exception(f"Not enough funds in wallet for this transaction.\nOnly {balance} satoshis available for a tx\
            with minimum fee of {min_fee} and a total output of {total_amount}")
        
        #If not, we try to find out if this tx is unawarely trying to spend all of our funds:
        elif total_amount >= balance - max_fee and total_amount <= balance-min_fee and not send_all: send_all = True
            
        #If we are indeed trying to send all the funds, then we choose all the utxos
        if send_all: coins = {"utxos":all_utxos,"fee":min_fee,"change":False}
        #If not, then we have to choose in an efficient manner.
        else: coins = coin_selector(all_utxos, total_amount, len(to_address_amount_list)) 
        
        return coins
        
    def get_signing_account(self):
        
        #We create the multisignature account to sign the transaction. 
        account = FHMAccount(self.m, self.xtended_pubkey_list, self.master_privkey, self.addr_type,
                             self.testnet, self.segwit)
        
        return account
        
    