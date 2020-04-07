from neo4j import GraphDatabase

class WalletDB(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!

    def close(self):
        self._driver.close()
        
        
    @staticmethod
    def _new_address(tx, address,i,change_addr):
        if change_addr: addr_type = "change"
        else: addr_type = "recipient"
        result = tx.run("CREATE a = (:address {address:$address, acc_index:$index, type:$kind, created:timestamp()}) "
                        "RETURN a ", address=address, index = i, kind = addr_type)
        return result.single()
    
    
    @staticmethod
    def _new_utxo(tx, address,tx_id,out_index, amount):
        local_index = tx.run( "MATCH (u:utxo) RETURN COUNT (u) ").single()[0] 
        result = tx.run("MATCH (n:address {address : $address}) "
                        "CREATE p = (:utxo {address:$address, transaction_id:$tx_id, out_index:$out_index, local_index:$local_index, spent:false, amount:$amount})-[:BELONGS]->(n) "
                        "RETURN p ", address=address, tx_id = tx_id, out_index = out_index, local_index=local_index,amount=amount)
        return result.single()
    
    
    @staticmethod
    def _new_tx(tx,tx_id,inputs, outputs):
        result = tx.run("CREATE (n:TxOut {id:$tx_id, inputs:$inputs , outputs:$outputs, confirmations:0, created:timestamp()}) "
                        "WITH n "
                        "UNWIND n.inputs AS ins "
                        "MATCH coins = (:utxo {local_index:ins}) "
                        "FOREACH ( coin IN nodes(coins) | CREATE (coin)<-[:SPENT]-(n) ) ",
                        tx_id=tx_id, inputs = inputs, outputs = outputs)
        return result.single()
    
    
    @staticmethod
    def _update_confirmations(tx,tx_id,n_confirmations):
        result = tx.run("MATCH (n:TxOut {id:$tx_id}) "
                        "SET n.confirmations=$n_confirmations "
                        "RETURN n ", tx_id=tx_id, n_confirmations = n_confirmations)
        return result.single()
    
    
    @staticmethod
    def _update_utxo(tx,tx_id):
        result = tx.run("MATCH p = (u)<-[:SPENT]-(:TxOut {id:$tx_id}) "
                        "SET u.spent=true "
                        "RETURN p ", tx_id=tx_id)
        return result.consume()
    
    
    @staticmethod
    def _clean_addresses(tx):
        result = tx.run("MATCH (a: address) "
                        "WHERE NOT (a)--() AND (timestamp() - a.created )>2592000000 "
                        "DELETE a ")
        return result.single()

    
    @staticmethod
    def _look_for_coins(tx):
        result = tx.run("MATCH (coin:utxo {spent:false}) "
                        "RETURN coin.transaction_id, coin.out_index, coin.address, coin.amount ")
        return result.data()
    
    @staticmethod
    def _get_unused_addresses(tx):
        result = tx.run("MATCH (unused_address:address) "
                        "WHERE NOT (unused_address)--() "
                        "RETURN  unused_address.address, unused_address.acc_index, unused_address.type ")
        return result.data()



    
    def new_address(self, address,i,change_addr):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_address, address,i,change_addr)
            print(result)
            
    def new_utxo(self, address,tx_id,out_index,amount):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_utxo, address,tx_id,out_index,amount)
            print(result)
            
    def new_tx(self, tx_id,utxo_local_index_list, outputs):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_tx, tx_id,utxo_local_index_list, outputs)
            print(result)
            
    def update_confirmations(self, tx_id,n_confirmations):
        with self._driver.session() as session:
            result = session.write_transaction(self._update_confirmations, tx_id,n_confirmations)
            print(result)
            
    def update_utxo(self, tx_id):
        with self._driver.session() as session:
            result = session.write_transaction(self._update_utxo, tx_id)
            print(result)
        
    def clean_addresses(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._clean_addresses)
            print(result)
            
    def look_for_coins(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._look_for_coins)
            return result
        
    def get_unused_addresses(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._get_unused_addresses)
            return result
            