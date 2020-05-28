"""
This module is coded entirely by Oscar Serna.
This code makes use of the code written by Jimmy Song in the book Programming Bitcoin.
This code only tries to build on Jimmi Song's code and take it to the next step as 
suggested by him in chapter 14 of his book.

This is just an educational-purpose code. The author does not take any responsibility
on any losses caused by the use of this code.
"""
from accounts import MasterAccount, Account, MultSigAccount
from transactions import Transaction, MultiSigTransaction
from os import urandom
from database import WalletDB
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
        
        
        self.db = WalletDB( "neo4j://localhost:7687" ,db_user ,db_password )
        super().__init__( depth, fingerprint, index, chain_code, private_key,testnet)
        
        if not self.db.exist_wallet(self.get_xtended_key()):
            self.db.new_wallet(self.get_xtended_key())
        
        self.start_schedule()
        
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
        #print("cleaning addresses...")
        self.db.clean_addresses()

    def close_db(self):
        self.db.close()
    
    @classmethod
    def get_i(self, index):
        if index is None:
            print(f"get i: {index}")
            i = int.from_bytes(urandom(4),"big")
            i = i & 0x7fffffff
            if i < (2**31-1):print("true")
        else:
            if index <= (2**31-1):
                i = index
            else:
                raise Exception (f"index must be less than {2**31-1} ")
        return i

    #@classmethod
    def get_unused_addresses_list(self, change_addresses=False, range_of_days=None, last_day_range=None):
        
        unused_addresses = self.db.get_unused_addresses(xprv = self.get_xtended_key(), 
                                                        days_range = range_of_days, 
                                                        max_days = last_day_range)
        
        if change_addresses:
            unused_addresses_filtered =  [x for x in unused_addresses if x["unused_address.type"]=="change"]
        else:
            unused_addresses_filtered =  [x for x in unused_addresses if x["unused_address.type"]=="recipient"]
        
        return unused_addresses_filtered
                               
                               
    #@classmethod
    def create_receiving_address(self, addr_type = "p2pkh",index=None):
        receiving_path = "m/0H/2H/"
        i = self.get_i(index)
        path = receiving_path + str(i)
        print(f"Path: {path}")
        receiving_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(receiving_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.db.new_address(account.address,i,False, self.get_xtended_key())
        return account

    #@classmethod
    def create_change_address(self,addr_type = "p2wpkh", index=None):
        change_path = "m/0H/1H/"
        i = self.get_i(index)
        path = change_path + str(i)
        print(f"Path: {path}")
        change_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(change_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.db.new_address(account.address,i,True, self.get_xtended_key())
        return account
    
    def get_utxos(self):
        return self.db.look_for_coins(self.get_xtended_key())
        
    def get_balance(self):
        coins = self.get_utxos()
        balance = 0
        for coin in coins:
            balance += coin["coin.amount"]
        return balance

    def update_balance(self):
        addresses = self.db.get_all_addresses(self.get_xtended_key())
        
        if self.testnet: coin_symbol = "btc-testnet"
        else: coin_symbol = "btc"
            
        for address in addresses:
            
            addr_info = get_address_details(address["addr.address"], coin_symbol = coin_symbol, unspent_only=True)
            
            if addr_info["unconfirmed_n_tx"] > 0:
                for utxo in addr_info["unconfirmed_txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], False):
                        print("new unconfirmed UTXO")
                        self.db.new_utxo(utxo["address"],utxo["tx_hash"],utxo["tx_output_n"],utxo["value"],False)
            
            if addr_info["n_tx"] - addr_info["unconfirmed_n_tx"] > 0 :
                for utxo in addr_info["txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], True):
                        print("new confirmed UTXO")
                        self.db.new_utxo(addr_info["address"],utxo["tx_hash"],utxo["tx_output_n"],utxo["value"],True)
      
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
            if utxo["coin.amount"] > total_amount*1.1:
                utxos = [utxo]
                break
                
        if len(utxos)==0:    
            for utxo in all_utxos:
                utxos.append(utxo)
                utxo_total += utxo["coin.amount"]
                if utxo_total>total_amount: break
        change_account = self.create_change_address()
          
        tx = Transaction.create_from_master( utxos,to_address_amount_list, self,change_account,
                           fee=None, segwit=segwit)
        
        print(f"TRANSACTION ID: {tx.transaction.id()}")
        
        #saving in db
        self.db.new_tx(tx.transaction.id(),[x["coin.local_index"] for x in utxos], 
                       #[str(x[0])+":"+str(x[1]) for x in to_address_amount_list]
                       [str(x) for x in tx.transaction.tx_outs]
                      )
        if self.testnet: symbol = "btc-testnet"
        else: symbol= "btc"
        
        load_dotenv()
        BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
        push = pushtx(tx_hex= tx.transaction.serialize().hex(), coin_symbol=symbol,api_key=BLOCKCYPHER_API_KEY)
        
        self.db.update_utxo(tx.transaction.id())
        
        return tx,push
        