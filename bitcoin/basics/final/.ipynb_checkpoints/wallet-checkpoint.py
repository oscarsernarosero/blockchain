"""
This module is coded entirely by Oscar Serna.
This code makes use of the code written by Jimmy Song in the book Programming Bitcoin.
This code only tries to build on Jimmi Song's code and take it to the next step as 
suggested by him in chapter 14 of his book.

This is just an educational-purpose code. The author does not take any responsibility
on any losses caused by the use of this code.
"""
from constants import *
from accounts import MasterAccount, Account, MultSigAccount
from transactions import Transaction, MultiSigTransaction
from os import urandom
#from database import WalletDB
from wallet_database_sqlite3 import Sqlite3Wallet
from blockcypher import get_address_details
from blockcypher import pushtx
from dotenv import load_dotenv
import os

import schedule 
import time 

class Wallet(MasterAccount):
    
    def __init__(self, depth, fingerprint, index, chain_code, private_key, db_user="neo4j",db_password="wallet", testnet = False):
        
        load_dotenv()
        BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
        
        
        #self.db = WalletDB( "neo4j://localhost:7687" ,db_user ,db_password )
        
        super().__init__( depth, fingerprint, index, chain_code, private_key,testnet)
        
        #if not self.db.exist_wallet(self.get_xtended_key()):
            #self.db.new_wallet(self.get_xtended_key())
        
        #self.start_schedule()
        
    @classmethod
    def start_schedule(self):
        """
        This method starts the process of the scheduled tasks that are in charge of cleaning the database, 
        updating the balace automatically every hour, and update confirmations on new transactions sent or
        received.
        """
        schedule.every().day.do(self.clean_addresses)
        schedule.every().hour.do(self.update_balance)
        #pendind: to update confirmations of incoming and outcoming transactions.
        
    
    #@classmethod
    def clean_addresses(self):
        print("cleaning addresses...")
        self.db.clean_addresses()
        
    def start_conn(self, conn=None):
        if conn:
            self.db= conn
        else:
            self.db = Sqlite3Wallet()
        return True

    def close_conn(self):
        self.db.conn.close()
    
    def close_db(self):
        self.db.close_database()
    
    #@classmethod
    def get_i(self,account_path, index,random_index = False):
        if random_index:
            if index is None:
                print(f"get i: {index}")
                i = int.from_bytes(urandom(4),"big")
                i = i & 0x7fffffff
                if i < (2**31-1):print("true")
            elif index is not None:
                if index <= (2**31-1):
                    i = index
                else:
                    raise Exception (f"index must be less than {2**31-1} ")
        else:
            try:
                print(f"{self.db} OK.")
            except:
                self.start_conn()
                
            last_index = self.db.get_max_index( account_path, self.get_xtended_key())
            
            if last_index is None: i = 0
            else: i = last_index + 1
            
            
        return i

    #@classmethod
    def get_unused_addresses_list(self, change_addresses=False, range_of_days=None, last_day_range=None):
        
        unused_addresses = self.db.get_unused_addresses(wallet = self.get_xtended_key(), 
                                                        days_range = range_of_days, 
                                                        max_days = last_day_range)
        
        if change_addresses:
            unused_addresses_filtered =  [x for x in unused_addresses if x[1]==1]
        else:
            unused_addresses_filtered =  [x for x in unused_addresses if x[1]==0]
        
        return unused_addresses_filtered
                               
                               
    def create_receiving_address(self, addr_type = "p2pkh",index=None):
        if addr_type.lower()   ==   "p2pkh":     _type  = P2PKH
        elif addr_type.lower() ==  "p2wpkh":     _type  = P2WPKH
        elif addr_type.lower() ==    "p2sh":     _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wpkh": _type  = P2SH_P2WPKH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
        receiving_path = "m/44H/0H/0H/"
        i = self.get_i(receiving_path, index)
        path = receiving_path + str(i)
        print(f"Deposit address's Path: {path}")
        receiving_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(receiving_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.db.new_address(account.address,receiving_path,i,FALSE, _type, self.get_xtended_key())
        return account

    
    def create_change_address(self, addr_type = "p2wpkh", index=None):
        change_path = "m/44H/0H/1H/"
        i = self.get_i(change_path, index)
        path = change_path + str(i)
        print(f"Change address's Path: {path}")
        change_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(change_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.db.new_address(account.address,change_path,i,TRUE, P2WPKH, self.get_xtended_key())
        return account
    
    def get_a_change_address(self):
        """
        Returns an Account object containing a change address. It returns an existing unused change
        address account, or creates a new one if necessary.
        """
        unused_addresses = self.get_unused_addresses_list(change_addresses=True)
        
        if len(unused_addresses)>0: 
            #We grab the first unused address always
            #The unused_addresses will be a list of touples. Each touple will be (address, change_addr, path, acc_index)
            change_xtended_acc = self.get_child_from_path(f"{unused_addresses[0][2]}{unused_addresses[0][3]}")
            account = Account(int.from_bytes(change_xtended_acc.private_key,"big"),"p2wpkh", self.testnet )
            if unused_addresses[0][0] == account.address:
                return account
            else:
                raise Exception("Addresses don't match!")
        else: return create_change_address()
    
    def get_utxos(self):
        return self.db.look_for_coins(self.get_xtended_key())
        
    def get_balance(self):
        coins = self.get_utxos()
        print(coins)
        balance = 0
        if len(coins)>0:
            for coin in coins:
                print(coin)
                "coin will be an array with data [ tx_id, out_index, amount ]"
                balance += coin[2]
        return balance

    def update_balance(self):
        addresses = self.db.get_all_addresses(self.get_xtended_key())
        
        if self.testnet: coin_symbol = "btc-testnet"
        else: coin_symbol = "btc"
            
        for address in addresses:
            "address will be a touple with data (address,)"
            print(f"consulting blockchain for address {address}")
            addr_info = get_address_details(address[0], coin_symbol = coin_symbol, unspent_only=True)
            print(f"res for {address}:\n{addr_info}")
            
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
                        self.db.new_utxo(addr_info["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],confirmed = 1)
      
        return self.get_balance()
    
    #@classmethod
    #def create_multisig_account(m,public_key_list,account,addr_type="p2sh", testnet = False, segwit=True):
    #    n = len(public_key_list)
    #    return MultiSigTransaction(m, n, int.from_bytes(account.private_key,"big"), public_key_list, addr_type, testnet, segwit)

    #@classmethod
    def send(self, to_address_amount_list, segwit=True):
        """
        to_address can be a single address or a list.
        amount can be an integer or a list of integers.
        If they are lists, they must be ordered in the same way. address 1 will e sent amount 1, 
        adrress 2 will be sent amount2.. adress n will be sent amount n.
        """
        print(f"From wallet.send(): {to_address_amount_list}")
        total_amount = 0
        for output in to_address_amount_list:
            total_amount += output[1]
            
        balance = self.get_balance()
        if total_amount>balance:
            raise Exception(f"Not enough funds in wallet for this transaction.\nOnly {balance} satoshis available")
            
        all_utxos = self.get_utxos()
        utxos = []
        utxo_total = 0
        for utxo in all_utxos:
            if utxo[2] > total_amount*1.1:
                utxos = [utxo]
                break
                
        if len(utxos)==0:    
            for utxo in all_utxos:
                utxos.append(utxo)
                utxo_total += utxo[2]
                if utxo_total > (total_amount*1.1) : break
        change_account = self.get_a_change_address()
          
        tx = Transaction.create_from_master( utxos,to_address_amount_list, self,change_account,
                           fee=None, segwit=segwit)
        
        if self.testnet: symbol = "btc-testnet"
        else: symbol= "btc"
        
        load_dotenv()
        BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
        push = pushtx(tx_hex= tx.transaction.serialize().hex(), coin_symbol=symbol,api_key=BLOCKCYPHER_API_KEY)
        
        print(f"TRANSACTION ID: {tx.transaction.id()}")
        
        #saving in db
        self.db.new_tx(tx.transaction.id(), [ (x[0],x[1]) for x in utxos] ,
                       [str(x).split(":")+[i] for i,x in enumerate(tx.transaction.tx_outs)]
                      )
        
        
        return tx,push
        