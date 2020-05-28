import kivy
kivy.require('1.11.1') # replace with your current kivy version !
from wallet import Wallet
import qrcode

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty,BooleanProperty, ObjectProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
Config.set('graphics','width',300)
Config.set('graphics','height',600)



class MainScreen(Screen):
    btc_balance = NumericProperty()
    usd_balance = 0.0
    
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        # Initialize Target Container
        self.update_balance()
    
    
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    font_size = "20sp"
    
    def update_balance(self):
        app = App.get_running_app() 
        self.my_wallet = app.my_wallet
        self.btc_balance = app.btc_balance/100000000
        self.usd_balance = self.btc_balance * 10000
        self.btc_balance_text =  str(self.btc_balance) + " BTC"
        self.usd_balance_text = "{:10.2f}".format(self.usd_balance) + " USD"
        

        
class SendScreen(Screen):
    
    """
    def function():
        app = App.get_running_app() 
        print(app.root.manager.MainScreen.my_variable)
        
    function()
    """
  
    def confirm_popup(self):
        self.show = ConfirmSendPopup()
        self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(280,280), 
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        self.show.YES.bind(on_release=self.go_back)
        self.show.CANCEL.bind(on_release=self.popupWindow.dismiss)
        
    
    def send_tx(self,screen):
        "the button is the Button object"
        print(screen.show.YES.text)
        print("SENDING TX")
        
    def go_back(self,button):
        self.send_tx(self)
        print(self.ids)
        amount = self.ids.amount.text
        address = self.ids.address.text
        print(f"amount: {amount}, address: {address}")
        #app = WindowManager()
        #Main = MainScreen(name="Main")
        #app.add_widget(Main)
        #app.switch_to(Main,direction="right")
        self.ids.amount.text = ""
        self.ids.address.text = ""
        self.popupWindow.dismiss()
        print("just did go bakc")
        
        
        
class ConfirmSendPopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        message = Label(text="Are you sure you want \nto send xx.xxx BTC to adress\n abc666lkp1233?",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"x":0.2, "top":1}
                       )

        self.YES = Button(text="YES",
                     pos_hint= {"x":0, "y":0.35}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.CANCEL = Button(text="CANCEL",
                     pos_hint= {"x":0, "y":-0.01}, 
                     size_hint= (1,0.3),
                             background_color=[1,0.3,0.3,1]
                      )
        self.add_widget(message)
        self.add_widget(self.YES)
        self.add_widget(self.CANCEL)
        

        
class QRcodePopup(FloatLayout):
    def __init__(self, address):
        super().__init__()
        #self.orientation="vertical")
        self.address = address
        
        qrcode.make(self.address).save("images/QR.png")
        
        qrcode_image = AsyncImage(source='images/QR.png',
                            size_hint= (0.8, 0.8),size=(210,210),
                            pos_hint= {'center_x':.5, 'center_y': 0.65} )
        
        address = Label(text=self.address,
                       halign="center",size_hint= (0.6,0.25), 
                        pos_hint={"center_x":0.5, "center_y":0.23},
                        font_name= "Arial",
                        font_size="13sp"
                       )
        
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        self.add_widget(qrcode_image)
        self.add_widget(address)
        self.add_widget(self.OK)
    

class ReceiveScreen(Screen):
    label_font_size = "15sp"
    address = None
    
    #def from_unused():
        
        
    
    def qr_popup(self):
        self.show = QRcodePopup("mocc7fvLz4ggT5kVfLSJsiXfFByoXYBCqi")
        self.popupWindow = Popup(title="Address QR Code", content=self.show, size_hint=(None,None), size=(280,380))
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.OK.bind(on_release=self.popupWindow.dismiss)
    
    def activate_spinner(self):
        new_addr = True
    
    
        
        
class WindowManager(ScreenManager):
    pass


class walletguiApp(App):
    
    title = "Wallet"
    #self.my_variable = StringProperty("THIS IS MY FLAG")
    
    words = "engine over neglect science fatigue dawn axis parent mind man escape era goose border invest slab relax bind desert hurry useless lonely frozen morning"
    
    my_wallet = ObjectProperty()
    btc_balance = NumericProperty()
    
    my_wallet = Wallet.recover_from_words(words, 256, "RobertPauslon",True)
    btc_balance = my_wallet.get_balance()
    
    def build(self):
        return Builder.load_file("walletgui.kv")


if __name__ == '__main__':
    walletguiApp().run()
    
    