from neo4j import GraphDatabase

class WalletDB(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!

    def close(self):
        self._driver.close()
        
        
    @staticmethod
    def _new_address(tx, address,i,change_addr,wallet_xprv):
        if change_addr: addr_type = "change"
        else: addr_type = "recipient"
        result = tx.run("MATCH (w:wallet {xprv:$xprv})"
                        "CREATE a = (:address {address:$address, acc_index:$index, type:$kind, created:timestamp()}) "
                        "<- [:OWNS]-(w)"
                        "RETURN a ", address=address, index = i, kind = addr_type, xprv=wallet_xprv)
        return result.single()
    
    
    @staticmethod
    def _new_utxo(tx, address,tx_id,out_index, amount,confirmed):
        local_index = tx.run( "MATCH (u:utxo) RETURN COUNT (u) ").single()[0] 
        result = tx.run("MATCH (n:address {address : $address}) "
                        "CREATE p = (:utxo {address:$address, transaction_id:$tx_id, out_index:$out_index, local_index:$local_index, spent:false, amount:$amount, confirmed:$confirmed})-[:BELONGS]->(n) "
                        "RETURN p ", address=address, tx_id = tx_id, out_index = out_index, 
                        local_index=local_index,amount=amount,confirmed=confirmed)
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
        return result.data()
    
    
    @staticmethod
    def _clean_addresses(tx):
        result = tx.run("MATCH (a: address) "
                        "WHERE NOT (a)--() AND (timestamp() - a.created )>2592000000 "
                        "DELETE a ")
        return result.single()

    
    @staticmethod
    def _look_for_coins(tx,xprv):
        result = tx.run("MATCH (coin:utxo {spent:false})--(address)--(w:wallet {xprv:$xprv}) "
                        "RETURN coin.transaction_id, coin.out_index, coin.address, coin.amount, coin.local_index, address.acc_index, address.type ",xprv=xprv)
        return result.data()
    
    @staticmethod
    def _get_unused_addresses(tx):
        result = tx.run("MATCH (unused_address:address) "
                        "WHERE NOT (unused_address)--() "
                        "RETURN  unused_address.address, unused_address.acc_index, unused_address.type ")
        return result.data()
    
    @staticmethod
    def _get_all_addresses(tx,xprv):
        result = tx.run("MATCH (addr:address)<-[:OWNS]-(:wallet {xprv:$xprv}) "
                        "RETURN  addr.address, addr.acc_index, addr.type ",xprv=xprv)
        return result.data()
    
    @staticmethod
    def _exist_utxo(tx, tx_id, out_index, confirmed):
        result = tx.run("MATCH (coin:utxo {transaction_id:$tx_id, out_index:$out_index}) "
                        "RETURN  coin.amount, coin.confirmed ",tx_id=tx_id, out_index=out_index)
        data = result.data()
        if len(data)>0:
            _confirmed = data[0]["coin.confirmed"]
            if _confirmed != confirmed:
                tx.run("MATCH (coin:utxo {transaction_id:$tx_id, out_index:$out_index}) "
                       "SET coin.confirmed = $confirmed "
                        "RETURN  coin.amount, coin.confirmed ",tx_id=tx_id, out_index=out_index, confirmed=confirmed)
            return True
        else: return False
        
    @staticmethod
    def _new_wallet(tx,xprv):
        result = tx.run("CREATE (w:wallet {xprv: $xprv}) "
                        "RETURN  w ",xprv = xprv )
        return result.single()
    
    @staticmethod
    def _exist_wallet(tx, xprv):
        result = tx.run("MATCH (wallet:wallet {xprv:$xprv}) "
                        "RETURN  COUNT (wallet) ",xprv = xprv )
        data = result.data()
        #print(f"data: {data}")
        if data[0]["COUNT (wallet)"]>0: return True
        else: return False
            



    
    def new_address(self, address,i,change_addr,wallet_xprv):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_address, address,i,change_addr,wallet_xprv)
            print(result)
            
    def new_utxo(self, address,tx_id,out_index,amount,confirmed):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_utxo, address,tx_id,out_index,amount,confirmed)
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
            
    def look_for_coins(self,xprv):
        with self._driver.session() as session:
            result = session.write_transaction(self._look_for_coins,xprv)
            return result
        
    def get_unused_addresses(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._get_unused_addresses)
            return result
        
    def get_all_addresses(self,xprv):
        with self._driver.session() as session:
            result = session.write_transaction(self._get_all_addresses,xprv)
            return result
            
    def exist_utxo(self, tx_id, out_index, confirmed):
        with self._driver.session() as session:
            result = session.write_transaction(self._exist_utxo, tx_id, out_index, confirmed)
            return result
        
    def new_wallet(self, xprv):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_wallet, xprv )
            print(result)
            return result
        
    def exist_wallet(self, xprv):
        with self._driver.session() as session:
            result = session.write_transaction(self._exist_wallet, xprv )
            return result