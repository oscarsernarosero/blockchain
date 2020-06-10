import sqlite3
from sqlite3 import Error
import time

class Sqlite3Wallet:
    
    def __init__(self):
        self.conn = None
        self.conn = self.create_connection(r"database/wallet_db.db")
        
    def create_connection(self,db_file):
        """ create a database self.connection to a SQLite database """
        conn = None
        try:
 
            return conn

        except Error as e:
            print(e)

    def close_database(self):
        if self.conn:
            self.conn.close()
        
    def execute_w_res(self, query):
        try:
            c = self.conn.cursor()
            result = c.execute(query)
            return result.fetchall()
        except Error as e:
            print(e)
            return None
        
    def execute(self, query):
        try:
            c = self.conn.cursor()
            c.execute(query)
            return True
        except Error as e:
            print(e)
            return None
        
    def create_wallet_table(self):
        query1 =  f"CREATE TABLE IF NOT EXISTS Wallets ( xprv text NOT NULL PRIMARY KEY,\n "
        query2 = f"name text, words text NOT NULL) WITHOUT ROWID;"
        query = query1+query2
        #print(query)
        return self.execute(query)

    def create_address_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Addresses ( address text NOT NULL PRIMARY KEY,\nacc_index INT NOT NULL,"
        query2 = "\npath text NOT NULL,\nchange_addr INT NOT NULL,\ncreated INT NOT NULL,\nwallet text NOT NULL,\nFOREIGN KEY (wallet) "
        query3 = "\nREFERENCES Wallets(xprv) ) WITHOUT ROWID ;"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)

    def create_utxo_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Utxos ( address text NOT NULL,\namount INT NOT NULL,\ntx_id text NOT NULL,"
        query2 = "\nout_index INT NOT NULL,\ncreated INT NOT NULL,\nspent INT NOT NULL,\nconfirmed INT NOT NULL, "
        query3 = "\nPRIMARY KEY (tx_id, out_index)\nFOREIGN KEY (address)\nREFERENCES Addresses(address) );"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)

    def create_transaction_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Transactions ( tx_id text NOT NULL PRIMARY KEY,\nlock_time INT,\nversion INT,\n"
        query2 = "\nn_confirmations INT NOT NULL,\ncreated INT NOT NULL)  WITHOUT ROWID ;"
        query = query1 + query2
        #print(query)
        return self.execute( query)

    def create_tx_in_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Tx_Ins ( tx_id text NOT NULL, out_index INT NOT NULL,\nspent_by text NOT NULL,\n"
        query2 = "PRIMARY KEY (tx_id,out_index,spent_by)\n "
        query3 = "FOREIGN KEY (tx_id,out_index)\nREFERENCES Utxo(tx_id,out_index) \n "
        query4 = "FOREIGN KEY (spent_by)\nREFERENCES Transactions(tx_id) )  WITHOUT ROWID ;"
        query = query1 + query2 + query3 + query4
        #print(query)
        return self.execute(query)

    def create_tx_out_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Tx_Outs ( out_index INT NOT NULL,\n amount INT NOT NULL,\ncreated_by text NOT NULL,\n"
        query2 = "script_pubkey text NOT NULL, \n PRIMARY KEY (created_by, out_index)\n"
        query3 = "FOREIGN KEY (created_by)\nREFERENCES Transactions(tx_id) )  WITHOUT ROWID ;"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)

    def create_tables(self):
        self.create_wallet_table()
        self.create_address_table()
        self.create_utxo_table()
        self.create_transaction_table()
        self.create_tx_in_table()
        self.create_tx_out_table()
        return True

    def new_wallet(self, xprv, words, name = None ):
        """
        Creates a new wallet in the database.
        self.conn: self.conn: internal database driver transaction.
        xprv: String; extended private key of the wallet.
        words: String; The mnemonic phrase of the wallet.
        name: String Optional. This is an alias for the wallet if user prefers it.
        """
        query1 = "INSERT INTO Wallets (xprv, words, name)\n "
        query2 = f"VALUES('{xprv}', '{words}', '{name}') ;"
        query = query1+query2
        #print(query)
        return self.execute(query)

    def new_address(self, address, path, acc_index, change_addr, wallet):
        """
        Creates a new address in the database.
        self.conn: internal database driver transaction.
        address: String; the address to create.
        path: String; the path in wich the address is created until the account level. i.e. "m/44'/0'/0'/"
        as a standard, it must start with m and end with /
        acc_index: int; account index. This would be the last part of the path.
        change_addr: int, 0=False, 1=True; if the address is a "change adrress" then 1 (True). Otherwise 0 (False).
        wallet: String; the xtended private key of the wallet
        """
        created = int(time.time())
        query1 = "INSERT INTO Addresses (address, path, acc_index, change_addr, created, wallet)\n "
        query2 = f'VALUES("{address}", "{path}", {acc_index}, {change_addr}, {created}, "{wallet}") ;'
        query = query1+query2
        #print(query)
        return self.execute(query)

    def new_utxo(self, address, amount, tx_id, out_index, spent=0, confirmed=0):
        """
        Creates new utxo in the database.
        self.conn: internal database driver transaction.
        address: the base58 representation of the address that holds the utxo.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        amount: Int, the amount of SATOSHIS that the utxo holds.
        spent: Int, 0=False, 1=True; if the utxo has been spent by a transaction then 1 (True).
        confirmed: Int, 0=False, 1=True; if the transaction has less than 6 confirmations then 0 (False).
        """
        created = int(time.time())
        query1 = "INSERT INTO Utxos (address, amount, tx_id, out_index, created, spent, confirmed)\n "
        query2 = f"VALUES('{address}', {amount}, '{tx_id}', {out_index}, {created}, {spent}, {confirmed});"
        query = query1+query2
        #print(query)
        return self.execute(query)

    def new_tx(self, tx_id, tx_ins, tx_outs, n_confirmations = 0, lock_time=0, version=1 ):
        """
        tx_id: String. transaction id.
        tx_ins: List of touples: [ (prev_tx_id, index), ... ]
        tx_outs: List of touples: [ (out_index, amount, script_pubkey), ... ]
        n_confirmations: int; number of confirmations in the blockchain.
        lock_time: Int: transaction locktime.
        version: Int: version.
        """
        created = int(time.time())
        query1 = "INSERT INTO Transactions ( tx_id, created, n_confirmations, lock_time, version)\n "
        query2 = f"VALUES('{tx_id}', {created}, {n_confirmations}, {lock_time}, {version});"
        query = query1+query2
        self.execute(query)

        for tx_in in tx_ins:
            query3 = "INSERT INTO Tx_Ins ( tx_id, out_index, spent_by)\n "
            query4 = f"VALUES( '{tx_in[0]}', {tx_in[1]}, '{tx_id}');"
            query = query3+query4
            self.execute(query)

        for tx_out in tx_outs:
            query5 = "INSERT INTO Tx_Outs ( out_index, amount, script_pubkey, created_by)\n "
            query6 = f"VALUES( {tx_out[0]}, {tx_out[1]}, '{tx_out[2]}', '{tx_id}');"
            query = query5+query6
            self.execute(query)

        return True

    def update_confirmations(self, tx_id, n_confirmations):
        """
        Updates the number of confirmations for a transaction to later confirm the transaction was broadcasted.
        self.conn: internal database driver transaction.
        tx_id: String, the id or hash of the transaction being broadcasted.
        n_confirmations: Int, the number of confirmations.
        """
        query = f"UPDATE Transactions \nSET n_confirmations = {n_confirmations} WHERE tx_id = '{tx_id}'"
        return self.execute(query)

    def spend_utxo(self, tx_id, out_index):
        query = f"UPDATE Utxos \nSET spent = 1 \nWHERE tx_id = '{tx_id}' AND out_index = {out_index} "
        return self.execute(query)

    def spend_utxo(self, tx_id, out_index):
        """
        Updates the state of an exisiting utxo to "spent=True" once the transaction was broadcasted successfully and confirmed.
        self.conn: internal database driver transaction.
        tx_id: String, the id or hash of the transaction that created the utxo (previous transaction).
        out_index: index of the utxo in the previous transaction.
        """
        query = f"UPDATE Utxos \nSET spent = 1 \nWHERE tx_id = '{tx_id}' AND out_index = {out_index} "
        return self.execute(query)

    def clean_addresses(self):
        """
        Not necessary in this implementation.
        """
        pass

    def look_for_coins(self, wallet):
        """
        Searches the database for utxos that haven't been spent for the specific wallet.
        self.conn: internal database driver transaction.
        wallet: String, The wallet extended private key.
        Returns: List of touples [(tx_id, out_index, amount)]
        """
        query1 = f"SELECT tx_id, out_index, amount\n FROM Utxos INNER JOIN Addresses \n"
        query2 = f"ON Utxos.address = Addresses.address\nWHERE Utxos.spent = 0 AND Addresses.wallet = '{wallet}';"
        query = query1 + query2
        return self.execute_w_res(query)

    def get_unused_addresses(self,wallet, days_range=None, max_days=None):
        """
        Searches the database for addresses that haven't been used in the specific wallet.
        tx: internal database driver transaction.
        xprv: String, The wallet extended private key.
        max_days: how far away should the app look for the unused address in the pass. The limit is 30 since the app deletes 
        unused addresses after a month of creation.
        days_range: number of days for the range in which to look for the address. The range will start
        in day_range days before the max_days day (starting_day = (max_days - days_range)).

        days_range and max_days should be either both specified or neither specified. If they are not, both values will be
        automatically set to 30 making the search to happen from now to the last 30 days. If only one of them is specified, 
        the function will throw an exception.
        """
        if days_range is None and max_days is None:
            query1 = f"SELECT address \nFROM Addresses WHERE\nNOT EXISTS(\nSELECT 1 \n FROM Utxos"
            query2 = f"\nWHERE Utxos.address = Addresses.address) \nAND\n Addresses.wallet = '{wallet}';"
            query = query1 + query2
            #print(query)
            return self.execute_w_res(query)

        elif (days_range is None or max_days is None) and (days_range != max_days):
            raise Exception("Arguments days_range and max_days must be either both specified or neither one specified.")

        else:
            SEC_PER_DAY = 86400
            finish_day = max_days * SEC_PER_DAY
            start_day = finish_day - days_range * SEC_PER_DAY
            now = int(time.time())
            query1 = f"SELECT address \nFROM Addresses WHERE\nNOT EXISTS(\nSELECT 1 \n FROM Utxos"
            query2 = f"\nWHERE Utxos.address = Addresses.address) \nAND\n Addresses.wallet = '{wallet}'"
            query3 = f"\nAND\n ({now} - Addresses.created) > {start_day} AND ({now} - Addresses.created) < {finish_day} ';"
            query = query1 + query2 + query3
            #print(query)
            return self.execute_w_res(query)

    def get_all_addresses(self,wallet):
        """
        Returns all the addresses in the database for the specific wallet.
        self.conn: internal database driver transaction.
        wallet: String, The wallet extended private key.
        """
        query = f"SELECT address \nFROM Addresses WHERE wallet = '{wallet}'; "
        return self.execute_w_res(query)

    def exist_utxo(self, tx_id, out_index, confirmed):
        """
        Returns True if the utxo already exists in the database. False if it doesn't. It also updates
        the "confirmed" property of the utxo if necessary.
        tx: internal database driver transaction.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        confirmed: Int/Boolean 0=False, 1=True; the current state of confirmation of the transaction in the actual blockchain.
        """
        query = f"SELECT * FROM Utxos WHERE  tx_id = '{tx_id}' AND out_index = {out_index}"
        result = execute_w_res(query)
        if len(result)>0:
            if result[0][6] != confirmed:
                query = f"UPDATE Utxos \nSET confirmed = {confirmed} WHERE tx_id = '{tx_id}' AND out_index = {out_index} "
                result = execute_w_res(query)

        return True

    def does_table_exist(self, table):
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';"
        return self.execute_w_res(query)
    
    def erase_database(self):
        query = "DROP TABLE Tx_Ins"
        self.execute(query)
        query = "DROP TABLE Tx_Outs"
        self.execute(query)
        query = "DROP TABLE Transactions"
        self.execute(query)
        query = "DROP TABLE Utxos"
        self.execute(query)
        query = "DROP TABLE Addresses"
        self.execute(query)
        query = "DROP TABLE Wallets"
        self.execute(query)
        return True