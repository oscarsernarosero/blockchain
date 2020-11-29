import kivy
kivy.require('1.11.1') # replace with your current kivy version !
from wallet import Wallet
from corporate_wallets import CorporateSuperWallet, StoreWallet, ManagerWallet, SHDSafeWallet, HDMWallet
from wallet_database_sqlite3 import Sqlite3Wallet, Sqlite3Environment
import qrcode
from urllib.request import Request, urlopen
import json
import os
import pyperclip
import time, threading
from datetime import date, timedelta
from abc import ABCMeta, abstractmethod
import calendar
import operator

from kivy.core.clipboard import Clipboard 
from kivy.clock import Clock
from kivy.base import EventLoop
from  kivy.uix.camera import Camera
from kivy_garden.zbarcam import ZBarCam

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty,BooleanProperty, ObjectProperty, NumericProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
import kivy.input.motionevent 
from kivy.config import Config 
from kivy.core.window import Window
from functools import partial


def store_wallet(app, rv, index, _wallet):
    app.wallets[0].update({f"{rv.data[index]['text']}": _wallet})
    app.current_wallet = rv.data[index]['text']
    print(f"self.app.wallets[0]: {app.wallets[0]}, current: {app.current_wallet}")


class Balance():
    
    def update_real_balance(self):
        self.loading = LoadingPopup("Now consulting the blockchain..\n\nUpdating the database...\n\
        \nThis might take a few\nmore seconds...\nPlease wait.")
        self.loadingDB = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingDB.open()
        mythread = threading.Thread(target=self.update_real_balance_process)
        mythread.start()
    
    def update_real_balance_process(self):
        
        print(f"update_balance_process:\napp.wallets {self.app.wallets}, current wallet: {self.app.current_wallet}")
        
        #self.my_wallet.start_conn()
                                
        try:                        
            self.my_wallet.update_balance()  
            print("Database up to date. Updating information on display...")
            self.loadingDB.dismiss()

            self.update_balance()
        except Exception as e:
            print("update balance exception")
            if str(e).startswith("('Status Code 429'"):
                #TRIGGER THE "WRONG INPUT POPUP"
                self.exception_popup = GenericOkPopup("Too many requests in the\npast hour.\nTry again later.")
                self.notEnoughFundsWindow = Popup(title="Server Error", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingDB.dismiss()

                self.update_balance()                  
        
    def update_balance(self):
        #Creating the loading screen
        self.loading = LoadingPopup("Consulting the\ndatabase\nand Bitcoin's price...\n\nAlmost done.\nPlease wait.")
        self.loadingBalance = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingBalance.open()
        mythread = threading.Thread(target=self.update_balance_process)
        mythread.start()
        
    def update_balance_process(self):
        env = Sqlite3Environment()
        api_key = env.get_key("CC_API")[0][0]
        env.close_database()
        url = f"https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD"
        raw_data = self.read_json(url)
        btc_price = raw_data["USD"]
        
        print(f"update_balance_process:\napp.wallets {self.app.wallets}, current wallet: {self.app.current_wallet}")
        
        self.my_wallet.start_conn()
        self.btc_balance = self.my_wallet.get_balance()/100000000
        print(f"balance: {self.btc_balance}")
        #self.btc_balance = app.btc_balance/100000000
        self.usd_balance = self.btc_balance * btc_price
        self.btc_balance_text =  str(self.btc_balance) + " BTC"
        self.usd_balance_text = "{:10.2f}".format(self.usd_balance) + " USD"
        
        print("closing loading window")
        self.loadingBalance.dismiss()
        self.my_wallet.close_conn()
        
    def read_json(self,url):
        request = Request(url)
        response = urlopen(request)
        data = response.read()
        url2 = json.loads(data)
        return url2
        
        
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''
    def on_leave(self):
        self.selected = False

class SelectRV(RecycleDataViewBehavior, Label):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectRV, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectRV, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        self.app = App.get_running_app()
        if is_selected: self.if_selected( rv, index)
        else: print("selection removed for {0}".format(rv.data[index]))
    
    @abstractmethod
    def if_selected(self,rv, index):
        pass
            
class SelectWallet(SelectRV):
    
    def if_selected(self,rv, index):
        """
        This method is the one that implements the behaviour of a recycleview item when selected.
        """
        print("selection changed to {0}".format(rv.data[index]))
        if "You don't have" in rv.data[index]["text"]: return
        

        words = self.app.db.get_words_from_wallet(rv.data[index]["text"])
        #the result of the query will come in the form [(result,)]. Therefore, we  
        #will select the datum in result[0][0].
        print(f"words from db: {words[0][0]}")
        _wallet = Wallet.recover_from_words(mnemonic_list=words[0][0],testnet = True)
        
        store_wallet(self.app, rv, index, _wallet)
        
        Clock.schedule_once(self.go_to_wallet_type, 0.7)  

                                
    def go_to_main(self,obj):
        self.selected = False
        self.app.sm.current = "Main"
        
    def go_to_wallet_type(self,obj):
        self.selected = False
        self.app.sm.current = "WalletType"
        

class SelectDay(SelectRV):

    def if_selected(self, rv, index):
        print("selection changed to {0}".format(rv.data[index]))
        if "You don't have" in rv.data[index]["text"]: return
        _wallet = SHDSafeWallet.from_database(rv.data[index]["text"])
        
        store_wallet(self.app, rv, index, _wallet)
        
        Clock.schedule_once(self.go_to_day, 0.7)  

            
    def go_to_day(self,obj):
        self.selected = False
        self.app.sm.current = "DayScreen"
        
            
class SelectWeek(SelectRV):
    
    def if_selected(self, rv, index):
        print("selection changed to {0}".format(rv.data[index]))
        if "You don't have" in rv.data[index]["text"]: return
        _wallet = SHDSafeWallet.from_database(rv.data[index]["text"])
        
        store_wallet(self.app, rv, index, _wallet)
        
        Clock.schedule_once(self.go_to_week_safe, 0.7)  
            
    def go_to_week_safe(self,obj):
        self.selected = False
        self.app.sm.current = "WeekSafeScreen"  
                          
class SelectStore(SelectRV):

    def if_selected(self, rv, index):
        print("selection changed to {0}".format(rv.data[index]))
        if "You don't have" in rv.data[index]["text"]: 
            self.selected = False
            return
        #We recreate the wallet with the info stored in the database and save it in the variable _wallet.
        _wallet = SHDSafeWallet.from_database(rv.data[index]["text"])

        store_wallet(self.app, rv, index, _wallet)

        Clock.schedule_once(self.go_to_year, 0.7)  
        
            
    def go_to_year(self,obj):
        self.selected = False
        self.app.sm.current = "StoreSafesScreen" 
        
        
class SelectYear(SelectRV):

    def if_selected(self, rv, index):
        if "You don't have" in rv.data[index]["text"]: return
        Clock.schedule_once(self.go_to_year, 0.7)  

            
    def go_to_year(self,obj):
        self.selected = False
        self.app.sm.current = "CorporateScreen"   
        
        
class SelectAccount(SelectRV):

    def if_selected(self, rv, index):
        if "You don't have" in rv.data[index]["text"]: return
        Clock.schedule_once(self.go_to_store, 0.7)  

            
    def go_to_store(self,obj):
        self.selected = False
        self.app.sm.current = "StoreSafesScreen"   

class SelectPayment(SelectRV):

    def if_selected(self, rv, index):
        if "You don't have" in rv.data[index]["text"]: return
        Clock.schedule_once(self.go_to_store, 0.7)  
                                
            
    def go_to_store(self,obj): 
        self.selected = False
        
class SelectContact(SelectRV):

    def if_selected(self, rv, index):
        if "You don't have" in rv.data[index]["text"]: return
        contact_xpub = rv.data[index]["xpub"]
        print(f"self.app.caller: {self.app.caller}")
        print(f"self.app.last_caller: {self.app.last_caller}")

        if self.app.caller == "MyContactsScreen" and self.app.last_caller == "NewStoreSafeScreen":
            print("in first if")
            contact = self.app.db.get_contact(contact_xpub)
            current_contact = self.app.arguments[0]["new_wallet_consigners"]["current"]
            self.app.arguments[0]["new_wallet_consigners"].update({current_contact:contact})
            Clock.schedule_once(self.go_back, 0.7) 

        elif self.app.caller == "MyContactsScreen" or self.app.caller == "YearList":
            self.app.arguments[0].update({"current_contact":contact_xpub})
            Clock.schedule_once(self.see_contact, 0.7) 
                
            
    def go_back(self,obj):
        self.selected = False
        self.app.sm.current = self.app.last_caller 
        
    def see_contact(self,obj):
        self.selected = False
        self.app.sm.current = "ContactInfoScreen"
        
        
class WalletScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        my_wallet_names = self.app.my_wallet_names
        no_wallet_msg ="You don't have any wallet yet.\nLet's start by creating one.\n\nPress the '+' button." 
        if len(my_wallet_names)>0:
            self.ids.rv.data = [{'text': str(x[1])} for x in my_wallet_names]
        else:
            self.ids.rv.data = [{'text': no_wallet_msg}]

    def new_wallet(self):
        self.new_wallet_popup = NewWalletPopup()
        self.newWalletWindow = Popup(title="New Wallet", content=self.new_wallet_popup, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.6}
                           )
        self.newWalletWindow.open()
        self.new_wallet_popup.ids.button.bind(on_release=self.create_wallet)
        
    def create_wallet(self,button):
        my_wallet_names = self.app.my_wallet_names
        name = self.new_wallet_popup.ids.wallet_name.text
        my_wallet = Wallet.generate_random(testnet=True)
        self.app.db.new_wallet(my_wallet.xtended_key, str(my_wallet.words)[1:], name)
        my_wallet_names.append((my_wallet.xtended_key, name, str(my_wallet.words)[1:]))
        self.ids.rv.data = [{'text': x[1]} for x in my_wallet_names]
        self.newWalletWindow.dismiss()
        
    
        
class MainScreen(Screen,Balance):
    btc_balance = NumericProperty()
    usd_balance = 0.0
    
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
        
        if self.app.current_wallet is not None:
            self.my_wallet = self.app.wallets[0][self.app.current_wallet]
            self.update_balance()
        
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    font_size = "20sp"
    

class WalletTypeScreen(Screen):
    
    public_key = StringProperty()
    
    def on_pre_enter(self):
        self.app = App.get_running_app() 
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        
        if isinstance( my_wallet, SHDSafeWallet) or isinstance( my_wallet, HDMWallet):
            print("wallet is not a Wallet")
            self.app.current_wallet = my_wallet.parent_name
            if self.app.current_wallet is None: self.app.current_wallet = self.app.last_wallet
            print(f"app.current_wallet {self.app.current_wallet}")
            my_wallet = self.app.wallets[0][self.app.current_wallet]
            
        print(f"my_wallet class: {type(my_wallet)}")   
        my_wallet.start_conn()
        self.public_key = str(my_wallet.xtended_public_key)
        
    def go_back(self):
        self.app.sm.current = self.app.caller
        
    def on_leave(self):
        self.app.last_wallet = self.app.current_wallet
        
class StoreListScreen(Screen):
    font_size = "20sp"
    total= StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__()
        
            
    def on_pre_enter(self):
        self.total = "A lot"
        self.app = App.get_running_app()
        print(f"StoreListScreen app.current_wallet: {self.app.current_wallet}")
        store_list = self.app.db.get_all_store_wallets()
        data = [x[0] for x in store_list if x[10]==self.app.current_wallet and x[11] == -1 and x[12] != "None"]
        print(f"data {data}")
        no_wallet_msg ="You don't have any stores added yet." 
        if len(data)>0:
            self.ids.store_list.data = [{'text': x} for x in data]
        else:
            self.ids.store_list.data = [{'text': no_wallet_msg}]
        self.app.caller = "StoreList"
        
    def go_back(self):
        self.app.sm.current = self.app.caller
        
    def on_leave(self):
        self.app.caller = "StoreList"
        
        
class StoreSafesScreen(Screen):
    font_size = "20sp"
    font_total_size = "30sp"
    font_label_size = "15sp"
    total= StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__()
        
            
    def on_pre_enter(self):
        self.total = "A lot"
        self.app = App.get_running_app()
        print(f"StoreSafes app.current_wallet: {self.app.current_wallet}")
        #Let's retreive the daily safes from the database.
        daily_safes = self.app.db.get_daily_safe_wallets(self.app.current_wallet)  
        #Let's get the names of them
        full_names = [x[0] for x in daily_safes]
        print(full_names)
        daily_safe_date = {}
        #Now let's filter them to only the ones from 2 weeks ago until tododay
        for full_name in full_names: 
            date_str,name = full_name.split("_")
            monthday,of,year = date_str.split("-")
            wallet_date = date(int("20"+year),list(calendar.month_abbr).index(monthday[:3]),int(monthday[-2:]))
            daily_safe_date.update({f"{full_name}":wallet_date})
        
        print(daily_safe_date)
        today = date.today()
        two_weeks_ago = today - timedelta(days=14)
        filtered_daily_safes = [key for key in daily_safe_date if \
                                daily_safe_date[key] > two_weeks_ago  and  daily_safe_date[key] < today]
        
        #Now let's do the same with the week safes
        weekly_safes = self.app.db.get_weekly_safe_wallets(self.app.current_wallet)
        print(f"weekly_safes: {weekly_safes}")
        full_names = [x[0] for x in weekly_safes]
        print(full_names)
        week_safe_dates = {}
        #Now let's filter them to only the ones from 8 weeks ago until tododay
        for full_name in full_names: 
            week_number,name = full_name.split("_")
            week,week_n,of,year = week_number.split("-")
            wallet_date = date.fromisocalendar(int("20"+year),int(week_n),1)#This will be available with python 3.8
            week_safe_dates.update({f"{full_name}":wallet_date})
            print(wallet_date)
            
        eight_weeks_ago = today - timedelta(days=56)
        filtered_weekly_safes = [key for key in week_safe_dates if \
                                week_safe_dates[key] > eight_weeks_ago  and  week_safe_dates[key] < today]
        


        no_wallet_msg ="You don't have any stores added yet." 
        
        if len(filtered_daily_safes)>0: self.ids.daysafe_list.data = [{'text': x} for x in filtered_daily_safes]
        else:  self.ids.daysafe_list.data = [{'text': no_wallet_msg}]
            
        if len(filtered_weekly_safes)>0: self.ids.weeksafe_list.data = [{'text': x} for x in filtered_weekly_safes]   
        else: self.ids.weeksafe_list.data = [{'text': no_wallet_msg}]
        
    def go_back(self):
        self.app.sm.current = self.app.caller
        
    def new_weekly_safe(self):
        self.show = NewSafePopup("weekly")
        self.popupWindow = Popup(title="Create New Week Safe", content=self.show, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.5}
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        self.show.current.bind(on_release=partial(self.new_safe,when="this_week"))
        self.show.past.bind(on_release=partial(self.new_safe,when="last_week"))
        self.show.other.bind(on_release=partial(self.custom_safe,when="1111"))
        
        
    def new_daily_safe(self):
        self.show = NewSafePopup("daily")
        self.popupWindow = Popup(title="Create New Week Safe", content=self.show, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.5}
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        self.show.current.bind(on_release=partial(self.new_safe,when="today"))
        self.show.past.bind(on_release=partial(self.new_safe,when="yesterday"))
        self.show.other.bind(on_release=partial(self.custom_safe,when="1111"))
        
    def new_safe(self,*args, **kargs):
        print(f"args: {args}, kargs {kargs}")
        master_safe = self.app.wallets[0][self.app.current_wallet]
        #master_safe.start_conn() #maybe uncomment this
        
        if kargs["when"] == "today" or kargs["when"] == "this_week": index = None
        
        elif kargs["when"] == "yesterday":
            yesterday = date.today() - timedelta(days=1)
            index_string = str(yesterday.year)[2:]+'{:02d}'.format(yesterday.month)+'{:02d}'.format(yesterday.day)
            index = int(index_string)
            
        elif kargs["when"] == "last_week":
            this_week = datetime.datetime.now().isocalendar()
            index_string = str(this_week[0])[2:]+str(this_week[1])
            index = int(index_string)
            
        else: raise Exception(f"new_safe takes only one argument 'when' and it can only be 1 out of 4 options\
        : 'today', 'yesterday', 'this_week', or 'last_week'. Not {kargs['when']}")
        
        print(f"master_safe: {master_safe}\nindex: {index}")
        if kargs["when"] == "today" or kargs["when"] == "yesterday": master_safe.get_daily_safe_wallet(index)
        else: master_safe.get_weekly_safe_wallet(index)
        
        self.app.sm.current = "DaySafeScreen"
        
        
    def custom_safe(self,*args, **kargs):
        print("custom_safe")
    
    def on_leave(self):
        self.app.last_wallet = self.app.current_wallet
        
    def go_back(self):
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        
        
        if isinstance( my_wallet, SHDSafeWallet) or isinstance( my_wallet, HDMWallet):
            self.app.current_wallet = my_wallet.parent_name
            my_wallet = self.app.wallets[0][self.app.current_wallet]
            
        #app.current_wallet = app.last_wallet
        self.app.sm.current = "StoreList"
        
        
    def share(self):
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        msg = str(my_wallet.share())
        print(msg)
        self.share_ = GenericOkPopup(msg)
        self.share_window = Popup(title="Share Wallet", content=self.share_, 
                                                  size_hint=(None,None),size=(500,1000), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
        self.share_window.open()
        self.share_.OK.bind(on_release=self.share_window.dismiss) 
        return
    
    def whoshere(self):
        self.app.sm.current = "WhosHereScreen"

        
class WhosHereScreen(Screen):
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
        wallet = self.app.wallets[0][self.app.current_wallet]
        self.ids.wallet_name.text = self.app.current_wallet
        data = []
        level1pubkeys = wallet.level1pubkeys
        for pubkey in wallet.public_key_list:
            contact = self.app.db.get_contact_by_store_safe_pubkey( str( int.from_bytes(pubkey,"big") ) )
            print(contact)
            if contact[-1] in level1pubkeys: 
                print(f"contact {contact} is a Level1")
                contact.append("Day-Safe Only")
            else: contact.append("All Accesss")
            data.append(contact)
            
        participant_list = self.ids.participant_list
        spacer = self.ids.spacer
        for contact in data:
                print(contact)
                participant = Participant(contact[0][0]+" "+contact[0][1],contact[1])
                participant_list.add_widget(participant)
        
        n_ = len(wallet.public_key_list)
        if n_<6: 
            participant_list.size_hint_y = n_
            spacer.size_hint_y = 5.1 - n_
        else: 
            participant_list.size_hint_y = 6
            spacer.size_hint_y = 0.1
        
        return  
    
    def go_back(self):
        self.app.sm.current = "StoreSafesScreen"
           
            
            
            
            
    
class YearListScreen(Screen):
    font_size = "15sp"
    
    def __init__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        year_list = [2020,2019]
        no_data_msg ="You don't have any year accounts yet." 
        if len(year_list)>0:
            self.ids.year_list.data = [{'text': str(x)} for x in year_list]
        else:
            self.ids.year_list.data = [{'text': no_data_msg}]
            
    def go_back(self):
        self.app.sm.current = self.app.caller
        
    def on_leave(self):
        self.app.caller = "YearList"
        
            
class CorporateScreen(Screen):
    font_size = "20sp"
    total= StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        account_list = ["Account 1","Account 2","Account 3","Account 5"]
        no_data_msg ="You don't have any accounts yet." 
        if len(account_list)>0:
            self.ids.account_list.data = [{'text': x} for x in account_list]
        else:
            self.ids.account_list.data = [{'text': no_data_msg}]
            
    def on_pre_enter(self):
        self.total = "A lot"
        
    def go_back(self):
        self.app.sm.current = self.app.caller
        
class CorporateTransferScreen(Screen):
    font_size = "20sp"
    
    def go_back(self):
        app = App.get_running_app()
        sm = app.sm
        sm.current = app.caller
    
class CorporateTransferFromAccountScreen(Screen):
    font_size = "20sp"
    
    def go_back(self):
        app = App.get_running_app()
        sm = app.sm
        sm.current = app.caller
    
    
class CorporateTransferAllScreen(Screen):
    font_size = "20sp"
    
    def go_back(self):
        app = App.get_running_app()
        sm = app.sm
        sm.current = app.caller
        
        

class DayScreen(Screen, Balance):
    font_size = "15sp"
    _address = "Your address here"
    
    btc_balance = NumericProperty(0)
    address = StringProperty(_address)
    usd_balance = 0.0
    
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
        self.my_wallet = self.app.wallets[0][self.app.current_wallet]
        
        #if self.app.current_wallet is not None:
        raw_address = self.app.db.get_day_deposit_addresses(self.app.current_wallet)
        print(raw_address)
        if len(raw_address) == 0: self.address = self.my_wallet.create_receiving_address()
        else: self.address = raw_address[0][0]
        self.update_real_balance()
        print(self.address)
        qrcode.make(self.address).save("images/QRdaily.png")
        
        self.ids.qr.reload()
        self.ids.title.text = self.app.current_wallet
        
    def transfer(self):
        self.app.current_wallet_balance = self.btc_balance_text
        print(f"self.btc_balance_text: {self.btc_balance_text}")
        self.app.last_caller = self.app.caller
        self.app.caller = "DayScreen"
        self.app.sm.current = "SafeTransferScreen"
        
    def copy(self):
        pyperclip.copy(self.ids.address_text.text)
   
    def go_back(self):
        self.app.current_wallet = self.my_wallet.parent_name
        print(f"\n\nfrom DaySafeScreen.go_back() app.current_wallet: {self.app.current_wallet} ")
        sm = self.app.sm
        sm.current = "StoreSafesScreen"

class NewContactScreen(Screen):
    font_size = "15sp"
    original_xpub = ""
    
    def on_pre_enter(self):    
        self.app = App.get_running_app()
        
        if self.app.caller == "ContactInfoScreen":
            
            first_name,last_name,phone_number,position,xpub,safe_pubkey=\
            self.app.db.get_contact(self.app.arguments[0]["current_contact"])[0]
            
            self.original_xpub = xpub
            self.ids.first_name.text = first_name
            self.ids.last_name.text = last_name 
            if phone_number is not None: self.ids.phone_number.text = phone_number
            else: self.ids.phone_number.text = ""
            self.ids.position.text = position
            self.ids.xpub.text = xpub 
            if safe_pubkey is not None: self.ids.safe_pubkey.text = safe_pubkey 
            else: self.ids.safe_pubkey.text = ""
            self.ids.title.text = "-- Edit Contact --"
            self.ids.go.text = "Save Changes"
    
    def add_contact(self):
        first_name = self.ids.first_name.text
        last_name = self.ids.last_name.text
        phone_number = self.ids.phone_number.text
        position = self.ids.position.text
        xpub = self.ids.xpub.text
        safe_pubkey = self.ids.safe_pubkey.text
        if self.app.caller != "ContactInfoScreen":
            self.app.db.new_contact(first_name, last_name, phone_number, position, xpub,safe_pubkey)
            self.app.sm.current = "YearList"
            
        else:
            self.app.db.update_contact(self.original_xpub,first_name, last_name, phone_number, position, xpub,safe_pubkey)
            self.app.arguments[0].update({"current_contact":xpub})
            self.app.sm.current = app.caller
            
    
    def go_back(self):
        self.app.sm.current = self.app.caller
        
class AddCosignerRow(BoxLayout):
    
    def __init__(self,cosigner_n, parent):
        super().__init__()
        self.name = self.ids.button.cosigner = self.ids.label.text = f"Cosigner {cosigner_n}"
        self.ids.button.bind(on_release=parent.add_cosigner)
        
class Participant(BoxLayout):
    
    def __init__(self,name, level):
        super().__init__()
        self.name = self.ids.name.text = name
        self.ids.level.text = level
    
    
class NewStoreSafeScreen(Screen):
    font_size = "15sp"
    font_size_cosigners = "11sp"
    consigners = {}
    
    def __init__(self,**kwargs):
        super().__init__()
        self.app = App.get_running_app()
        self.last_caller = "init"
        
    
    def add_cosigner(self,obj):
        self.app.arguments[0]["new_wallet_consigners"].update({"current":obj.cosigner})
        self.app.caller = "NewStoreSafeScreen"
        self.app.sm.current = "MyContactsScreen" 
        #self.app.sm.current = "LookUpContactScreen"  
        
        
    def on_pre_enter(self):
        
        if self.last_caller == "init": 
            self.last_caller = self.app.caller
            self.update_n("6")
            
        current_args = self.app.arguments[0]
        cosigners = current_args["new_wallet_consigners"]
        print(f"cosigners: {cosigners}")
        
        #we iterate the 'cosigners' selected
        for key in cosigners:
            print(f"key: {key}")
            #we skip if cosigner is "current" because this is just a helper
            if key == "current": continue
            cosigner_box = self.ids.cosigner_box
            #now we iterate through the boxes in the Layout
            for i,child in enumerate(cosigner_box.children):
                #We try to store the name of the box. If it hasn't been selected it would have no name. That's 
                #the reason for the try-except clause.
                try: name = child.name
                except:  continue
                
                #if we find the box that belongs to the cosigner, we proceed to change the text and color of the 
                #button by looking for the second ([1]) child of the box (the button) and setting the properties.
                if name == key:
                    cosigner_box.children[i].children[1].text = cosigners[key][0][0]+" "+cosigners[key][0][1]
                    cosigner_box.children[i].children[1].background_color = (0.3,0.6,1,1) 
            
            
    def create_store_safe(self):
        current_args = self.app.arguments[0]
        wallet = self.app.wallets[0][self.app.current_wallet]
        
        #wallet.start_conn()
        self.app.corporate_wallet = CorporateSuperWallet.recover_from_words(mnemonic_list=wallet.words,
                                                              passphrase=wallet.passphrase,
                                                              testnet = wallet.testnet)
        print(f"self.app.corporate_wallet: {self.app.corporate_wallet}")
        
        alias = self.ids.store_name.text
        if alias is None: raise Exception("Must provide a name/alias for the store")
        n = int(self.ids.n.text)
        m = int(self.ids.m.text)
        cosigners = current_args["new_wallet_consigners"]
        #we substract 1 from n since we are 1 of the cosigners, and we substract the "current" from the "cosigners"
        #variable. Since we have -1 on both sides of the "<", then they cancel each other.
        if len(cosigners)  < n: raise Exception("Not enough cosigners selected")
        pubkey_list = []
        for key in cosigners:
            if key == "current": continue
            pubkey_list.append(int(cosigners[key][0][5]).to_bytes(33,"big"))
        
        level1 = []
        for cosigner in self.ids.cosigner_box.children:
            print(cosigner.children)
            try: 
                checked = cosigner.children[0].active
                print(f"cosigner {cosigner.children[1].text} is active?: {checked}")
                if not checked: level1.append(int(cosigners[cosigner.name][0][5]).to_bytes(33,"big"))
            except: continue
        
        if len(level1) < 1 or len(level1) > len(pubkey_list)//2:
            raise Exception("Select at least 1 level1 manager, but not more than half of the total cosigners.")
        
        if n - len(level1) + 1 < m:raise Exception(f"There must be at least the same amount of cosigners availabel for the \
        week safe as 'm', but you only left {n - len(level1) + 1} cosigners available for the week safes.")
        
        print(f"alias {alias}, n {n}, pubkey_list {pubkey_list}")
            
        try:
            safe = SHDSafeWallet.from_master_privkey(alias,pubkey_list,
                                                master_privkey=wallet.get_child_from_path("m/44H/0H/1H"),
                                               n=n,m=m,testnet=wallet.testnet, parent_name=self.app.current_wallet,
                                                    level1pubkeys=level1)
        except: print("Could not create SHDSafeWallet.")
        
        #We clean the current arguments
        self.app.arguments[0]["new_wallet_consigners"] = {"current":""}
        self.go_back()
                                              
    
    def update_n(self,string_n):
        cosigner_box = self.ids.cosigner_box
        spacer = self.ids.spacer
        n = int(string_n)
        children = [child for child in cosigner_box.children]
        kids = len(children)
        if n < kids:
            for kid in range(kids - n):
                cosigner_box.remove_widget(children[ kid ])
                
        elif n > kids:
            for kid in range( n - kids):
                i = kids + kid 
                box = AddCosignerRow(i,self)
                cosigner_box.add_widget(box)
                
        if n<6: 
            cosigner_box.size_hint_y = n
            spacer.size_hint_y = 5.1 - (n-1)
        else: 
            cosigner_box.size_hint_y = 6
            spacer.size_hint_y = 0.1
                
    
    def go_back(self):
        print(self.last_caller)
        self.app.sm.current = "StoreList"
    

            
    
class MultiplePaymentScreen(Screen):
    font_size = "12sp"
    def __init__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        payment_list = ["Payment 1","Payment 2","Payment 3","Payment 5"]
        no_data_msg ="You don't have an payments yet." 
        if len(payment_list)>0:
            self.ids.payment_list.data = [{'text': x} for x in payment_list]
        else:
            self.ids.payment_list.data = [{'text': no_data_msg}]
    
    
class MyContactsScreen(Screen):
    font_size = "15sp"
    
    def __init__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        
        
    def on_pre_enter(self):   
        self.app.last_caller = self.app.caller
        self.app.caller = "MyContactsScreen"
        self.populate_contact_list()
            
    def update_result(self):
        search_for = self.ids.search.text
        self.populate_contact_list(search_for)
        
    def populate_contact_list(self,search_for=""):
        print(f"############   search_for: {search_for}")
        contact_list_raw = self.app.db.get_all_contacts()
        print(f"all contacts:\n{contact_list_raw}")
        contact_list=[]
        for x in contact_list_raw:
            if x[1].lower().startswith(search_for.lower()) or x[0].lower().startswith(search_for.lower()):
                space = " "
                for i in range(20 - len(x[1])-len(x[0])): space += " "
                contact_list.append(("[b]"+x[1]+" "+x[0]+ space +  "[color=002266]"+x[4][:6]+\
                              "...."+x[4][-5:]+"[/color][/b]", x[4]))
             
        no_data_msg ="No results found." 
        if len(contact_list)>0:
            self.ids.contact_list.data = [{'text': x[0],"xpub":x[1], "markup":True} for x in contact_list]
        else:
            self.ids.contact_list.data = [{'text': no_data_msg}]
       
    
    def select_contact(self):
        contact = self.ids.contact_list.data
        self.app.sm.current = app.caller
        
class ContactInfoScreen(Screen):
    font_size = "15sp"
    
    
    def on_pre_enter(self):   
        self.app = App.get_running_app()
        first_name,last_name,phone_number,position,xpub,safe_pubkey = \
        self.app.db.get_contact(self.app.arguments[0]["current_contact"])[0]
        
        self.ids.first_name.text = first_name
        self.ids.last_name.text = last_name 
        if phone_number is not None: self.ids.phone_number.text = phone_number
        else: self.ids.phone_number.text = ""
        self.ids.position.text = position
        self.ids.xpub.text = xpub 
        if safe_pubkey is not None: self.ids.safe_pubkey.text = safe_pubkey
        else: self.ids.safe_pubkey.text = ""
        self.app.caller = "ContactInfoScreen"
        
    def edit(self):
        self.app.sm.current = "NewContactScreen"
    
    def delete(self):
        self.app.db.delete_contact(self.app.arguments[0]["current_contact"])
        self.app.sm.current = "MyContactsScreen"
        
        
    
class ReceiveAccountScreen(Screen):
    font_size = "15sp"
    
    
class DaySafeScreen(Screen):
    font_size = "20sp"
    
    def __int__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
    
    def go_back(self):
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        
        self.app.current_wallet = my_wallet.parent_name
        print(f"\n\nfrom DaySafeScreen.go_back() self.app.current_wallet: {self.app.current_wallet} ")
        self.app.sm.current = self.app.caller
    
    def transfer(self):
        self.app.last_caller = self.app.caller
        self.app.caller = "DaySafeScreen"
        self.app.sm.current = "SafeTransferScreen"
    
class WeekSafeScreen(Screen,Balance):
    font_size = "20sp"
    _address = "Your address here"
    
    btc_balance = NumericProperty(0)
    address = StringProperty(_address)
    usd_balance = 0.0
    
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
        self.my_wallet = self.app.wallets[0][self.app.current_wallet]
        
        #get_day_deposit_addresses still works for week safes, so...
        raw_address = self.app.db.get_day_deposit_addresses(self.app.current_wallet)
        print(raw_address)
        if len(raw_address) == 0: self.address = self.my_wallet.create_receiving_address()
        else: self.address = raw_address[0][0]
        self.update_real_balance()
        print(self.address)
        qrcode.make(self.address).save("images/QRweekly.png")
        
        self.ids.qr.reload()
        self.ids.title.text = self.app.current_wallet
        
        
    def copy(self):
        pyperclip.copy(self.ids.address_text.text)
   
    
    def __int__(self, **kwargs):
        super().__init__()
        self.app = App.get_running_app()
        
    def go_back(self):
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        self.app.current_wallet = my_wallet.parent_name
        print(f"\n\nfrom WeekSafeScreen.go_back() self.app.current_wallet: {self.app.current_wallet} ")
        self.app.sm.current = "StoreSafesScreen"
        
    def transfer(self):
        self.app.current_wallet_balance = self.btc_balance_text
        print(f"self.btc_balance_text: {self.btc_balance_text}")
        self.app.last_caller = self.app.caller
        self.app.caller = "WeekSafeScreen"
        self.app.sm.current = "SafeTransferScreen"

    
class WeekSafeTransferScreen(Screen):
    font_size = "15sp"    
    
class Send():
    def paste(self):
        text_to_paste = pyperclip.paste()
        self.ids.address.text = text_to_paste
  
    def get_amount(self):
        #reading the inputs and 
        denomination = self.ids.denomination.text
        amount = None
        
        try: 
            amount = float(self.ids.amount.text)
            
        except: 
            #TRIGGER THE "WRONG INPUT POPUP"
            self.wrong_input = WrongInputPopup()
            self.wrongInputWindow = Popup(title="Not a valid amount", content=self.wrong_input, size_hint=(None,None), 
                                          size=(500,500), pos_hint={"center_x":0.5, "center_y":0.5})
            self.wrongInputWindow.open()
            self.wrong_input.OK.bind(on_release=self.wrongInputWindow.dismiss) 
            
        if denomination == "Bitcoins": amount = int(amount*100000000)
        else: amount = int(amount)
            
        self.confirm_popup(amount,denomination)
        return 
    
    def confirm_popup(self,amount):
        
        self.address = self.ids.address.text
        self.amount = amount
        
        self.show = ConfirmSendPopup(amount,self.address,"Satoshis")
        self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(500,500), 
                                 pos_hint={"center_x":0.5, "center_y":0.5}
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        self.show.YES.bind(on_release=self.start_sending)
        self.show.CANCEL.bind(on_release=self.popupWindow.dismiss)

                                
    def send_tx(self,screen, amount, address):
        "the button is the Button object"
        print(f"amount: {amount}, address: {address}")
        print("SENDING TX")
        app = App.get_running_app() 
        #my_wallet = app.my_wallet
        my_wallet = app.wallets[0][app.current_wallet]
        my_wallet.start_conn()
        transaction = my_wallet.send([(address,amount)])
        print(f"SENT SUCCESSFULLY. TX ID: {transaction[0].transaction.id()}")
        #closing popups
        self.loadingWindow.dismiss()
        self.popupWindow.dismiss()
        return transaction
        
        
    def start_sending(self,button):
        """
        Sends transaction, pops up a loading scree, cleans the inputs, and updates balances.
        """
        #disabling the button to avoid unintentional double action.
        self.prepare_to_send()
        mythread = threading.Thread(target=self.send_tx_process)
        mythread.start()
        
    def prepare_to_send(self):
        self.show.YES.disabled = True
        #Creating the loading screen
        self.loading = LoadingPopup("Broadcasting your\ntransaction...")
        self.loadingWindow = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingWindow.open()
        
    def send_tx_process(self):
        #reading the inputs and 
        #denomination = self.ids.denomination.text
        #amount = float(self.ids.amount.text)                        
        #address = self.ids.address.text
        address = self.address
        address = address.replace("\n","")
        address = address.strip(" ")
        address = address.strip("'")
        starts = address.rfind("'")
        address = address[starts+1:]                        
        
        #if denomination == "Bitcoins": amount = int(amount*100000000)
        #else: amount = int(amount)
            
        #broadcasting transaction
        try: 
            tx, sent = self.send_tx(self, self.amount, address)
                                
            #cleanning the inputs
            self.ids.amount.text = ""
            self.ids.address.text = ""
            
            if isinstance(sent,bool):
                if not sent:
                    self.share = GenericOkPopup(tx.transaction.serialize().hex())
                    self.shareWindow = Popup(title="Share with cosigners", content=self.share, 
                                                      size_hint=(None,None),size=(500,500), 
                                                      pos_hint={"center_x":0.5, "center_y":0.5})
                    self.shareWindow.open()
                    self.share.OK.bind(on_release=self.shareWindow.dismiss)  
                        
        except Exception as e:
                                
            if str(e).startswith("Not enough funds"):
                self.exception_popup = GenericOkPopup("You don't have enough\nfunds for this transaction.\n\nSorry :/")
                self.notEnoughFundsWindow = Popup(title="Not a valid amount", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                
            elif str(e).startswith("('Status Code 429'"):
                self.exception_popup = GenericOkPopup("Too many requests in the\npast hour.\nTry again later.")
                self.notEnoughFundsWindow = Popup(title="Server Error", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                 
            elif (str(e)[str(e).find(" ")+1:]).startswith("not a valid"):
                                
                msg1 = "You entered an invalid address.\nWe prevented the transaction from\nlosing your funds. "
                msg2 = "Please\nenter a valid address and try\nagain."
                self.exception_popup = GenericOkPopup(msg)
                self.notEnoughFundsWindow = Popup(title="Bad Address", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                
            else:
                #TRIGGER THE "OOPS! POPUP"
                self.exception_popup = GenericOkPopup(f"Oops! Something went wrong.\n{str(e)}\nPlease try again later.")
                self.notEnoughFundsWindow = Popup(title="Unknown Exception", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                
        
    def scan_qr(self):
        self.qrscanner = CameraPopup()
        self.QRScannerWindow = Popup(title="Scan Qr Code", content=self.qrscanner, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.6}
                            #auto_dismiss=False
                           )
        self.QRScannerWindow.open()
        self.qrscanner.ids.select.bind(on_release=self.scanqr)
    
    
    def scanqr(self,button_object):
        self.ids.address.text = self.qrscanner.ids.address.text
        self.QRScannerWindow.dismiss()
        
class SendScreen(Screen,Send):
    pass
    
        
class CameraPopup(FloatLayout):
    pass

class SafeTransferScreen(Screen, Send):
    font_size = "15sp"
    
    
    def go_back(self):
        self.app.sm.current = self.app.caller 
    
    def on_pre_enter(self):
        self.app = App.get_running_app()
        print(f"self.app.current_wallet_balance {self.app.current_wallet_balance}")
        balnace_txt = self.ids.balance.text = self.app.current_wallet_balance
        self.balance = int(float(balnace_txt.split()[0])*100000000)
        print(f"balance in satoshis: {self.balance}")
        print(self.app.caller)
        if self.app.caller == "WeekSafeScreen":
            self.ids.title.text = "Transfer Week Safe"
            self.ids.transfer.text = "Transfer From This Week"
            self.ids.transfer_all.text = "Transfer All To\nCorporate's Safe"
            self.ids.transfer_all.bind(on_press=self.send_all)
        elif self.app.caller == "DayScreen":
            self.ids.title.text = "Transfer Day Safe"
            self.ids.transfer.text = "Transfer From This Day"
            self.ids.transfer_all.text = "Transfer All To\Week's Safe"
            self.ids.transfer_all.bind(on_press=self.send_all_week_safe)
        else: self.ids.title.text = self.ids.transfer.text = self.ids.transfer_all.text =  "Error"
        
    
    def send_all_week_safe(self,button):
        """
        """
        amount = self.balance
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        parent_wallet = self.app.wallets[0][my_wallet.parent_name]
        
        date_str,name = my_wallet.name.split("_")
        monthday,of,year = date_str.split("-")
        wallet_date = date(int("20"+year),list(calendar.month_abbr).index(monthday[:3]),int(monthday[-2:]))
        _year, week, _weekday  =  wallet_date.isocalendar()
        week_safe_index = int(  str(_year)[2:] + f"{week:02d}"  )
        
        wallets_week_wallet = parent_wallet.get_weekly_safe_wallet(week_safe_index)
        
        #get_day_deposit_addresses still works for week safes, so...
        raw_address = self.app.db.get_day_deposit_addresses(wallets_week_wallet.name)
        print(raw_address)
        if len(raw_address) == 0: address = wallets_week_wallet.create_receiving_address()
        else: address = raw_address[0][0]
        
        self.ids.address.text = address
        #self.ids.denomination.text = "Satoshis"
        #self.ids.amount.text = amount
        
        self.confirm_popup(amount)
        
    def send_all(self,button):
        """
        """
        amount = self.balance
        
        self.confirm_popup(amount)
        
        

class NewWalletPopup(FloatLayout):
    pass

class GenericOkPopup(FloatLayout):
    def __init__(self,msg_txt):
        super().__init__()
                                
        message = TouchLabel(text= msg_txt,
                       halign="center",size_hint= (0.6,0.3), multiline = True,
                        pos_hint={"center_x":0.5, "center_y":0.65}, font_size="14sp"
                       )

        self.OK = Button(text="Ok. Got it!",
                     pos_hint= {"center_x":0.5, "center_y":0.18}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.add_widget(message)
        self.add_widget(self.OK) 
        
        
class NewSafePopup(FloatLayout):
    def __init__(self,kind):
        super().__init__()
        
        if kind == "daily": message = ["Today's","Yesterday's", "day's"]
        elif kind == "weekly": message = ["This week's","Last week's", "week's"]
        else: raise Exception(f"argument kind only accepts String 'daily' or 'weekly'. Not {kind}")
                                
        label = Label(text= "Create new safe wallet.\nChoose one option:",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.85}, font_size="14sp"
                       )

        self.current = Button(text=f"{message[0]} Safe",
                     pos_hint= {"center_x":0.5, "center_y":0.60}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.past = Button(text=f"{message[1]} Safe",
                     pos_hint= {"center_x":0.5, "center_y":0.35}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.other = Button(text=f"Other {message[2]} Safe",
                     pos_hint= {"center_x":0.5, "center_y":0.10}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.add_widget(label)
        self.add_widget(self.current) 
        self.add_widget(self.past) 
        self.add_widget(self.other) 
                                
class WrongInputPopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        msg_txt1 = "Only decimal numbers are allowed\nin the 'Amount' field.\nPlease enter a valid amount of"
        msg_txt2 = " currency.\nMake sure you are\nselecting the right 'Units'(Bitcoins/Satoshis)."
        msg_txt3 = "\nFor example:\n0.0234 Bitcoins;  or:  2340000 Satoshis."
        msg_txt = msg_txt1 + msg_txt2 + msg_txt3
        message = Label(text= msg_txt,
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.65}, font_size="12sp"
                       )

        self.OK = Button(text="Ok. Got it!",
                     pos_hint= {"center_x":0.5, "center_y":0.18}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.add_widget(message)
        self.add_widget(self.OK)
            
        
class LoadingPopup(FloatLayout):
     def __init__(self,msg):
        super().__init__()
        
        self.message = Label(text=msg,
                            halign="center", size_hint=(1,1), pos_hint={"center_x":0.5, "center_y":0.5},
                            
                            )
        self.add_widget(self.message)
        
class ConfirmSendPopup(FloatLayout):
    def __init__(self,amount,address,denomination):
        super().__init__()
        #self.orientation="vertical")
            
        message = Label(text=f"Are you sure you want to send\n {amount/100000000} BTC to the address\n{address}\n?",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.8}, font_size="11sp"
                       )

        self.YES = Button(text="YES",
                     pos_hint= {"center_x":0.5, "center_y":0.43}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.CANCEL = Button(text="CANCEL",
                     pos_hint= {"center_x":0.5, "center_y":0.15}, 
                     size_hint= (1,0.3),
                             background_color=[1,0.3,0.3,1]
                      )
        self.add_widget(message)
        self.add_widget(self.YES)
        self.add_widget(self.CANCEL)
         
            
class TouchLabel(Label):       
    def on_touch_down(self, touch):
        Clock.schedule_once(lambda dt: pyperclip.copy(self.text))
        Label.on_touch_down(self, touch)
        

class QRcodePopup(FloatLayout):
    def __init__(self, address):
        super().__init__()
        #self.orientation="vertical")
        self.address = address
        
        
        if self.address:
            qrcode.make(self.address).save("images/QR.png")
        
            qrcode_image = AsyncImage(source='images/QR.png',
                                size_hint= (0.8, 0.8),size=(210,210),
                                pos_hint= {'center_x':.5, 'center_y': 0.65} )
        
            address = TouchLabel(text=self.address,
                           halign="center",size_hint= (0.6,0.25), 
                            pos_hint={"center_x":0.5, "center_y":0.23},
                            font_name= "Arial",
                            font_size="12sp",
                            
                           )
            self.add_widget(qrcode_image)
            self.add_widget(address)
        else:
            address = Label(text="NO UNUSED ADDRESSES\nAVAILABLE. \n\nPLEASE CREATE A\nNEW ADDRESS.",
                           halign="center",size_hint= (0.6,0.25), 
                            pos_hint={"center_x":0.5, "center_y":0.6},
                            font_name= "Arial",
                            font_size="15sp"
                           )
            self.add_widget(address)
            
        
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        
        self.add_widget(self.OK)
        
        
class SelectOnePopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        
        address = Label(text="YOU MUST SELECT ONE\nOPTION FOR THE ADDRESS\n\n(NEW ADDRESS)\nOR\nEXISTING UNUSED\nADDRESS)",
                        halign="center",size_hint= (0.6,0.25), 
                        pos_hint={"center_x":0.5, "center_y":0.7},
                        font_name= "Arial",
                        font_size="18sp"
                        )
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        
        self.add_widget(self.OK)
        self.add_widget(address)

        
class ReceiveScreen(Screen):
    label_font_size = "15sp"
    address = None
    
    #def from_unused():
        

    def qr_popup(self):
        self.app = App.get_running_app() 
        my_wallet = self.app.wallets[0][self.app.current_wallet]
        my_wallet.start_conn()
        
        if self.ids.existing_addr.state == "down":
        
            addresses = my_wallet.get_unused_addresses_list()
            print(addresses)
            addr_type = self.ids.existing_addr.text
            
            if addr_type == "P2PKH (default)": 
                addresses_filtered = [x for x in addresses if x[0][0] in "1mn"]
                
            elif addr_type == "P2WPKH": 
                addresses_filtered = [x for x in addresses if x[0][:3] in ["tb1","bc1"]]
                
            else:
                addresses_filtered = [x for x in addresses if x[0][0] in "23"]

                
            if len(addresses_filtered)==0:
                self.show = QRcodePopup(None)
            else:
                self.show = QRcodePopup(addresses_filtered[0][0])
                
        elif self.ids.new_addr.state == "down":
            addr_type = self.ids.new_addr.text
            
            if addr_type == "P2PKH (default)": 
                addr_type = "P2PKH"
                
            account = my_wallet.create_receiving_address(addr_type)
            self.show = QRcodePopup(account.address)
        
        else: 
            self.show = SelectOnePopup()
    
        self.popupWindow = Popup(title="Address and QR Code", content=self.show, size_hint=(None,None), size=(550,700),
                                pos_hint={"center_x":0.5, "center_y":0.5})
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.OK.bind(on_release=self.popupWindow.dismiss)
    
    def activate_spinner(self):
        new_addr = True


class walletguiApp(App):
    Config.set('graphics','resizable',0)
    Config.set('graphics','width',300)
    Config.set('graphics','height',600)
    
    Window.size = (300, 600)
    
    title = "Wallet"
    
    my_wallet_names = ListProperty()
    wallets = ListProperty([{}])
    current_wallet = StringProperty()
    last_wallet = StringProperty()
    store_list=ListProperty()
    corporate_wallet = ObjectProperty()
    db = ObjectProperty()
    sm = ObjectProperty()
    caller = StringProperty()
    arguments=ListProperty()
    arguments=[{"new_wallet_consigners":{"current":""}}]
    cosigner_button = ObjectProperty()
    current_wallet_balance = StringProperty()
    
    current_wallet = None
    db = Sqlite3Wallet()
    res =  db.does_table_exist("Wallets")
    if len(res)>0:
        res = db.get_all_wallets()
        my_wallet_names = res
        
    else:
        my_wallet_names = []
        
    
    store_list = db.get_all_store_wallets()
    print(f"store_list[-1][0]: {store_list[-1][0]}")
    data = [x[0] for x in store_list if x[0]!=""]
    print(f"data: {data}")
    def build(self):
        #return Builder.load_file("walletgui.kv")
        #return WalletScreen()
        self.sm = ScreenManager()
        self.sm.add_widget(WalletScreen())
        self.sm.add_widget(MainScreen())
        self.sm.add_widget(ReceiveScreen())
        self.sm.add_widget(SendScreen())  
        self.sm.add_widget(WalletTypeScreen())
        self.sm.add_widget(StoreListScreen())  
        self.sm.add_widget(StoreSafesScreen())
        self.sm.add_widget(YearListScreen())
        self.sm.add_widget(CorporateScreen())
        self.sm.add_widget(CorporateTransferScreen())
        self.sm.add_widget(CorporateTransferFromAccountScreen())
        self.sm.add_widget(CorporateTransferAllScreen())
        self.sm.add_widget(MultiplePaymentScreen())
        self.sm.add_widget(ReceiveAccountScreen())
        self.sm.add_widget(DaySafeScreen())
        self.sm.add_widget(WeekSafeScreen())
        self.sm.add_widget(SafeTransferScreen())
        self.sm.add_widget(WeekSafeTransferScreen())
        self.sm.add_widget(NewContactScreen())
        self.sm.add_widget(NewStoreSafeScreen())
        self.sm.add_widget(MyContactsScreen())
        self.sm.add_widget(ContactInfoScreen())
        self.sm.add_widget(DayScreen())
        self.sm.add_widget(WhosHereScreen())
        return self.sm

    def on_stop(self):
        self.db.close_database()

if __name__ == '__main__':
    walletguiApp().run()
    
    