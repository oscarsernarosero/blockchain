import copy


def select_coins_by_exact_match(utxos, total_out,n_outputs,min_fee_per_byte=70):
    
    change_coins = [x for x in utxos if x[2] < total_out]
    change_coins.sort( key=lambda x:x[2]) 
    
    min_estimated_fee = (146 + n_outputs*34 + 20)*min_fee_per_byte
    max_estimated_fee = min_estimated_fee*2 + 546 
    
    candidates = [x for x in utxos  if  x[2]> min_estimated_fee+total_out and x[2]< max_estimated_fee+total_out]
    if len(candidates)>0:
        return [min(candidates,key=lambda x:x[2])]
    
    #If not then we check that we actually have coins to build this...
    if len(change_coins) == 0: return False
    
    min_estimated_fee = (len(change_coins)*146 + n_outputs*34 + 20)*min_fee_per_byte
    max_estimated_fee = (len(change_coins)*146 + n_outputs*34 + 20)*4 + 546 
    total_in_change_coins = sum([x[2] for x in change_coins])
    if total_in_change_coins > total_out + min_estimated_fee and total_in_change_coins <= total_out + max_estimated_fee:
        return change_coins
    
    if len(change_coins) <3: return False
    
    #In case there are only 3 coins in change_coins:
    closest_coin = change_coins[-1]
    
    if len(change_coins)==3:
        
        min_estimated_fee = (2*146 + n_outputs*34 + 20)*min_fee_per_byte
        max_estimated_fee = min_estimated_fee*2 + 546
        
        change_coins.remove(closest_coin)
        for coin in change_coins:
            
            total_ = closest_coin[2] + coin[2]
            if  total_ > total_out + min_estimated_fee and total_ <= total_out + max_estimated_fee:
                return [closest_coin,coin] 
        
        total_ = sum([x[2] for x in change_coins])
        if  total_ > total_out + min_estimated_fee and total_ <= total_out + max_estimated_fee:
                return change_coins
        return False
    
    else:
        #if our closest coin is greater than 70%, we start looking for the small one.
        if closest_coin[2] > total_out *0.7:
            #let's try to find a single UTXO that makes up for the total:
            chosen_coins = [closest_coin]
            available_coins = change_coins
            available_coins.remove(*chosen_coins)

            max_iteration = len(available_coins)*5//2
            if max_iteration > 5:  max_iteration = 5

            for i in range(max_iteration):
                coins = iterate_these_available_coins(total_out, available_coins, chosen_coins, n_outputs)
                if not isinstance(coins, bool) and not isinstance(coins[0], bool):
                    return coins
                available_coins = coins[ 1]
                chosen_coins = coins[2]
            return False
            
        #elif closest_coin[2] > total_out *0.45:
        else:
            #let's try to find a single UTXO that makes up for the total:
            chosen_coins = [closest_coin]
            available_coins = change_coins
            available_coins.remove(*chosen_coins)

            max_iteration = len(available_coins)*5//2
            if max_iteration > 5:  max_iteration = 5

            for i in range(max_iteration):
                coins = iterate_these_available_coins_reversed(total_out, available_coins, chosen_coins, n_outputs)
                if not isinstance(coins, bool) and not isinstance(coins[0], bool):
                    return coins
                available_coins = coins[ 1]
                chosen_coins = coins[2]
            return False
            
def iterate_these_available_coins(total_out, available_coins, chosen_coins, n_outputs,min_fee_per_byte=70):
    available_coins_copy = copy.deepcopy(available_coins)
    
    for i in range( 1, len(available_coins) ):

        min_estimated_fee = ((len(chosen_coins)+1)*146 + n_outputs*34 + 20)*min_fee_per_byte
        max_estimated_fee = min_estimated_fee*2 + 546

        total_chosen_coins = sum([x[2] for x in chosen_coins])
        
        total_available = sum([x[2] for x in available_coins])
        if total_available + total_chosen_coins < (len(available_coins)*146 + n_outputs*34 + 20)*min_fee_per_byte + total_out:
            return False, available_coins_copy, chosen_coins, n_outputs


        for index,coin in enumerate(available_coins):
            total = total_chosen_coins + coin[2]

            if  total > total_out + max_estimated_fee: 
                #It doesn't matter what iteration we are in. If we hit a result greater than the max
                #for an exact change in the first index, it means we can't build it like this, because
                #we are dealing with the smallest coin.
                if index == 0: 
                    if len(chosen_coins)>1:
                        chosen_coins.remove(chosen_coins[0])
                        chosen_coins = [x for x in chosen_coins if x > available_coins_copy[-1]] 
                        if len(chosen_coins)==0:
                            chosen_coins = [available_coins_copy[-1]]
                            available_coins_copy.remove(available_coins_copy[-1])
                    else:
                        chosen_coins = [available_coins_copy[-1]]
                        available_coins_copy.remove(available_coins[-1])
                    return False, available_coins_copy, chosen_coins, n_outputs
                else: 
                    chosen_coins.append(available_coins[index-1])
                    available_coins.remove(available_coins[index-1])
                    break


            elif total >= total_out + min_estimated_fee: 
                chosen_coins.append(coin)
                return chosen_coins
            
    try:    
        chosen_coins.append(available_coins_copy[-1])
        available_coins_copy.remove(available_coins[-1])
    except: pass
    min_estimated_fee = ((len(chosen_coins)+1)*146 + n_outputs*34 + 20)*min_fee_per_byte
    max_estimated_fee = min_estimated_fee*2 + 546
    total = sum([x[2] for x in chosen_coins])
    if total >= total_out + min_estimated_fee and total <= total_out + max_estimated_fee: 
        return chosen_coins
            
        
    #chosen_coins= available_coins_copy[-1]
    #available_coins_copy.remove(available_coins[-1])
    print(f"made it to the end. chosen_coins: {chosen_coins}, available_coins_copy: {available_coins_copy}")
    return False, available_coins_copy, chosen_coins, n_outputs

def iterate_these_available_coins_reversed(total_out, available_coins, chosen_coins, n_outputs,min_fee_per_byte=70):
    #we reverse the sorting of the available coins.
    available_coins.sort( key=lambda x:x[2], reverse = True) 
    available_coins_copy = copy.deepcopy(available_coins)
    
    for i in range( 1, len(available_coins) ):

        min_estimated_fee = ((len(chosen_coins)+1)*146 + n_outputs*34 + 20)*min_fee_per_byte
        max_estimated_fee = min_estimated_fee*2 + 546

        total_chosen_coins = sum([x[2] for x in chosen_coins])
        
        total_available = sum([x[2] for x in available_coins])
        if total_available + total_chosen_coins < (len(available_coins)*146 + len(chosen_coins)*146 
                                                   + n_outputs*34 + 20)*min_fee_per_byte + total_out:
            return False, available_coins_copy, chosen_coins, n_outputs
        
        for index,coin in enumerate(available_coins):
            
            min_estimated_fee = ((len(chosen_coins)+1)*146 + n_outputs*34 + 20)*min_fee_per_byte
            max_estimated_fee = min_estimated_fee*2 + 546

            total_chosen_coins = sum([x[2] for x in chosen_coins])

            total = total_chosen_coins + coin[2]

            if  total > total_out + max_estimated_fee: 
                #It doesn't matter what iteration we are in. If we hit a result greater than the max
                #for an exact change in the first index, it means we can't build it like this.
                
                if len(chosen_coins)>1:
                    chosen_coins.append(coin)
                    available_coins.remove(coin)
                    total_remaining_available = sum([x[2] for x in available_coins])
                
                    min_balance=((len(chosen_coins)+1+len(available_coins))*146+n_outputs*34+20)*min_fee_per_byte-total_out
                    
                    #we check that we will still have money for next iterations
                    diff = total_chosen_coins + total_remaining_available - min_balance
                    
                    
                    if diff < 0:
                        #maybe the problem is the biggest coins in the chosen coins:
                        return False, available_coins_copy, chosen_coins, n_outputs
                    
                    #Let's see if by just taking one coin off we can make it:
                    
                    #First let's see if it is our biggest coins what causes the problem:
                    available_coins.sort( key=lambda x:x[2], reverse = False) 
                    total_chosen_coins = sum([x[2] for x in chosen_coins])
                    for chosen_coin in chosen_coins:
                        excedent = total - total_out - max_estimated_fee
                        diff = excedent - chosen_coin[2] 
                        fee_gap =  min_estimated_fee - max_estimated_fee
                        if diff > fee_gap:
                            if diff < 0:
                                chosen_coins.remove(chosen_coin)
                                return chosen_coins
                        #This means that taking out the chose coin is too much, so let's try to add a small coin
                        else:
                            chosen_coins_copy = copy.deepcopy(chosen_coins)
                            chosen_coins_copy.remove(chosen_coin)
                            available_coins.sort( key=lambda x:x[2], reverse = False) 
                            
                            coins = iterate_these_available_coins(total_out, available_coins, chosen_coins_copy, n_outputs)
                            if not isinstance(coins, bool) and not isinstance(coins[0], bool):
                                return coins
                            available_coins.sort( key=lambda x:x[2], reverse = True)
                            chosen_coins.sort( key=lambda x:x[2], reverse = True)
                else:
                    chosen_coins = [coin]
                    available_coins.remove(coin)
                
                return False, available_coins, chosen_coins, n_outputs
            
            elif total >= total_out + min_estimated_fee: 
                chosen_coins.append(coin)
                return chosen_coins
            
            chosen_coins.append(coin)
            available_coins.remove(coin)

    #print(f"made it to the end. chosen_coins: {chosen_coins}, available_coins_copy: {available_coins_copy}")
    return False, available_coins, chosen_coins, n_outputs       
  
def select_coins_to_hide_change(utxos, total_out,n_outputs,min_fee_per_byte=70):
    #we will create a fake total output which is going to be the avarage of the output
    if n_outputs==1: 
        avg = total_out
        fake_total_out=2*total_out
    else:
        avg = total_out//n_outputs
        fake_total_out = total_out + avg
        
    total_utxos = sum([x[2] for x in utxos])
    print(f"avg: {avg}, fake_total_out: {fake_total_out}, total_utxos: {total_utxos}")
    
    
    min_estimated_fee = (len(utxos)*146 + (n_outputs+1)*34 + 20)*min_fee_per_byte
    max_estimated_fee = min_estimated_fee*2 + 546 
    
    if total_utxos < fake_total_out + min_estimated_fee: return False
    
    #First we check if the utxos --as they are-- can do it:
    #we check first if the utxos are too big, and if they are, if it is acceptable:
    if total_utxos > fake_total_out + max_estimated_fee:
        print(f"total_utxos is greater")
        if total_utxos - (fake_total_out + max_estimated_fee) < avg*0.75:
            print(f"but... less than avg*1.75")
            return utxos
    #If they are not too big then they are not enough, in which case we will cease trying:
    elif total_utxos < fake_total_out + min_estimated_fee:
        print(f"total_utxos is less")
        if (fake_total_out + min_estimated_fee) - total_utxos > avg*0.8:
            print(f"but... greater than avg*.8")
            return utxos
        else: return False
        
    #if not, we will have to start playing with the utxo set:
    #we know now that the utxo is greater than the fake output. So we have to shrink it.
    #Let's see first if a single utxo can make it:
    min_estimated_fee = (146 + (n_outputs+1)*34 + 20)*min_fee_per_byte
    max_estimated_fee = min_estimated_fee*2 + 546 
    
    candidates = [x for x in utxos  if  x[2]> min_estimated_fee + fake_total_out - avg*0.2 \
                  and x[2]< max_estimated_fee + fake_total_out + avg*0.75]
    if len(candidates)>0: return [min(candidates,key=lambda x:x[2])]
    
    #if not, then we proceed playing with the utxos:
    candidates = [x for x in utxos  if  x[2]< max_estimated_fee + fake_total_out + avg*0.75]
    
    candidates.sort( key=lambda x:x[2], reverse = False)
    if candidates[-1][2]<fake_total_out*0.8:candidates.sort( key=lambda x:x[2], reverse = True)
    
    for i,candidate in enumerate(candidates):
        print(f"i,candidate : {i}, {candidate}")
        min_estimated_fee = ((len(candidates)-1)*146 + (n_outputs+1)*34 + 20)*min_fee_per_byte
        max_estimated_fee = min_estimated_fee*2 + 546 
        
        total_candidates = sum([x[2] for x in candidates])
        
        test_total = total_candidates - candidate[2]
        print(f"test_total : {test_total}")
        if test_total > fake_total_out + max_estimated_fee + avg*0.75:
            
            diff = test_total - (fake_total_out + max_estimated_fee + avg*0.75)
            print(f"diff : {diff}")
            if diff <  candidates[i+1][2]:
                print(f"candidates[i+1] {candidates[i+1]}")
                if diff < candidates[i+1][2] + candidates[i+2][2] :
                    print(f"candidates[i+1] + candidates[i+2]  {candidates[i+1] + candidates[i+2] }")
                    if diff < candidates[i+1][2] + candidates[i+2][2] + candidates[i+3][2]:
                        print(f"3  {candidates[i+1][2] + candidates[i+2][2] + candidates[i+3][2]}")
                        if diff < candidates[i+1][2] + candidates[i+2][2] + candidates[i+3] + candidates[i+4][2]: pass
                        else:
                            for j in range(1,5): candidates.remove(candidates[i+j])
                            return candidates
                    else:
                        for j in range(1,4): candidates.remove(candidates[i+j])
                        return candidates
                else:
                    for j in range(1,3): candidates.remove(candidates[i+j])
                    return candidates
            else:
                for j in range(1,2): candidates.remove(candidates[i+j])
                return candidates
        elif  test_total > fake_total_out + min_estimated_fee - avg*0.2: 
            candidates.remove(candidates[i])
            return candidates
    return False
            
def naive_coin_selection(utxos, total_out,n_outputs,min_fee_per_byte=70):
    
    total_utxos = sum([x[2] for x in utxos])
    min_estimated_fee = (len(utxos)*146 + (n_outputs+1)*34 + 20)*min_fee_per_byte
    if total_utxos < total_out + min_estimated_fee: return False
    
    coins = []
    utxo_total = 0
    for utxo in utxos:
        coins.append(utxo)
        utxo_total += utxo[2]
        min_estimated_fee = (len(coins)*146 + (n_outputs+1)*34 + 20)*min_fee_per_byte
        max_estimated_fee = min_estimated_fee*2 + 546 
        if utxo_total > total_out + min_estimated_fee: break
    
    if utxo_total > total_out + max_estimated_fee + 146*min_fee_per_byte:
        change = utxo_total - total_out - (min_estimated_fee + 146*2)
        return {"utxos":coins, "fee":min_estimated_fee + 146*2,"change":change}
    else: 
        print("NO change")
        fee = utxo_total - total_out
        return {"utxos":coins, "fee":fee,"change":False}
     
        
def coin_selector(utxos, total_out, n_outputs, min_fee_per_byte=70):
    #first let's try to get an exact change:
    coins = select_coins_by_exact_match(utxos, total_out, n_outputs,min_fee_per_byte)
    
    if not isinstance(coins,bool):
        print("found exact match")
        total_coins = sum([x[2] for x in coins])
        fee = total_coins - total_out
        return {"utxos":coins, "fee":fee,"change":False}
    
    print(f"utxos {utxos}\ntotal_out {total_out}\nn_outputs{n_outputs}")
    coins = select_coins_to_hide_change(utxos, total_out, n_outputs,min_fee_per_byte)
    if not isinstance(coins,bool):
        print("created tx with hidden change.")
        #fee will be the minimum plus the dust fee
        fee = (len(coins)*146 + (n_outputs+1)*34 + 20)*min_fee_per_byte + 546
        total_coins = sum([x[2] for x in coins])
        change = total_coins - total_out - fee
        return {"utxos":coins, "fee":fee,"change":change}
    
    coins = naive_coin_selection(utxos, total_out, n_outputs,min_fee_per_byte)  
    if not isinstance(coins,bool):
        print("naive selection necessary.")
        return coins
    return {"utxos":"Not enough money", "fee":0,"change":False}