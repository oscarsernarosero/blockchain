from corporate_wallets import CorporateSuperWallet, ManagerWallet, SHDSafeWallet

words = "client sudden sunset borrow pupil rely sand girl prefer movie bachelor guilt giraffe glove much strong dizzy switch ill silent goddess crumble goat power"
manager2 = ManagerWallet.recover_from_words(words,entropy=256,passphrase="RobertPaulson",testnet=True)

invite = {'public_key_list': [b"\x02\x17n\x0c\xfd\x84]'\xce\x83)\x1fC\x1d\xda3s\x8f\xcf \x96\xa6\xf3\xf7\xc4\xab\xde\xb3p\x08\xed\xe6}", b'\x02\x1bP\xbbp\x89\xe5\xa2Q\x12\x1cp\x19\x03\xcd+\xc6Oa\xc7\x1a#\xaf\xcf$G\xa4\xed\x8bY\xa1\x14+'], 'm': 2, 'n': 3, 'addr_type': 'p2wsh', 'master_pubkey': "tpubDDPhf39HYJ34itcntagMVucwfUzvf6npJHGBMBuDaoUjyEeVFgvzgi8FbuQnRdMzMDd81kiqs7zcsGQRFC3B75QQQbVbtUM5cqnr7gWuqdf", 'testnet': 1, 'segwit': 1, 'level1pubkeys': [b'\x02\x1bP\xbbp\x89\xe5\xa2Q\x12\x1cp\x19\x03\xcd+\xc6Oa\xc7\x1a#\xaf\xcf$G\xa4\xed\x8bY\xa1\x14+']}


store_safev2 = manager2.accept_invite(invite, "Buenos Aires Manager2v3")

nov_21_safe = store_safev2.get_daily_safe_wallet(201124)
res = nov_21_safe.open_partial_tx("c7189863e4bbb304f0236710b7c477546d2e454e39d49ef24438510cdc837a7c")