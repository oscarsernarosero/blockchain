from corporate_wallets import CorporateSuperWallet, ManagerWallet, SHDSafeWallet

words = "engine over neglect science fatigue dawn axis parent mind man escape era goose border invest slab relax bind desert hurry useless lonely frozen morning"
Roosevelt = CorporateSuperWallet.recover_from_words(words, 256, "RobertPauslon",True)



invite = {'name': 'test 2', 'master_pubkey_list': ["tpubDDPhf39HYJ34neDTEPjyoYVSKKEoVAmEZmP1oGW7tW5gTD8Cb1abfw8rmgUUvnHp2Fr9Rjrmpk7DpwkDFBtDnAPkgVG5VbNp1xpZ7awW3Q4", "tpubDDPhyYJTpHbymUXyKP8BgWzymtKuoTxeykgo737WPk2JAYhT4NPYCaWzCuRrbf5k6voucxuMr8Q8YivHz3F1ibTPM3AmzAsy7GaxozxXBry", "tpubDCYEqvE5F87BQzZovqjWAtH1xo2ViiqBLCEEkWqd5zN2UBfHo2qKL1UTw1vawzyRffohXZn5tdgxGXJu1MzNHBfoByCm9YotHswF8uQ8qyq"], 'm': 2, 'n': 3, 'addr_type': 'p2wsh', 'testnet': 1, 'segwit': 1}


corp_wallet = Roosevelt.accept_corporate_safe_invite(invite)

year_wallet = corp_wallet.get_year_wallet(2020)
res = year_wallet.open_partial_tx("83da3ea8853eeb22c247e08ed81cc9d7aa9f0db06ad274588832c42f7c6c7715")